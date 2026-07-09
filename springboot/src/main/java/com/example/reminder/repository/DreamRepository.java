package com.example.reminder.repository;

import com.example.reminder.domain.dream.Dream;
import com.example.reminder.domain.dream.DreamType;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface DreamRepository extends JpaRepository<Dream, Long> {
    List<Dream> findByType(DreamType type);
    List<Dream> findByMemberId(Long memberId);
}
