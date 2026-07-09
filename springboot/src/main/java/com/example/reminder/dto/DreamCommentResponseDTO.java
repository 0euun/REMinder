package com.example.reminder.dto;

import com.example.reminder.domain.dream.DreamComment;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class DreamCommentResponseDTO {
    private Long memberId;
    private Long dreamId;
    private Long commentId;
    private String content;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;

    public static DreamCommentResponseDTO from(DreamComment dreamComment) {
        return DreamCommentResponseDTO.builder()
                .memberId(dreamComment.getMember().getId())
                .dreamId(dreamComment.getDream().getId())
                .commentId(dreamComment.getId())
                .content(dreamComment.getContent())
                .createdAt(dreamComment.getCreatedAt())
                .updatedAt(dreamComment.getUpdatedAt())
                .build();
    }
}
