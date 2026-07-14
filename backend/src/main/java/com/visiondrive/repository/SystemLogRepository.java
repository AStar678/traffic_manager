package com.visiondrive.repository;

import com.visiondrive.model.entity.SystemLog;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.LocalDateTime;
import java.util.List;

@Repository
public interface SystemLogRepository extends JpaRepository<SystemLog, Long> {

    List<SystemLog> findByModuleAndCreatedAtAfter(String module, LocalDateTime after);

    List<SystemLog> findByModuleAndEventAndCreatedAtAfter(String module, String event, LocalDateTime after);

    @Modifying(clearAutomatically = true, flushAutomatically = true)
    @Query("""
            DELETE FROM SystemLog log
            WHERE UPPER(log.level) = 'ERROR'
              AND (:module IS NULL OR log.module = :module)
              AND (:event IS NULL OR log.event = :event)
            """)
    int deleteErrorLogs(@Param("module") String module, @Param("event") String event);
}
