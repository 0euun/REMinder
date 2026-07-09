package com.example.reminder.dto;

import com.example.reminder.domain.dream.Dream;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class DreamResponseDTO {
    private Long dreamId;
    private Long memberId;
    private String title;
    private String content;
    private String type;
    private Boolean isPublic;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;

    public static DreamResponseDTO from(Dream dream) {
        return DreamResponseDTO.builder()
                .dreamId(dream.getId())
                .memberId(dream.getMember().getId())
                .title(dream.getTitle())
                .content(dream.getContent())
                .type(dream.getType() != null ? dream.getType().getDescription() : null)
                .isPublic(dream.getIsPublic())
                .createdAt(dream.getCreatedAt())
                .updatedAt(dream.getUpdatedAt())
                .build();
    }
}
