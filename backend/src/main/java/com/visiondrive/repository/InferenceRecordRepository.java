package com.visiondrive.repository;

import com.visiondrive.model.entity.InferenceRecord;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.LocalDateTime;
import java.util.Optional;

@Repository
public interface InferenceRecordRepository extends JpaRepository<InferenceRecord, Long> {

    /**
     * 多条件搜索
     */
    @Query("SELECT r FROM InferenceRecord r WHERE " +
            "(:taskType IS NULL OR r.taskType = :taskType) AND " +
            "(r.userId = :userId OR (:includeUnassigned = true AND r.userId IS NULL)) AND " +
            "(:keyword IS NULL OR LOWER(COALESCE(r.resultJson, '')) LIKE LOWER(CONCAT('%', :keyword, '%')) " +
            "OR LOWER(COALESCE(r.errorMessage, '')) LIKE LOWER(CONCAT('%', :keyword, '%'))) AND " +
            "(:startTime IS NULL OR r.createdAt >= :startTime) AND " +
            "(:endTime IS NULL OR r.createdAt <= :endTime) AND " +
            "(:success IS NULL OR r.success = :success)")
    Page<InferenceRecord> search(
            @Param("taskType") String taskType,
            @Param("userId") Long userId,
            @Param("includeUnassigned") boolean includeUnassigned,
            @Param("keyword") String keyword,
            @Param("startTime") LocalDateTime startTime,
            @Param("endTime") LocalDateTime endTime,
            @Param("success") Boolean success,
            Pageable pageable
    );

    /**
     * 按任务类型查询
     */
    Page<InferenceRecord> findByTaskType(String taskType, Pageable pageable);

    /**
     * 按用户ID查询
     */
    Page<InferenceRecord> findByUserId(Long userId, Pageable pageable);

    /**
     * 按成功状态查询
     */
    Page<InferenceRecord> findBySuccess(Boolean success, Pageable pageable);

    @Query("SELECT r FROM InferenceRecord r WHERE r.id = :id AND " +
            "(r.userId = :userId OR (:includeUnassigned = true AND r.userId IS NULL))")
    Optional<InferenceRecord> findAccessibleById(
            @Param("id") Long id,
            @Param("userId") Long userId,
            @Param("includeUnassigned") boolean includeUnassigned
    );
}
