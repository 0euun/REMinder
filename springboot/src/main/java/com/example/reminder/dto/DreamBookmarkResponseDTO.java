package com.example.reminder.dto;

import com.example.reminder.domain.dream.DreamBookmark;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class DreamBookmarkResponseDTO {
    private Long memberId;
    private Long dreamId;
    private Long bookmarkId;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;

    public static DreamBookmarkResponseDTO from(DreamBookmark dreamBookmark) {
        return DreamBookmarkResponseDTO.builder()
                .memberId(dreamBookmark.getMember().getId())
                .dreamId(dreamBookmark.getDream().getId())
                .bookmarkId(dreamBookmark.getId())
                .createdAt(dreamBookmark.getCreatedAt())
                .updatedAt(dreamBookmark.getUpdatedAt())
                .build();
    }
}
