package com.visiondrive.repository;

import com.visiondrive.model.entity.InferenceRecord;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

@Repository
public interface InferenceRecordRepository extends JpaRepository<InferenceRecord, Long> {
    // JpaRepository 自动提供 save()、findById()、delete() 等方法
}