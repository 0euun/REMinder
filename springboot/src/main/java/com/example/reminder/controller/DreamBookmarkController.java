package com.example.reminder.controller;

import com.example.reminder.dto.DreamBookmarkRequestDTO;
import com.example.reminder.dto.DreamBookmarkResponseDTO;
import com.example.reminder.service.DreamBookmarkService;
import io.swagger.v3.oas.annotations.Operation;
import jakarta.servlet.http.HttpSession;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequiredArgsConstructor
@RequestMapping("/dreamBookmarks")
//"/dreamComments")
public class DreamBookmarkController {
    private final DreamBookmarkService dreamBookmarkService;

    @Operation(summary = "북마크 등록", description = "꿈일기를 북마크합니다.")
    @PostMapping
    public ResponseEntity<String> createBookmark(@RequestBody DreamBookmarkRequestDTO dreamBookmarkRequestDTO, HttpSession session) {
        String message = dreamBookmarkService.creatDreamBookmark(dreamBookmarkRequestDTO.getDreamId(), session);
        return ResponseEntity.ok(message);
    }

    @Operation(summary = "내 북마크 단일 조회", description = "사용자의 특정 북마크를 조회합니다.")
    @GetMapping("/{dreamBookmarkId}")
    public ResponseEntity<DreamBookmarkResponseDTO> getDreamBookmark(@PathVariable Long dreamBookmarkId, HttpSession session) {
        return ResponseEntity.ok().body(dreamBookmarkService.getDreamBookmark(dreamBookmarkId, session));
    }

    @Operation(summary = "내 북마크 전체 조회", description = "사용자의 모든 북마크를 조회합니다.")
    @GetMapping("/me")
    public ResponseEntity<List<DreamBookmarkResponseDTO>> getMyDreamBookmarks(HttpSession session) {
        return ResponseEntity.ok().body(dreamBookmarkService.getDreamBookmarksByMember(session));
    }

    @Operation(summary = "북마크 삭제", description = "특정 꿈일기에 대한 내 북마크를 삭제합니다.")
    @DeleteMapping("/dream/{dreamId}")
    public ResponseEntity<String> deleteDreamBookmark(@PathVariable Long dreamId, HttpSession session) {
        String message = dreamBookmarkService.deleteDreamBookmark(dreamId, session);
        return ResponseEntity.ok(message);
    }
}
