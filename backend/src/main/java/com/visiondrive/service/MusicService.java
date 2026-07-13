package com.visiondrive.service;

import com.visiondrive.common.exception.BusinessException;
import com.visiondrive.model.dto.MusicTrackResponse;
import com.visiondrive.model.entity.MusicTrack;
import com.visiondrive.repository.MusicTrackRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.stream.Collectors;

/**
 * 音乐播放服务 — 本地文件上传、流式播放、删除
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class MusicService {

    private final MusicTrackRepository musicTrackRepository;
    private final FileStorageService fileStorageService;

    /** 获取所有音乐列表 */
    public List<MusicTrackResponse> list() {
        return musicTrackRepository.findAllByOrderByCreatedAtDesc()
                .stream()
                .map(this::toResponse)
                .collect(Collectors.toList());
    }

    /** 上传本地音乐文件 → 存入 uploads/music/（gitignore 已忽略） */
    @Transactional
    public MusicTrackResponse upload(MultipartFile file, Long userId) {
        String url = fileStorageService.uploadFile(file, "music");
        String originalName = file.getOriginalFilename();
        String title = "未知歌曲";
        String artist = "未知艺术家";

        if (originalName != null) {
            String name = originalName;
            int dotIdx = name.lastIndexOf('.');
            if (dotIdx > 0) name = name.substring(0, dotIdx);
            if (name.contains(" - ")) {
                String[] parts = name.split(" - ", 2);
                artist = parts[0].trim();
                title = parts[1].trim();
            } else if (name.contains("-")) {
                String[] parts = name.split("-", 2);
                artist = parts[0].trim();
                title = parts[1].trim();
            } else {
                title = name.trim();
            }
        }

        MusicTrack track = new MusicTrack();
        track.setTitle(title);
        track.setArtist(artist);
        track.setFileSize(file.getSize());
        track.setFilePath(url);
        track.setUserId(userId);

        MusicTrack saved = musicTrackRepository.save(track);
        log.info("音乐上传成功: id={}, title={}", saved.getId(), saved.getTitle());
        return toResponse(saved);
    }

    /** 获取音频文件路径，用于流式播放 */
    public Path getStreamPath(Long id) {
        MusicTrack track = musicTrackRepository.findById(id)
                .orElseThrow(() -> new BusinessException(404, "歌曲不存在"));

        String path = track.getFilePath();
        if (path == null) {
            throw new BusinessException(404, "歌曲文件不存在");
        }

        Path filePath;
        if (path.startsWith("http://") || path.startsWith("https://")) {
            filePath = Path.of(path.replaceFirst(".*?/api/files/", "./uploads/"));
        } else {
            filePath = Path.of(path);
        }

        if (!Files.exists(filePath)) {
            throw new BusinessException(404, "歌曲文件已被删除");
        }
        return filePath;
    }

    /** 删除歌曲（数据库 + uploads 中的文件） */
    @Transactional
    public void delete(Long id) {
        MusicTrack track = musicTrackRepository.findById(id)
                .orElseThrow(() -> new BusinessException(404, "歌曲不存在"));

        String path = track.getFilePath();
        if (path != null && (path.startsWith("http://") || path.startsWith("https://"))) {
            try {
                Files.deleteIfExists(Path.of(path.replaceFirst(".*?/api/files/", "./uploads/")));
            } catch (Exception e) {
                log.warn("删除音乐文件失败: id={}", id);
            }
        }

        musicTrackRepository.delete(track);
        log.info("音乐删除成功: id={}", id);
    }

    private MusicTrackResponse toResponse(MusicTrack track) {
        MusicTrackResponse resp = new MusicTrackResponse();
        resp.setId(track.getId());
        resp.setTitle(track.getTitle());
        resp.setArtist(track.getArtist());
        resp.setAlbum(track.getAlbum());
        resp.setDuration(track.getDuration());
        resp.setFileSize(track.getFileSize());
        resp.setCreatedAt(track.getCreatedAt());
        resp.setHasFile(track.getFilePath() != null);
        resp.setStreamUrl("/api/v1/music/" + track.getId() + "/stream");
        return resp;
    }
}
