package com.example.reminder.infrastructure.openai;

import lombok.AllArgsConstructor;
import lombok.Getter;
import lombok.NoArgsConstructor;

import java.util.List;

@Getter
@NoArgsConstructor
@AllArgsConstructor
public class OpenAiResponse {
    private List<Choice> choices;

    @Getter
    public static class Choice {
        // 생성된 메세지 정보
        private OpenAiMessage message;
    }
}
