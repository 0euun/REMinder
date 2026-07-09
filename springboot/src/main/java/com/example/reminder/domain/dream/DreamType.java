package com.example.reminder.domain.dream;

public enum DreamType {
    HAPPY("행복한 꿈"),
    FUNNY("재미있는 꿈"),
    SAD("슬픈 꿈"),
    NIGHTMARE("악몽"),
    ANNOYING("짜증나는 꿈"),
    LUCID("자각몽"),
    NO_MEMORY("기억 안 남"),
    OTHER("기타");

    private final String description;

    DreamType(String description) {
        this.description = description;
    }

    public String getDescription() {
        return description;
    }
}