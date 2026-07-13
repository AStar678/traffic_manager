package com.visiondrive.model.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

/**
 * 音乐曲目响应DTO
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class MusicTrackResponse {

    private Long id;
    private String title;
    private String artist;
    private String album;
    private Double duration;
    private Long fileSize;
    private LocalDateTime createdAt;
    private String streamUrl;
    private boolean hasFile;
}
