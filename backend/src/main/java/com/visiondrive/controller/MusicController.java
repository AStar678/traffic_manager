package com.visiondrive.controller;

import com.visiondrive.model.dto.ApiResponse;
import com.visiondrive.model.dto.MusicTrackResponse;
import com.visiondrive.security.AuthenticatedUser;
import com.visiondrive.service.MusicService;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.MediaTypeFactory;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.io.*;
import java.nio.file.Path;
import java.util.List;

/**
 * 音乐播放控制器
 */
@Slf4j
@RestController
@RequestMapping("/api/v1/music")
@RequiredArgsConstructor
public class MusicController {

    private final MusicService musicService;

    /** 获取音乐列表 */
    @GetMapping
    public ApiResponse<List<MusicTrackResponse>> list() {
        return ApiResponse.success(musicService.list());
    }

    /** 上传音乐文件 */
    @PostMapping("/upload")
    public ApiResponse<MusicTrackResponse> upload(
            @RequestParam("file") MultipartFile file,
            @AuthenticationPrincipal AuthenticatedUser principal) {
        Long userId = principal != null ? principal.id() : 1L;
        return ApiResponse.success(musicService.upload(file, userId));
    }

    /** 流式播放音频（支持 HTTP Range 断点续传） */
    @GetMapping("/{id}/stream")
    public void stream(
            @PathVariable Long id,
            HttpServletRequest request,
            HttpServletResponse response) {
        Path filePath = musicService.getStreamPath(id);
        java.io.File file = filePath.toFile();
        long fileLength = file.length();

        MediaType mediaType = MediaTypeFactory.getMediaType(filePath.getFileName().toString())
                .orElse(MediaType.parseMediaType("audio/mpeg"));
        response.setContentType(mediaType.toString());

        String rangeHeader = request.getHeader("Range");
        if (rangeHeader != null && rangeHeader.startsWith("bytes=")) {
            long start = 0;
            long end = fileLength - 1;
            String[] ranges = rangeHeader.substring(6).split("-");
            try {
                start = Long.parseLong(ranges[0]);
                if (ranges.length > 1) end = Long.parseLong(ranges[1]);
            } catch (NumberFormatException e) { /* use defaults */ }

            if (start >= fileLength) {
                response.setStatus(HttpStatus.REQUESTED_RANGE_NOT_SATISFIABLE.value());
                response.setHeader("Content-Range", "bytes */" + fileLength);
                return;
            }

            long contentLength = end - start + 1;
            response.setStatus(HttpStatus.PARTIAL_CONTENT.value());
            response.setHeader("Content-Range", "bytes " + start + "-" + end + "/" + fileLength);
            response.setContentLengthLong(contentLength);
            response.setHeader("Accept-Ranges", "bytes");

            try (RandomAccessFile raf = new RandomAccessFile(file, "r");
                 OutputStream out = response.getOutputStream()) {
                raf.seek(start);
                byte[] buffer = new byte[8192];
                long remaining = contentLength;
                int bytesRead;
                while (remaining > 0 && (bytesRead = raf.read(buffer, 0,
                        (int) Math.min(buffer.length, remaining))) != -1) {
                    out.write(buffer, 0, bytesRead);
                    remaining -= bytesRead;
                }
                out.flush();
            } catch (IOException e) {
                log.error("音频流读取失败: id={}", id, e);
            }
        } else {
            response.setContentLengthLong(fileLength);
            response.setHeader("Accept-Ranges", "bytes");

            try (FileInputStream fis = new FileInputStream(file);
                 OutputStream out = response.getOutputStream()) {
                byte[] buffer = new byte[8192];
                int bytesRead;
                while ((bytesRead = fis.read(buffer)) != -1) {
                    out.write(buffer, 0, bytesRead);
                }
                out.flush();
            } catch (IOException e) {
                log.error("音频流读取失败: id={}", id, e);
            }
        }
    }

    /** 删除歌曲 */
    @DeleteMapping("/{id}")
    public ApiResponse<Void> delete(@PathVariable Long id) {
        musicService.delete(id);
        return ApiResponse.success(null);
    }
}
