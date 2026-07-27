package com.thesis.service;

import com.thesis.config.JpaSupport;
import com.thesis.entity.NoticeEntity;
import com.thesis.repository.NoticeRepository;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;

import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * 基线公告（MySQL sys_notice）— Spring Data JPA Repository。
 */
public class NoticeStore {

    private static final SimpleDateFormat FMT = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss");

    private static NoticeRepository repo() {
        return JpaSupport.repo(NoticeRepository.class);
    }

    private static String fmt(Date d) {
        if (d == null) return null;
        synchronized (FMT) {
            return FMT.format(d);
        }
    }

    private static Map<String, Object> shape(NoticeEntity e) {
        if (e == null) return null;
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", e.getId());
        m.put("title", e.getTitle());
        m.put("content", e.getContent());
        m.put("publisherUsername", e.getPublisherUsername());
        m.put("publisherName", e.getPublisherName());
        m.put("createdAt", fmt(e.getCreatedAt()));
        m.put("updatedAt", fmt(e.getUpdatedAt()));
        return m;
    }

    public static Map<String, Object> add(String title, String content, String publisherUsername, String publisherName) {
        String name = publisherName == null || publisherName.isBlank()
                ? (publisherUsername == null ? "系统" : publisherUsername)
                : publisherName;
        NoticeEntity e = new NoticeEntity();
        e.setTitle(title == null ? "" : title);
        e.setContent(content == null ? "" : content);
        e.setPublisherUsername(publisherUsername == null ? "" : publisherUsername);
        e.setPublisherName(name);
        e = repo().save(e);
        return get(e.getId() == null ? 0L : e.getId());
    }

    /** 领域启动时追加种子；表内已有同标题则跳过。 */
    public static void seedDomain(String title, String content, String publisherUsername, String publisherName) {
        if (repo().countByTitle(title) > 0) return;
        add(title, content, publisherUsername, publisherName);
    }

    public static Map<String, Object> get(long id) {
        return repo().findById(id).map(NoticeStore::shape).orElse(null);
    }

    public static Map<String, Object> update(long id, String title, String content) {
        return repo().findById(id).map(e -> {
            if (title != null) e.setTitle(title);
            if (content != null) e.setContent(content);
            repo().save(e);
            return shape(e);
        }).orElse(null);
    }

    public static boolean delete(long id) {
        if (!repo().existsById(id)) return false;
        repo().deleteById(id);
        return true;
    }

    public static Map<String, Object> page(int page, int size) {
        if (page < 1) page = 1;
        if (size < 1) size = 10;
        Page<NoticeEntity> p = repo().findAllByOrderByIdDesc(PageRequest.of(page - 1, size));
        List<Map<String, Object>> list = new ArrayList<>();
        for (NoticeEntity e : p.getContent()) {
            list.add(shape(e));
        }
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("list", list);
        out.put("total", p.getTotalElements());
        out.put("page", page);
        out.put("size", size);
        return out;
    }
}
