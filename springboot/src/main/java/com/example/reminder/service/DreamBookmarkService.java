package com.example.reminder.service;

import com.example.reminder.domain.dream.Dream;
import com.example.reminder.domain.dream.DreamBookmark;
import com.example.reminder.domain.member.Member;
import com.example.reminder.dto.DreamBookmarkResponseDTO;
import com.example.reminder.repository.DreamBookmarkRepository;
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
public class DreamBookmarkService {
    private final DreamBookmarkRepository dreamBookmarkRepository;
    private final MemberRepository memberRepository;
    private final DreamRepository dreamRepository;
    private final AuthService authService;

    // 북마크 등록
    @Transactional
    public String creatDreamBookmark(Long dreamId, HttpSession session) {
        Long memberId = authService.currentMemberId(session);
        Member member = memberRepository.findById(memberId).orElseThrow(() -> new RuntimeException("사용자 정보를 찾을 수 없습니다."));
        Dream dream = dreamRepository.findById(dreamId).orElseThrow(() -> new RuntimeException("꿈일기가 존재하지 않습니다."));

        boolean exists = dreamBookmarkRepository.existsByMemberIdAndDreamId(memberId, dreamId);
        if (exists) {
            return "이미 등록되었습니다.";
        }

        DreamBookmark dreamBookmark = DreamBookmark.builder()
                .member(member)
                .dream(dream)
                .build();
        dreamBookmarkRepository.save(dreamBookmark);

        return "북마크가 등록되었습니다.";
    }

    // 특정 회원 북마크 단일 조회
    @Transactional(readOnly = true)
    public DreamBookmarkResponseDTO  getDreamBookmark(Long dreamId, HttpSession session) {
        Long memberId = authService.currentMemberId(session);
        DreamBookmark dreamBookmark = dreamBookmarkRepository.findByMemberIdAndDreamId(memberId, dreamId).orElseThrow(() -> new RuntimeException("북마크가 존재하지 않습니다."));
        return DreamBookmarkResponseDTO.from(dreamBookmark);
    }

    // 특정 회원 북마크 전체 조회
    @Transactional(readOnly = true)
    public List<DreamBookmarkResponseDTO> getDreamBookmarksByMember(HttpSession session) {
        Long memberId = authService.currentMemberId(session);
        List<DreamBookmark> dreamBookmarks = dreamBookmarkRepository.findByMemberId(memberId);
        return dreamBookmarks.stream().map(DreamBookmarkResponseDTO::from).collect(Collectors.toList());
    }

    // 북마크 삭제
    public String deleteDreamBookmark(Long dreamId, HttpSession session) {
        Long memberId = authService.currentMemberId(session);
        DreamBookmark dreamBookmark = dreamBookmarkRepository.findByMemberIdAndDreamId(memberId, dreamId).orElseThrow(() -> new RuntimeException("북마크가 존재하지 않습니다."));
        dreamBookmarkRepository.delete(dreamBookmark);

        return "북마크가 삭제되었습니다.";
    }
}
