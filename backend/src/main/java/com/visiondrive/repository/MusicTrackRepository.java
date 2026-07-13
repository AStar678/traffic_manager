package com.visiondrive.repository;

import com.visiondrive.model.entity.MusicTrack;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.Optional;

/**
 * 音乐曲目数据访问层
 */
public interface MusicTrackRepository extends JpaRepository<MusicTrack, Long> {

    List<MusicTrack> findByUserIdOrderByCreatedAtDesc(Long userId);

    Optional<MusicTrack> findByIdAndUserId(Long id, Long userId);

    List<MusicTrack> findAllByOrderByCreatedAtDesc();

    long countByUserId(Long userId);
}
