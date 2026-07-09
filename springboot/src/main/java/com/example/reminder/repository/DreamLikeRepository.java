package com.example.reminder.repository;

import com.example.reminder.domain.dream.DreamLike;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Optional;

public interface DreamLikeRepository extends JpaRepository<DreamLike, Long> {
    boolean existsByMemberIdAndDreamId(Long memberId, Long dreamId);
    Optional<DreamLike> findByMemberIdAndDreamId(Long memberId, Long dreamId);
    Long countByDreamId(Long dreamId);
}
