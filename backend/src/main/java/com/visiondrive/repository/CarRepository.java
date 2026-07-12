package com.visiondrive.repository;

import com.visiondrive.model.entity.Car;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Optional;

public interface CarRepository extends JpaRepository<Car, Long> {
    Optional<Car> findByUserId(Long userId);
}
