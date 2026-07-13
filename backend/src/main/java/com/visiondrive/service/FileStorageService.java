package com.visiondrive.service;

import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import java.io.File;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.time.LocalDate;
import java.util.UUID;

/**
 * 文件存储服务
 * 负责上传文件的保存和URL生成
 */
@Slf4j
@Service
public class FileStorageService {

    @Value("${file.upload-dir:./uploads}")
    private String uploadDir;

    @Value("${server.port:8080}")
    private int serverPort;

    /**
     * 上传文件
     *  @param file 上传的文件
     *  @param subDir 子目录（images / videos）
     *  @return 可访问的URL
     */
    public String uploadFile(MultipartFile file, String subDir) {
        try {
            // 1. 校验文件类型
            String originalFilename = file.getOriginalFilename();
            if (originalFilename == null) {
                throw new IllegalArgumentException("文件名不能为空");
            }

            String ext = getFileExtension(originalFilename);
            if (!isValidImageType(ext) && !isValidVideoType(ext) && !isValidAudioType(ext)) {
                throw new IllegalArgumentException("不支持的文件格式：" + ext + "，请上传图片(jpg/png/bmp)、视频(mp4/avi/mov)或音频(mp3/wav/flac/ogg/m4a)");
            }

            // 校验文件大小（图片10MB，视频200MB，音频50MB）
            long maxSize = 200 * 1024 * 1024;
            if (isValidImageType(ext)) {
                maxSize = 10 * 1024 * 1024;
            } else if (isValidAudioType(ext)) {
                maxSize = 50 * 1024 * 1024;
            }
            if (file.getSize() > maxSize) {
                throw new IllegalArgumentException("文件大小超出限制: " + (maxSize / 1024 / 1024) + "MB");
            }

            // 2. 构建保存路径：./uploads/images/2026-07-07/
            String dateDir = LocalDate.now().toString();
            Path savePath = Paths.get(uploadDir, subDir, dateDir);
            File dir = savePath.toFile();
            if (!dir.exists()) {
                boolean created = dir.mkdirs();
                log.info("创建目录: {}, success={}", savePath, created);
            }

            // 3. 生成唯一文件名
            String newFilename = UUID.randomUUID().toString() + "." + ext;
            Path filePath = savePath.resolve(newFilename);

            // 4. 保存文件
            Files.write(filePath, file.getBytes());
            log.info("文件保存成功: {}", filePath.toAbsolutePath());

            // 5. 返回访问URL
            String url = "http://localhost:" + serverPort + "/api/files/" + subDir + "/" + dateDir + "/" + newFilename;
            log.info("文件访问URL: {}", url);

            return url;

        } catch (IllegalArgumentException e) {
            throw e;  // 直接抛出业务异常
        } catch (Exception e) {
            log.error("文件上传失败: ", e);
            throw new RuntimeException("文件上传失败: " + e.getMessage());
        }
    }

    /**
     * 获取文件扩展名
     */
    private String getFileExtension(String filename) {
        int idx = filename.lastIndexOf(".");
        return idx > 0 ? filename.substring(idx + 1).toLowerCase() : "";
    }

    /**
     * 是否是支持的图片格式
     */
    private boolean isValidImageType(String ext) {
        return "jpg".equals(ext) || "jpeg".equals(ext) || "png".equals(ext) || "bmp".equals(ext);
    }

    /**
     * 是否是支持的视频格式
     */
    private boolean isValidVideoType(String ext) {
        return "mp4".equals(ext) || "avi".equals(ext) || "mov".equals(ext);
    }

    /**
     * 是否是支持的音频格式
     */
    private boolean isValidAudioType(String ext) {
        return "mp3".equals(ext) || "wav".equals(ext) || "flac".equals(ext) || "ogg".equals(ext) || "m4a".equals(ext);
    }
}