package com.visiondrive.repository;

import com.visiondrive.model.entity.AlertEvent;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface AlertEventRepository extends JpaRepository<AlertEvent, Long> {

    List<AlertEvent> findBySeverity(String severity);

    List<AlertEvent> findByResolved(Boolean resolved);

    List<AlertEvent> findBySeverityAndResolved(String severity, Boolean resolved);

    long countBySeverity(String severity);

    long countByResolved(Boolean resolved);
}