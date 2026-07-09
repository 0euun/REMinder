package com.example.reminder.repository;

import com.example.reminder.domain.dream.DreamComment;
import org.springframework.data.jpa.repository.JpaRepository;

public interface DreamCommentRepository extends JpaRepository<DreamComment, Long> {

}
