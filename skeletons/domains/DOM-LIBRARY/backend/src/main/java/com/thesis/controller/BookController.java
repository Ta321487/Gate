package com.thesis.controller;

import com.thesis.common.AdminAuth;
import com.thesis.common.BizException;
import com.thesis.common.ErrorCode;
import com.thesis.common.R;
import com.thesis.service.LibraryStore;
import jakarta.servlet.http.HttpSession;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/books")
public class BookController {

    @GetMapping
    public R<Map<String, Object>> page(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "10") int size,
            @RequestParam(required = false) String keyword,
            @RequestParam(required = false) Long categoryId) {
        return R.ok(LibraryStore.pageBooks(keyword, categoryId, page, size));
    }

    @GetMapping("/{id}")
    public R<Map<String, Object>> detail(@PathVariable long id) {
        Map<String, Object> book = LibraryStore.getBook(id);
        if (book == null) throw new BizException(ErrorCode.NOT_FOUND, "图书不存在");
        return R.ok(book);
    }

    @GetMapping("/categories/all")
    public R<List<Map<String, Object>>> categories() {
        return R.ok(LibraryStore.listCategories());
    }

    @PostMapping
    public R<Map<String, Object>> create(@RequestBody Map<String, Object> body, HttpSession session) {
        AdminAuth.requireSuperAdmin(session);
        String title = str(body.get("title"));
        if (title.isBlank()) throw new BizException(ErrorCode.BAD_REQUEST, "书名不能为空");
        return R.ok(LibraryStore.addBook(
                title,
                str(body.get("author")),
                str(body.get("isbn")),
                body.get("categoryId") == null ? 1L : Long.parseLong(String.valueOf(body.get("categoryId"))),
                body.get("stock") == null ? 1 : Integer.parseInt(String.valueOf(body.get("stock"))),
                str(body.get("coverUrl"))
        ));
    }

    @PutMapping("/{id}")
    public R<Map<String, Object>> update(@PathVariable long id, @RequestBody Map<String, Object> body, HttpSession session) {
        AdminAuth.requireSuperAdmin(session);
        Map<String, Object> updated = LibraryStore.updateBook(id, body);
        if (updated == null) throw new BizException(ErrorCode.NOT_FOUND, "图书不存在");
        return R.ok(updated);
    }

    @DeleteMapping("/{id}")
    public R<Void> delete(@PathVariable long id, HttpSession session) {
        AdminAuth.requireSuperAdmin(session);
        if (!LibraryStore.deleteBook(id)) throw new BizException(ErrorCode.NOT_FOUND, "图书不存在");
        return R.ok(null);
    }

    private static String str(Object o) {
        return o == null ? "" : String.valueOf(o);
    }
}
