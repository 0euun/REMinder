package com.example.reminder.controller;

import com.example.reminder.dto.DreamRequestDTO;
import com.example.reminder.dto.DreamResponseDTO;
import com.example.reminder.service.DreamService;
import io.swagger.v3.oas.annotations.Operation;
import jakarta.servlet.http.HttpSession;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequiredArgsConstructor
@RequestMapping(value = "/dreams")
public class DreamController {
    private final DreamService dreamService;

    @Operation(summary = "꿈일기 작성", description = "꿈일기를 작성합니다.")
    @PostMapping
    public ResponseEntity<String> createDream(@RequestBody DreamRequestDTO dreamRequestDTO, HttpSession session) {
        String message = dreamService.createDream(dreamRequestDTO, session);
        return ResponseEntity.ok(message);
    }

    @Operation(summary = "특정 꿈일기 조회", description = "특정 꿈일기를 조회합니다.")
    @GetMapping("/{dreamId}")
    public ResponseEntity<DreamResponseDTO> getDream(@PathVariable Long dreamId) {
        return ResponseEntity.ok().body(dreamService.getDream(dreamId));
    }

    @Operation(summary = "전체 꿈일기 조회", description = "전체 꿈일기를 조회합니다.")
    @GetMapping
    public ResponseEntity<List<DreamResponseDTO>> getAllDreams() {
        return ResponseEntity.ok().body(dreamService.getAllDreams());
    }

    @Operation(summary = "본인 꿈일기 조회", description = "본인이 작성한 꿈일기를 조회합니다.")
    @GetMapping("/myDreams")
    public ResponseEntity<List<DreamResponseDTO>> getMyDreams(HttpSession session) {
        return ResponseEntity.ok().body(dreamService.getMyDreams(session));
    }

    @Operation(summary = "꿈일기 수정", description = "꿈일기를 수정합니다.")
    @PutMapping("/{dreamId}")
    public ResponseEntity<String> updateDream(@PathVariable Long dreamId, @RequestBody DreamRequestDTO dreamRequestDTO, HttpSession session) {
        String message = dreamService.updateDream(dreamId, dreamRequestDTO, session);
        return ResponseEntity.ok(message);
    }

    @Operation(summary = "꿈일기 삭제", description = "꿈일기를 삭제합니다.")
    @DeleteMapping("/{dreamId}")
    public ResponseEntity<String> deleteDream(@PathVariable Long dreamId, HttpSession session) {
        String message = dreamService.deleteDream(dreamId, session);
        return ResponseEntity.ok(message);
    }
}
