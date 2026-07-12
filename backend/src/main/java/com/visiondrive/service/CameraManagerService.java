package com.visiondrive.service;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.visiondrive.model.dto.CameraSlotRequest;
import com.visiondrive.model.dto.CameraSlotResponse;
import jakarta.annotation.PostConstruct;
import jakarta.annotation.PreDestroy;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import javax.imageio.ImageIO;
import java.awt.image.BufferedImage;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.time.Duration;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Objects;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;

@Slf4j
@Service
@RequiredArgsConstructor
public class CameraManagerService {

    public static final int SLOT_COUNT = 3;
    private static final long FRAME_CACHE_MILLIS = 350;
    private static final Duration CAPTURE_TIMEOUT = Duration.ofSeconds(8);
    private static final List<String> SOURCE_TYPES = List.of("OFF", "IMAGE", "VIDEO", "RTSP", "SANDBOX", "DEVICE");

    private final ObjectMapper objectMapper;
    private final Object stateLock = new Object();
    private final Object[] slotLocks = {new Object(), new Object(), new Object()};
    private final ExecutorService captureExecutor = Executors.newFixedThreadPool(SLOT_COUNT);
    private final Map<Integer, Double> videoPositions = new ConcurrentHashMap<>();
    private final List<CameraSlotResponse> slots = new ArrayList<>();

    @Value("${camera.state-file:./data/camera-slots.json}")
    private String stateFile;

    @Value("${camera.source-dir:./uploads/camera-sources}")
    private String sourceDir;

    @Value("${camera.frame-dir:./uploads/camera-frames}")
    private String frameDir;

    @Value("${camera.ffmpeg-bin:ffmpeg}")
    private String ffmpegBin;

    @Value("${camera.sandbox-base-url:rtsp://10.126.59.120:8554/live}")
    private String sandboxBaseUrl;

    @PostConstruct
    public void initialize() {
        try {
            Files.createDirectories(Path.of(sourceDir).toAbsolutePath().normalize());
            Files.createDirectories(Path.of(frameDir).toAbsolutePath().normalize());
            Path statePath = Path.of(stateFile).toAbsolutePath().normalize();
            if (statePath.getParent() != null) Files.createDirectories(statePath.getParent());
            loadState(statePath);
        } catch (Exception error) {
            log.error("初始化摄像头管理模块失败", error);
            synchronized (stateLock) {
                slots.clear();
                slots.addAll(defaultSlots());
            }
        }
    }

    @PreDestroy
    public void shutdown() {
        captureExecutor.shutdownNow();
    }

    public List<CameraSlotResponse> listSlots() {
        synchronized (stateLock) {
            return slots.stream().map(this::copySlot).toList();
        }
    }

    public List<Map<String, String>> sandboxPresets() {
        String[] scenes = {
                "桥面", "停车场出口", "行人检测", "消防车识别", "桥出口", "桥入口",
                "道路2", "隧道（事故识别）", "隧道（车辆数量）", "道路3", "停车场入口", "道路1"
        };
        List<Map<String, String>> presets = new ArrayList<>();
        for (int index = 0; index < scenes.length; index++) {
            String cameraId = "live" + (index + 1);
            Map<String, String> preset = new LinkedHashMap<>();
            preset.put("id", cameraId);
            preset.put("name", "沙盘 " + cameraId + " · " + scenes[index]);
            preset.put("url", sandboxBaseUrl.replaceAll("/+$", "") + "/" + cameraId);
            presets.add(preset);
        }
        return presets;
    }

    public List<String> sourceTypes() {
        return SOURCE_TYPES;
    }

    public CameraSlotResponse updateSlot(int slotId, CameraSlotRequest request) {
        CameraSlotResponse existing = requireSlot(slotId);
        String sourceType = normalizeSourceType(request.getSourceType());
        String nextPath = trimToNull(request.getPath());

        if (("IMAGE".equals(sourceType) || "VIDEO".equals(sourceType)) && nextPath == null) {
            nextPath = existing.getPath();
        }
        validateSource(sourceType, nextPath, request.getDeviceIndex());

        CameraSlotResponse updated = new CameraSlotResponse(
                slotId,
                trimToNull(request.getName()) != null ? request.getName().trim() : defaultName(slotId, sourceType),
                sourceType,
                "OFF".equals(sourceType) ? null : nextPath,
                request.getDeviceIndex() == null ? 0 : request.getDeviceIndex(),
                "OFF".equals(sourceType) ? "off" : "ready",
                null,
                frameUrl(slotId)
        );

        synchronized (stateLock) {
            slots.set(slotId - 1, updated);
            persistState();
        }
        videoPositions.remove(slotId);
        deleteQuietly(framePath(slotId));
        return copySlot(updated);
    }

    public CameraSlotResponse uploadMedia(int slotId, MultipartFile file) {
        String originalName = Objects.requireNonNullElse(file.getOriginalFilename(), "").trim();
        String extension = extensionOf(originalName);
        String sourceType;
        if (List.of("jpg", "jpeg", "png", "bmp").contains(extension)) {
            sourceType = "IMAGE";
        } else if (List.of("mp4", "avi", "mov", "mkv", "webm").contains(extension)) {
            sourceType = "VIDEO";
        } else {
            throw new IllegalArgumentException("仅支持 JPG/PNG/BMP 图片或 MP4/AVI/MOV/MKV/WEBM 视频");
        }

        try {
            Path directory = Path.of(sourceDir).toAbsolutePath().normalize();
            Files.createDirectories(directory);
            Path destination = directory.resolve("camera-" + slotId + "-" + System.currentTimeMillis() + "." + extension).normalize();
            if (!destination.startsWith(directory)) throw new IllegalArgumentException("非法文件路径");
            file.transferTo(destination);

            CameraSlotRequest request = new CameraSlotRequest();
            request.setSourceType(sourceType);
            request.setName(originalName.isBlank() ? "摄像头 " + slotId : originalName);
            request.setPath(destination.toString());
            return updateSlot(slotId, request);
        } catch (IOException error) {
            throw new RuntimeException("摄像头媒体保存失败: " + error.getMessage(), error);
        }
    }

    public List<CameraFrame> captureActiveFrames() {
        List<CameraSlotResponse> active = listSlots().stream()
                .filter(slot -> !"OFF".equals(slot.getSourceType()))
                .toList();
        List<CompletableFuture<CameraFrame>> futures = active.stream()
                .map(slot -> CompletableFuture.supplyAsync(() -> captureSlot(slot.getSlotId()), captureExecutor))
                .toList();
        return futures.stream().map(CompletableFuture::join).toList();
    }

    public CameraFrame captureSlot(int slotId) {
        CameraSlotResponse slot = requireSlot(slotId);
        if ("OFF".equals(slot.getSourceType())) {
            throw new IllegalStateException("摄像头 " + slotId + " 已关闭");
        }

        synchronized (slotLocks[slotId - 1]) {
            Path output = framePath(slotId);
            try {
                if (Files.exists(output)
                        && System.currentTimeMillis() - Files.getLastModifiedTime(output).toMillis() < FRAME_CACHE_MILLIS) {
                    return new CameraFrame(slotId, slot.getName(), slot.getSourceType(), output, frameUrl(slotId));
                }
                Files.createDirectories(output.getParent());
                Path temporary = output.resolveSibling(output.getFileName() + ".tmp.jpg");
                captureFrame(slot, temporary);
                moveReplacing(temporary, output);
                updateRuntimeState(slotId, "ready", null);
                return new CameraFrame(slotId, slot.getName(), slot.getSourceType(), output, frameUrl(slotId));
            } catch (Exception error) {
                updateRuntimeState(slotId, "error", error.getMessage());
                throw new RuntimeException("摄像头 " + slotId + " 取帧失败: " + error.getMessage(), error);
            }
        }
    }

    public Path currentFramePath(int slotId) {
        return captureSlot(slotId).path();
    }

    private void captureFrame(CameraSlotResponse slot, Path output) throws Exception {
        switch (slot.getSourceType()) {
            case "IMAGE" -> copyImageAsJpeg(slot.getPath(), output);
            case "VIDEO" -> captureVideoFrame(slot, output);
            case "RTSP" -> captureWithFfmpeg(List.of("-rtsp_transport", "tcp", "-i", slot.getPath()), output);
            case "SANDBOX" -> captureWithFfmpeg(List.of("-rtsp_transport", "tcp", "-i", sandboxUrl(slot.getPath())), output);
            case "DEVICE" -> captureDeviceFrame(slot, output);
            default -> throw new IllegalArgumentException("不支持的摄像头类型: " + slot.getSourceType());
        }
    }

    private void copyImageAsJpeg(String input, Path output) throws IOException {
        BufferedImage image = ImageIO.read(Path.of(input).toFile());
        if (image == null) throw new IOException("无法读取图片: " + input);
        if (!ImageIO.write(image, "jpg", output.toFile())) {
            throw new IOException("无法编码 JPEG 图片");
        }
    }

    private void captureVideoFrame(CameraSlotResponse slot, Path output) throws Exception {
        double position = videoPositions.getOrDefault(slot.getSlotId(), 0.0);
        try {
            captureWithFfmpeg(List.of("-ss", String.format(Locale.ROOT, "%.2f", position), "-i", slot.getPath()), output);
            videoPositions.put(slot.getSlotId(), position + 0.8);
        } catch (Exception firstError) {
            videoPositions.put(slot.getSlotId(), 0.0);
            captureWithFfmpeg(List.of("-ss", "0", "-i", slot.getPath()), output);
        }
    }

    private void captureDeviceFrame(CameraSlotResponse slot, Path output) throws Exception {
        int index = slot.getDeviceIndex() == null ? 0 : slot.getDeviceIndex();
        String os = System.getProperty("os.name", "").toLowerCase(Locale.ROOT);
        if (os.contains("mac")) {
            captureWithFfmpeg(List.of("-f", "avfoundation", "-framerate", "15", "-i", index + ":none"), output);
        } else {
            captureWithFfmpeg(List.of("-f", "v4l2", "-i", "/dev/video" + index), output);
        }
    }

    private void captureWithFfmpeg(List<String> inputArguments, Path output) throws Exception {
        List<String> command = new ArrayList<>();
        command.add(ffmpegBin);
        command.addAll(List.of("-hide_banner", "-loglevel", "error", "-nostdin"));
        command.addAll(inputArguments);
        command.addAll(List.of("-frames:v", "1", "-q:v", "2", "-y", output.toString()));

        Process process = new ProcessBuilder(command).redirectErrorStream(true).start();
        boolean finished = process.waitFor(CAPTURE_TIMEOUT.toMillis(), TimeUnit.MILLISECONDS);
        if (!finished) {
            process.destroyForcibly();
            throw new IOException("FFmpeg 取帧超时");
        }
        String outputText = new String(process.getInputStream().readAllBytes()).trim();
        if (process.exitValue() != 0 || !Files.exists(output)) {
            throw new IOException(outputText.isBlank() ? "FFmpeg 取帧失败" : outputText);
        }
    }

    private CameraSlotResponse requireSlot(int slotId) {
        if (slotId < 1 || slotId > SLOT_COUNT) throw new IllegalArgumentException("摄像头槽位必须是 1-3");
        synchronized (stateLock) {
            return copySlot(slots.get(slotId - 1));
        }
    }

    private void validateSource(String sourceType, String path, Integer deviceIndex) {
        if (!SOURCE_TYPES.contains(sourceType)) throw new IllegalArgumentException("不支持的输入类型: " + sourceType);
        if ("OFF".equals(sourceType)) return;
        if (("IMAGE".equals(sourceType) || "VIDEO".equals(sourceType))) {
            if (path == null) throw new IllegalArgumentException("请先上传图片或视频");
            if (!Files.isRegularFile(Path.of(path))) throw new IllegalArgumentException("媒体文件不存在: " + path);
        }
        if ("RTSP".equals(sourceType) && (path == null || !path.matches("^(rtsp|rtsps|http|https)://.+"))) {
            throw new IllegalArgumentException("真实视频流必须使用 RTSP/HTTP URL");
        }
        if ("SANDBOX".equals(sourceType) && path == null) throw new IllegalArgumentException("请选择沙盘摄像头");
        if ("DEVICE".equals(sourceType) && deviceIndex != null && deviceIndex < 0) {
            throw new IllegalArgumentException("摄像头设备索引不能为负数");
        }
    }

    private String normalizeSourceType(String value) {
        String normalized = Objects.requireNonNullElse(value, "").trim().toUpperCase(Locale.ROOT);
        if ("REAL".equals(normalized) || "STREAM".equals(normalized)) return "RTSP";
        return normalized;
    }

    private String sandboxUrl(String path) {
        if (path.matches("^(rtsp|rtsps)://.+")) return path;
        return sandboxBaseUrl.replaceAll("/+$", "") + "/" + path.replaceFirst("^/+", "");
    }

    private Path framePath(int slotId) {
        return Path.of(frameDir).toAbsolutePath().normalize().resolve("camera-" + slotId + ".jpg");
    }

    private String frameUrl(int slotId) {
        return "/api/v1/cameras/slots/" + slotId + "/frame.jpg";
    }

    private void updateRuntimeState(int slotId, String status, String error) {
        synchronized (stateLock) {
            CameraSlotResponse slot = slots.get(slotId - 1);
            slot.setStatus(status);
            slot.setError(error);
        }
    }

    private void loadState(Path statePath) throws IOException {
        synchronized (stateLock) {
            slots.clear();
            if (Files.isRegularFile(statePath)) {
                List<CameraSlotResponse> saved = objectMapper.readValue(statePath.toFile(), new TypeReference<>() {});
                if (saved.size() == SLOT_COUNT) slots.addAll(saved);
            }
            if (slots.size() != SLOT_COUNT) {
                slots.clear();
                slots.addAll(defaultSlots());
                persistState();
            }
            slots.forEach(slot -> {
                slot.setStatus("OFF".equals(slot.getSourceType()) ? "off" : "ready");
                slot.setError(null);
                slot.setFrameUrl(frameUrl(slot.getSlotId()));
            });
        }
    }

    private List<CameraSlotResponse> defaultSlots() {
        return List.of(
                new CameraSlotResponse(1, "沙盘 live3 · 行人检测", "SANDBOX", "live3", 0, "ready", null, frameUrl(1)),
                new CameraSlotResponse(2, "沙盘 live5 · 桥出口", "SANDBOX", "live5", 0, "ready", null, frameUrl(2)),
                new CameraSlotResponse(3, "沙盘 live6 · 桥入口", "SANDBOX", "live6", 0, "ready", null, frameUrl(3))
        );
    }

    private void persistState() {
        try {
            Path path = Path.of(stateFile).toAbsolutePath().normalize();
            if (path.getParent() != null) Files.createDirectories(path.getParent());
            objectMapper.writerWithDefaultPrettyPrinter().writeValue(path.toFile(), slots);
        } catch (IOException error) {
            throw new RuntimeException("保存摄像头配置失败: " + error.getMessage(), error);
        }
    }

    private CameraSlotResponse copySlot(CameraSlotResponse slot) {
        return new CameraSlotResponse(
                slot.getSlotId(), slot.getName(), slot.getSourceType(), slot.getPath(), slot.getDeviceIndex(),
                slot.getStatus(), slot.getError(), frameUrl(slot.getSlotId())
        );
    }

    private String defaultName(int slotId, String sourceType) {
        return "摄像头 " + slotId + " · " + sourceType;
    }

    private String extensionOf(String filename) {
        int index = filename.lastIndexOf('.');
        return index < 0 ? "" : filename.substring(index + 1).toLowerCase(Locale.ROOT);
    }

    private String trimToNull(String value) {
        if (value == null || value.isBlank()) return null;
        return value.trim();
    }

    private void moveReplacing(Path source, Path target) throws IOException {
        Files.move(source, target, StandardCopyOption.REPLACE_EXISTING);
    }

    private void deleteQuietly(Path path) {
        try {
            Files.deleteIfExists(path);
        } catch (IOException ignored) {
            // 旧帧清理失败不影响新配置生效。
        }
    }

    public record CameraFrame(
            Integer slotId,
            String cameraName,
            String sourceType,
            Path path,
            String frameUrl
    ) {}
}
