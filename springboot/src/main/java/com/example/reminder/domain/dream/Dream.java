package com.example.reminder.domain.dream;

import com.example.reminder.domain.member.Member;
import com.example.reminder.dto.DreamRequestDTO;
import com.example.reminder.global.entity.BaseEntity;
import jakarta.persistence.*;
import lombok.*;

@Entity
@Getter
@NoArgsConstructor
@AllArgsConstructor
@Builder
@Table(name = "dream")
public class Dream extends BaseEntity {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "dream_id")
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "member_id", nullable = false)
    private Member member;

    @Column(nullable = false, length = 50)
    private String title;

    @Lob
    @Column(nullable = false)
    private String content;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false)
    private DreamType type;

    @Builder.Default
    @Column(name = "is_public", nullable = false, columnDefinition = "BOOLEAN DEFAULT true")
    private Boolean isPublic = true;

    public void updateFromDTO(DreamRequestDTO dto) {
        this.title = dto.getTitle();
        this.content = dto.getContent();
        this.type = dto.getType();
        this.isPublic = dto.getIsPublic();
    }
}