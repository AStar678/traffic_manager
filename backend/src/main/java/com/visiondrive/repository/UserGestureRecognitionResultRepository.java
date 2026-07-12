package com.visiondrive.repository;

import com.visiondrive.model.entity.RecognitionResultId;
import com.visiondrive.model.entity.UserGestureRecognitionResult;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

@Repository
public interface UserGestureRecognitionResultRepository
        extends JpaRepository<UserGestureRecognitionResult, RecognitionResultId> {

    Page<UserGestureRecognitionResult> findByIdUserIdOrderByIdCreatedAtDesc(Long userId, Pageable pageable);
}
