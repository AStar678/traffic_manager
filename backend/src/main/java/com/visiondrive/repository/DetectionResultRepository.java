package com.visiondrive.repository;

import com.visiondrive.model.entity.DetectionResult;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface DetectionResultRepository extends JpaRepository<DetectionResult, Long> {
    // 按记录ID查询
    List<DetectionResult> findByRecordId(Long recordId);
}