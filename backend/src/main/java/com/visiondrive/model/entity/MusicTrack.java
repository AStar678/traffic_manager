package com.visiondrive.model.entity;

import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.hibernate.annotations.CreationTimestamp;

import java.time.LocalDateTime;

/**
 * 音乐曲目实体
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
@Entity
@Table(name = "music_track")
public class MusicTrack {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, length = 200)
    private String title;

    @Column(length = 200)
    private String artist;

    @Column(length = 200)
    private String album;

    /** 时长（秒） */
    private Double duration;

    /** 文件路径 */
    @Column(length = 500)
    private String filePath;

    /** 文件大小（字节） */
    private Long fileSize;

    /** 上传者用户ID */
    private Long userId;

    @CreationTimestamp
    @Column(updatable = false)
    private LocalDateTime createdAt;
}
