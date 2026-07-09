package com.example.reminder.service;

import com.example.reminder.domain.member.Member;
import com.example.reminder.dto.LoginRequestDTO;
import com.example.reminder.dto.LoginResponseDTO;
import com.example.reminder.dto.RegisterRequestDTO;
import com.example.reminder.dto.RegisterResponseDTO;
import com.example.reminder.repository.MemberRepository;
import jakarta.servlet.http.HttpSession;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@RequiredArgsConstructor
public class AuthService {
    private final MemberRepository memberRepository;

    // 회원가입
    @Transactional
    public RegisterResponseDTO register(RegisterRequestDTO registerRequestDTO, HttpSession session) {
        String username = registerRequestDTO.getUsername();
        validateDuplicateUsername(username);

        Member member = createMember(registerRequestDTO);
        Member savedMember = memberRepository.save(member);

        session.setAttribute("memberId", savedMember.getId());

        return RegisterResponseDTO.builder()
                .memberId(savedMember.getId())
                .username(savedMember.getUsername())
                .profileImage(savedMember.getProfileImage())
                .build();
    }

    // 회원가입 username 중복 확인
    private void validateDuplicateUsername(String username) {
        boolean duplicated = memberRepository.existsByUsername(username);
        if (duplicated) {
            throw new RuntimeException("이미 사용 중인 이름입니다.");
        }
    }

    // 회원가입 Member 생성
    private Member createMember(RegisterRequestDTO registerRequestDTO) {
        Member.MemberBuilder builder = Member.builder();
        builder.username(registerRequestDTO.getUsername());
        builder.password(registerRequestDTO.getPassword());
        builder.profileImage(registerRequestDTO.getProfileImage());

        return builder.build();
    }

    // 로그인
    @Transactional
    public LoginResponseDTO login(LoginRequestDTO loginRequestDTO, HttpSession session) {
        Member member = memberRepository.findByUsername(loginRequestDTO.getUsername()).orElseThrow(() -> new RuntimeException("사용자 정보를 찾을 수 없습니다."));
        if(!member.getPassword().equals(loginRequestDTO.getPassword())){
            throw new RuntimeException("비밀번호가 틀렸습니다.");
        }
        session.setAttribute("memberId", member.getId());

        return LoginResponseDTO.builder()
                .memberId(member.getId())
                .username(member.getUsername())
                .profileImage(member.getProfileImage())
                .build();
    }

    // 로그아웃
    @Transactional
    public String logout(HttpSession session) {
        session.invalidate();
        return "로그아웃 되었습니다.";
    }

    // 로그인한 사용자 정보 조회
    @Transactional(readOnly = true)
    public LoginResponseDTO getMe(HttpSession session) {
        Object memberId = session.getAttribute("memberId");
        if(memberId == null){
            throw new RuntimeException("로그인이 필요합니다.");
        }
        Member member = memberRepository.findById((Long) memberId).orElseThrow(() -> new RuntimeException("사용자 정보를 찾을 수 없습니다."));

        return LoginResponseDTO.builder()
                .memberId(member.getId())
                .username(member.getUsername())
                .profileImage(member.getProfileImage())
                .build();
    }

    // 로그인한 사용자 member_id 조회
    @Transactional(readOnly = true)
    public Long currentMemberId(HttpSession session){
        Object memberId = session.getAttribute("memberId");
        if(memberId == null){
            throw new RuntimeException("로그인이 필요합니다.");
        }

        return (Long) memberId;
    }
}