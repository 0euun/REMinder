package com.example.reminder.service;

import com.example.reminder.domain.dream.Dream;
import com.example.reminder.domain.member.Member;
import com.example.reminder.dto.DreamRequestDTO;
import com.example.reminder.dto.DreamResponseDTO;
import com.example.reminder.repository.DreamRepository;
import com.example.reminder.repository.MemberRepository;
import jakarta.servlet.http.HttpSession;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
public class DreamService {
    private final DreamRepository dreamRepository;
    private final MemberRepository memberRepository;
    private final AuthService authService;

    // 등록
    @Transactional
    public String createDream(DreamRequestDTO dreamRequestDTO, HttpSession session) {
        Long memberId = authService.currentMemberId(session);
        Member member = memberRepository.findById(memberId).orElseThrow(() -> new RuntimeException("사용자 정보를 찾을 수 없습니다."));

        Dream dream = Dream.builder()
                .title(dreamRequestDTO.getTitle())
                .content(dreamRequestDTO.getContent())
                .type(dreamRequestDTO.getType())
                .isPublic(dreamRequestDTO.getIsPublic())
                .member(member)
                .build();
        dreamRepository.save(dream);

        return "꿈일기가 등록되었습니다.";
    }

    // 단일 조회
    @Transactional(readOnly = true)
    public DreamResponseDTO getDream(Long id) {
        Dream dream = dreamRepository.findById(id).orElseThrow(() -> new RuntimeException("꿈일기가 존재하지 않습니다."));
        return DreamResponseDTO.from(dream);
    }

    // 전체 조회
    @Transactional(readOnly = true)
    public List<DreamResponseDTO> getAllDreams() {
        List<Dream> dreams = dreamRepository.findAll();
        return dreams.stream().map(DreamResponseDTO::from).collect(Collectors.toList());
    }

    // 자기가 쓴 글 조회
    @Transactional(readOnly = true)
    public List<DreamResponseDTO> getMyDreams(HttpSession session) {
        Long memberId = authService.currentMemberId(session);
        List<Dream> dreams = dreamRepository.findByMemberId(memberId);
        return dreams.stream().map(DreamResponseDTO::from).collect(Collectors.toList());
    }

    // 수정
    @Transactional
    public String updateDream(Long id, DreamRequestDTO dreamRequestDTO, HttpSession session) {
        Dream dream = dreamRepository.findById(id).orElseThrow(() -> new RuntimeException("꿈일기가 존재하지 않습니다."));
        Long memberId = authService.currentMemberId(session);
        enumOwner(dream, memberId);
        dream.updateFromDTO(dreamRequestDTO);

        return "꿈일기가 수정되었습니다.";
    }

    // 삭제
    @Transactional
    public String deleteDream(Long id, HttpSession session) {
        Dream dream = dreamRepository.findById(id).orElseThrow(() -> new RuntimeException("꿈일기가 존재하지 않습니다."));
        Long memberId = authService.currentMemberId(session);
        enumOwner(dream, memberId);
        dreamRepository.delete(dream);

        return "꿈일기가 삭제되었습니다.";
    }

    // 권한 확인
    public void enumOwner(Dream dream, Long memberId) {
        Long ownerId = dream.getMember().getId();

        if (!ownerId.equals(memberId)) {
            throw new RuntimeException("권한이 없습니다.");
        }
    }
}
