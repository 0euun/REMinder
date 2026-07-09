package com.example.reminder.infrastructure.openai;

import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestTemplate;

import java.util.List;

@Component
@RequiredArgsConstructor
public class OpenAiClient {
    private final RestTemplate restTemplate;

    @Value("${openai.api-url}")
    private String apiUrl;
    @Value("${openai.model}")
    private String model;

    // 꿈일기를 받아 수정본과 간단한 해석 결과를 반환
    public String interpretDream(String dreamText) {
        OpenAiResponse response = getChatCompletion(dreamText);
        return extractFirstAnswer(response);
    }

    // GPT 모델에 전달하고 응답 받기
    public OpenAiResponse getChatCompletion(String dreamText) {
        // OpenAI 요청 구성
        OpenAiRequest openAiRequest = getOpenAiRequest(dreamText);

        // RestTemplate을 통해 OpenAI API POST 요청 전송
        ResponseEntity<OpenAiResponse> chatResponse = restTemplate.postForEntity(
                apiUrl,
                openAiRequest,
                OpenAiResponse.class
        );

        // 응답 실패 처리
        if (chatResponse.getStatusCode().is2xxSuccessful() && chatResponse.getBody() != null) {
            return chatResponse.getBody();
        }
        throw new IllegalStateException("OpenAI API 호출 실패");
    }

    // OpenAI 요청 구성
    private OpenAiRequest getOpenAiRequest(String dreamText) {
        OpenAiMessage systemMessage = new OpenAiMessage(
                "system",
                "당신은 REMinder의 꿈 기록 도우미입니다. \n" +
                        "사용자의 꿈 내용을 바탕으로: \n" +
                        "1) 꿈일기를 현재형으로 조금 더 풍부하게 다시 써주세요. \n" +
                        "   - 원래 내용은 유지하되, 빠진 묘사나 감각을 자연스럽게 보충하세요.\n" +
                        "   - 서술은 짧은 문장, 1인칭 현재형으로 씁니다.\n" +
                        "   - 원문을 완전히 바꾸지 말고, ‘조금 더 디테일한 버전’으로 만듭니다. \n" +
                        "2) 아래에 짧은 해석(2~3문장)을 덧붙이세요. \n" +
                        "   - 꿈의 감정, 분위기, 상징 중 핵심 하나를 짚어주세요.\n" +
                        "   - 추측은 부드럽게 (“~같다”, “~을 의미할 수 있다”). \n" +
                        "출력 형식:\n" +
                        "## 꿈일기(수정본)\n" +
                        "...\n" +
                        "\n" +
                        "## 간단 해석\n" +
                        "... \n" +
                        "사용자가 기록한 꿈일기를 그대로 두되, 현재형으로 간단히 다듬고 3~5문장으로 정리해주세요. \n" +
                        "너무 길게 작성하지 말고 간단하게 작성해주세요. \n" +
                        "\n" +
                        "아래에 짧은 해석(2문장 이내)을 덧붙여주세요."
        );

        // 사용자 메시지
        OpenAiMessage userMessage = new OpenAiMessage("user", dreamText);

        // 메시지 리스트에 system -> user 순서로 담기
        List<OpenAiMessage> messages = List.of(systemMessage, userMessage);

        // 모델 이름과 메시지를 포함한 요청 객체 생성
        return new OpenAiRequest(model, messages);
    }

    // 응답에서 첫 번째 답변만 안전하게 추출
    private String extractFirstAnswer(OpenAiResponse response) {
        if (response == null) {
            return "";
        }
        List<OpenAiResponse.Choice> choices = response.getChoices();
        if (choices == null || choices.isEmpty()) {
            return "";
        }
        OpenAiMessage message = choices.get(0).getMessage();
        if (message == null) {
            return "";
        }
        return message.getContent() == null ? "" : message.getContent();
    }
}
