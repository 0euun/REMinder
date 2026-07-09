package com.example.reminder.service;

import com.example.reminder.domain.dream.Dream;
import com.example.reminder.domain.dream.DreamLike;
import com.example.reminder.domain.member.Member;
import com.example.reminder.dto.DreamLikeResponseDTO;
import com.example.reminder.repository.DreamLikeRepository;
import com.example.reminder.repository.DreamRepository;
import com.example.reminder.repository.MemberRepository;
import jakarta.servlet.http.HttpSession;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@RequiredArgsConstructor
public class DreamLikeService {
    private final DreamLikeRepository dreamLikeRepository;
    private final MemberRepository memberRepository;
    private final DreamRepository dreamRepository;
    private final AuthService authService;

    // 좋아요 등록
    @Transactional
    public String createDreamLike(Long dreamId, HttpSession session) {
        Long memberId = authService.currentMemberId(session);
        Member member = memberRepository.findById(memberId).orElseThrow(() -> new RuntimeException("사용자 정보를 찾을 수 없습니다."));
        Dream dream = dreamRepository.findById(dreamId).orElseThrow(() -> new RuntimeException("꿈일기가 존재하지 않습니다."));

        boolean exists = dreamLikeRepository.existsByMemberIdAndDreamId(memberId, dreamId);
        if (exists) {
            return "이미 좋아요를 누르셨습니다.";
        }

        DreamLike dreamLike = DreamLike.builder()
                .member(member)
                .dream(dream)
                .build();
        dreamLikeRepository.save(dreamLike);

        return "좋아요가 등록되었습니다.";
    }

    // 좋아요 단일 조회
    @Transactional(readOnly = true)
    public DreamLikeResponseDTO getDreamLike(Long dreamId, HttpSession session) {
        Long memberId = authService.currentMemberId(session);
        DreamLike dreamLike = dreamLikeRepository.findByMemberIdAndDreamId(memberId, dreamId).orElseThrow(() -> new RuntimeException("좋아요가 존재하지 않습니다."));

        return DreamLikeResponseDTO.from(dreamLike);
    }

    // 좋아요 삭제
    @Transactional
    public String deleteDreamLike(Long dreamId, HttpSession session) {
        Long memberId = authService.currentMemberId(session);
        DreamLike dreamLike = dreamLikeRepository.findByMemberIdAndDreamId(memberId, dreamId).orElseThrow(() -> new RuntimeException("좋아요가 존재하지 않습니다."));
        dreamLikeRepository.delete(dreamLike);
        return "좋아요가 삭제되었습니다.";
    }

    // 좋아요 수 조회
    @Transactional(readOnly = true)
    public Long countLikes(Long dreamId) {
        return dreamLikeRepository.countByDreamId(dreamId);
    }
}
