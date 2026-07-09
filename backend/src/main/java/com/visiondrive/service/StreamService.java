package com.visiondrive.service;

import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.io.File;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * 沙盘摄像头推流管理 —— 管理 Python DetectionStreamer 子进程
 */
@Slf4j
@Service
public class StreamService {

    private final Map<String, Process> runningStreams = new ConcurrentHashMap<>();

    /** 算法项目根目录（自动探测） */
    private static final String ALGORITHM_DIR = detectAlgorithmDir();

    private static String detectAlgorithmDir() {
        String cwd = System.getProperty("user.dir");
        // 尝试相对路径
        File dir = new File(cwd, "algorithm");
        if (dir.exists()) return dir.getAbsolutePath();
        // 可能在 backend 子目录下
        dir = new File(cwd, "../algorithm");
        if (dir.exists()) return dir.getAbsolutePath();
        // 回退：通过系统属性指定
        return System.getProperty("algorithm.dir", cwd + "/algorithm");
    }

    /**
     * 启动摄像头推流
     * @param cameraId  摄像头编号 (live1 ~ live12)
     * @return WebRTC 观看 URL，失败返回错误信息
     */
    public Map<String, Object> startStream(String cameraId) {
        if (runningStreams.containsKey(cameraId)) {
            return Map.of("success", true, "webRtcUrl", buildWebRtcUrl(cameraId),
                    "message", "已运行中");
        }

        try {
            ProcessBuilder pb = new ProcessBuilder(
                    "python", "streaming_demo.py",
                    "--camera", cameraId,
                    "--no-preview"
            );
            pb.directory(new File(ALGORITHM_DIR));
            pb.redirectErrorStream(true);
            pb.redirectOutput(new File(ALGORITHM_DIR, "stream_" + cameraId + ".log"));

            Process process = pb.start();
            runningStreams.put(cameraId, process);

            // 等 3 秒确认启动成功
            Thread.sleep(3000);

            if (process.isAlive()) {
                String url = buildWebRtcUrl(cameraId);
                log.info("摄像头 {} 推流已启动, WebRTC: {}", cameraId, url);
                return Map.of("success", true, "webRtcUrl", url,
                        "cameraId", cameraId);
            } else {
                runningStreams.remove(cameraId);
                return Map.of("success", false, "message", "推流进程启动失败");
            }
        } catch (Exception e) {
            log.error("启动推流失败: cameraId={}", cameraId, e);
            runningStreams.remove(cameraId);
            return Map.of("success", false, "message", "启动失败: " + e.getMessage());
        }
    }

    /**
     * 停止摄像头推流
     */
    public Map<String, Object> stopStream(String cameraId) {
        Process process = runningStreams.remove(cameraId);
        if (process != null && process.isAlive()) {
            process.destroyForcibly();
            log.info("摄像头 {} 推流已停止", cameraId);
            return Map.of("success", true, "message", "已停止");
        }
        return Map.of("success", true, "message", "未在运行");
    }

    /**
     * 查询当前运行中的推流
     */
    public Map<String, Object> getRunningStreams() {
        Map<String, Object> result = new java.util.HashMap<>();
        result.put("count", runningStreams.size());
        result.put("cameras", runningStreams.keySet().stream()
                .map(id -> Map.of("cameraId", id, "webRtcUrl", buildWebRtcUrl(id)))
                .toList());
        return result;
    }

    /**
     * 根据摄像头编号生成 WebRTC 观看地址
     * live1 → http://127.0.0.1:8889/video31
     */
    private String buildWebRtcUrl(String cameraId) {
        int num = Integer.parseInt(cameraId.replace("live", ""));
        return "http://127.0.0.1:8889/video3" + num;
    }
}
