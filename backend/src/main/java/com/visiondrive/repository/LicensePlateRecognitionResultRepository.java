package com.visiondrive.repository;

import com.visiondrive.model.entity.LicensePlateRecognitionResult;
import com.visiondrive.model.entity.RecognitionResultId;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

@Repository
public interface LicensePlateRecognitionResultRepository
        extends JpaRepository<LicensePlateRecognitionResult, RecognitionResultId> {

    Page<LicensePlateRecognitionResult> findByIdUserIdOrderByIdCreatedAtDesc(Long userId, Pageable pageable);
}
