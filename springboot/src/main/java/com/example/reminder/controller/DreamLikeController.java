package com.example.reminder.controller;

import com.example.reminder.dto.DreamLikeRequestDTO;
import com.example.reminder.dto.DreamLikeResponseDTO;
import com.example.reminder.service.DreamLikeService;
import io.swagger.v3.oas.annotations.Operation;
import jakarta.servlet.http.HttpSession;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequiredArgsConstructor
@RequestMapping(value = "/dreamLikes")
public class DreamLikeController {
    private final DreamLikeService dreamLikeService;

    @Operation(summary = "좋아요 등록", description = "꿈일기에 좋아요를 등록합니다.")
    @PostMapping
    public ResponseEntity<String> createDreamLike(@RequestBody DreamLikeRequestDTO dreamLikeRequestDTO, HttpSession session) {
        String message = dreamLikeService.createDreamLike(dreamLikeRequestDTO.getDreamId(), session);
        return ResponseEntity.ok(message);
    }

    @Operation(summary = "내 좋아요 단일 조회", description = "특정 꿈일기에 대한 내 좋아요를 조회합니다.")
    @GetMapping("/dream/{dreamId}/")
    public ResponseEntity<DreamLikeResponseDTO> getDreamLike(@PathVariable Long dreamId, HttpSession session) {
        return ResponseEntity.ok().body(dreamLikeService.getDreamLike(dreamId, session));
    }

    @Operation(summary = "좋아요 삭제", description = "좋아요를 삭제합니다.")
    @DeleteMapping("/dream/{dreamId}")
    public ResponseEntity<String> deleteDreamLike(@PathVariable Long dreamId, HttpSession session) {
        String message = dreamLikeService.deleteDreamLike(dreamId, session);
        return ResponseEntity.ok(message);
    }

    @Operation(summary = "좋아요 수 조회", description = "특정 꿈일기의 좋아요 수를 조회합니다.")
    @GetMapping("/dream/{dreamId}/count")
    public ResponseEntity<Long> countDreamLikes(@PathVariable Long dreamId) {
        return ResponseEntity.ok(dreamLikeService.countLikes(dreamId));
    }
}
