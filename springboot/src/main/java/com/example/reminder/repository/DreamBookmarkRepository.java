package com.example.reminder.repository;

import com.example.reminder.domain.dream.DreamBookmark;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.Optional;

public interface DreamBookmarkRepository extends JpaRepository<DreamBookmark, Long> {
    boolean existsByMemberIdAndDreamId(Long memberId, Long dreamId);
    Optional<DreamBookmark> findByMemberIdAndDreamId(Long memberId, Long dreamId);
    List<DreamBookmark> findByMemberId(Long memberId);
}
