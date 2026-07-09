package com.example.reminder.controller;

import com.example.reminder.dto.LoginRequestDTO;
import com.example.reminder.dto.LoginResponseDTO;
import com.example.reminder.dto.RegisterRequestDTO;
import com.example.reminder.dto.RegisterResponseDTO;
import com.example.reminder.service.AuthService;
import io.swagger.v3.oas.annotations.Operation;
import jakarta.servlet.http.HttpSession;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequiredArgsConstructor
@RequestMapping("/auth")
public class AuthController {
    private final AuthService authService;

    @Operation(summary = "회원가입", description = "새로운 사용자 정보를 등록합니다.")
    @PostMapping("/register")
    public ResponseEntity<RegisterResponseDTO> register(@RequestBody RegisterRequestDTO registerRequestDTO, HttpSession session) {
        return ResponseEntity.ok(authService.register(registerRequestDTO, session));
    }

    @Operation(summary = "로그인", description = "username과 password로 로그인하여 사용자 정보를 저장합니다.")
    @PostMapping("/login")
    public ResponseEntity<LoginResponseDTO> login(@RequestBody LoginRequestDTO loginRequestDTO, HttpSession session) {
        return ResponseEntity.ok(authService.login(loginRequestDTO, session));
    }

    @Operation(summary = "로그아웃", description = "세션 정보를 만료시켜 로그아웃합니다.")
    @PostMapping("/logout")
    public ResponseEntity<String> logout(HttpSession session) {
        String message = authService.logout(session);
        return ResponseEntity.ok(message);
    }

    @Operation(summary = "내 정보 조회", description = "로그인된 사용자 정보를 반환합니다.")
    @GetMapping("/me")
    public ResponseEntity<LoginResponseDTO> getMe(HttpSession session) {
        return ResponseEntity.ok(authService.getMe(session));
    }
}