package com.example.reminder.dto;

import com.example.reminder.domain.dream.DreamLike;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class DreamLikeResponseDTO {
    private Long memberId;
    private Long dreamId;
    private Long likeId;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;

    public static DreamLikeResponseDTO from(DreamLike dreamLike) {
        return DreamLikeResponseDTO.builder()
                .memberId(dreamLike.getMember().getId())
                .dreamId(dreamLike.getDream().getId())
                .likeId(dreamLike.getId())
                .createdAt(dreamLike.getCreatedAt())
                .updatedAt(dreamLike.getUpdatedAt())
                .build();
    }
}
