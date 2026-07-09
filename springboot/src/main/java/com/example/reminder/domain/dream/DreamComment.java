package com.example.reminder.domain.dream;

import com.example.reminder.domain.member.Member;
import com.example.reminder.dto.DreamCommentRequestDTO;
import com.example.reminder.global.entity.BaseEntity;
import jakarta.persistence.*;
import lombok.*;

@Entity
@Getter
@NoArgsConstructor
@AllArgsConstructor
@Builder
@Table(name = "dream_comment")
public class DreamComment extends BaseEntity {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "dream_comment_id")
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "member_id", nullable = false)
    private Member member;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "dream_id", nullable = false)
    private Dream dream;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "parent_comment_id")
    private DreamComment parentComment;

    @Lob
    @Column(nullable = false)
    private String content;

    public void updateCommentFromDTO(DreamCommentRequestDTO dto) {
        this.content = dto.getContent();
    }
}