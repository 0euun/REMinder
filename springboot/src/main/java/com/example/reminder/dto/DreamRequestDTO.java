package com.example.reminder.dto;

import com.example.reminder.domain.dream.DreamType;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class DreamRequestDTO {
    private String title;
    private String content;
    private DreamType type;
    private Boolean isPublic = true;
}
