package com.thesis.repository;

import com.thesis.entity.NoticeEntity;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;

public interface NoticeRepository extends JpaRepository<NoticeEntity, Long> {
    long countByTitle(String title);

    Page<NoticeEntity> findAllByOrderByIdDesc(Pageable pageable);
}
