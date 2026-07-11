package com.visiondrive.repository;

import com.visiondrive.model.entity.OwnerGestureControlBinding;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.Collection;
import java.util.List;
import java.util.Optional;

@Repository
public interface OwnerGestureControlBindingRepository extends JpaRepository<OwnerGestureControlBinding, Long> {
    Optional<OwnerGestureControlBinding> findByGestureCode(String gestureCode);

    List<OwnerGestureControlBinding> findByGestureCodeIn(Collection<String> gestureCodes);
}
