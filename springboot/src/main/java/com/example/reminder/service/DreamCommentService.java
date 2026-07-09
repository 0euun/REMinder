package com.example.reminder.service;

import com.example.reminder.domain.dream.Dream;
import com.example.reminder.domain.dream.DreamComment;
import com.example.reminder.domain.member.Member;
import com.example.reminder.dto.DreamCommentRequestDTO;
import com.example.reminder.dto.DreamCommentResponseDTO;
import com.example.reminder.repository.DreamCommentRepository;
import com.example.reminder.repository.DreamRepository;
import com.example.reminder.repository.MemberRepository;
import jakarta.servlet.http.HttpSession;
import org.springframework.transaction.annotation.Transactional;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
public class DreamCommentService {
    private final DreamCommentRepository dreamCommentRepository;
    private final DreamRepository dreamRepository;
    private final MemberRepository memberRepository;
    private final AuthService authService;

    // 댓글 등록
    @Transactional
    public String createDreamComment(DreamCommentRequestDTO dreamCommentRequestDTO, HttpSession session) {
        Long memberId = authService.currentMemberId(session);
        Member member = memberRepository.findById(memberId).orElseThrow(() -> new RuntimeException("사용자 정보를 찾을 수 없습니다."));
        Dream dream = dreamRepository.findById(dreamCommentRequestDTO.getDreamId()).orElseThrow(() -> new RuntimeException("꿈일기가 존재하지 않습니다."));

        DreamComment dreamComment = DreamComment.builder()
                .content(dreamCommentRequestDTO.getContent())
                .dream(dream)
                .member(member)
                .build();
        dreamCommentRepository.save(dreamComment);

        return "댓글이 등록되었습니다.";
    }

    // 특정 꿈일기 댓글 단일 조회
    @Transactional(readOnly = true)
    public  DreamCommentResponseDTO getDreamComment(Long commentId) {
        DreamComment dreamComment = dreamCommentRepository.findById(commentId).orElseThrow(() -> new RuntimeException("댓글이 존재하지 않습니다."));
        return DreamCommentResponseDTO.from(dreamComment);
    }

    // 특정 꿈일기 댓글 전체 조회
    @Transactional(readOnly = true)
    public List<DreamCommentResponseDTO> getDreamCommentsByDreamId(Long dreamId) {
        dreamRepository.findById(dreamId).orElseThrow(() -> new RuntimeException("꿈일기가 존재하지 않습니다."));

        List<DreamComment> dreamComments = dreamCommentRepository.findAll().stream()
                .filter(dreamComment -> dreamComment.getDream().getId().equals(dreamId))
                .toList();

        return dreamComments.stream().map(DreamCommentResponseDTO::from).collect(Collectors.toList());
    }

    // 수정
    @Transactional
    public String updateDreamComment(Long commentId, DreamCommentRequestDTO dreamCommentRequestDTO, HttpSession session) {
        DreamComment dreamComment = dreamCommentRepository.findById(commentId).orElseThrow(() -> new RuntimeException("댓글이 존재하지 않습니다."));
        Long memberId = authService.currentMemberId(session);
        enumCommentOwner(dreamComment, memberId);
        dreamComment.updateCommentFromDTO(dreamCommentRequestDTO);

        return "댓글이 수정되었습니다.";
    }

    // 삭제
    @Transactional
    public String deleteDreamComment(Long commentId, HttpSession session) {
        DreamComment dreamComment = dreamCommentRepository.findById(commentId).orElseThrow(() -> new RuntimeException("댓글이 존재하지 않습니다."));
        Long memberId = authService.currentMemberId(session);
        enumCommentOwner(dreamComment, memberId);
        dreamCommentRepository.delete(dreamComment);

        return "댓글이 삭제되었습니다.";
    }

    // 권한 확인
    public void enumCommentOwner(DreamComment dreamComment, Long memberId) {
        Long ownerId = dreamComment.getMember().getId();

        if (!ownerId.equals(memberId)) {
            throw new RuntimeException("권한이 없습니다.");
        }
    }
}
