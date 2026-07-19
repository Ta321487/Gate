package com.thesis.service;

import com.thesis.capability.ArchiveStore;
import com.thesis.capability.TicketStore;

import java.util.List;
import java.util.Map;

/**
 * LIBRARY 薄封装：业务仍走 book/category/borrow 表，实现落在能力运行时。
 */
public class LibraryStore {

    public static final int LOAN_DAYS = TicketStore.LOAN_DAYS;
    public static final double FINE_PER_DAY = TicketStore.FINE_PER_DAY;

    static {
        ArchiveStore.bind("category", "book");
        TicketStore.bind("borrow");
    }

    public static long addCategory(String name) {
        return ArchiveStore.addCategory(name);
    }

    public static Map<String, Object> createCategory(String name) {
        return ArchiveStore.createCategory(name);
    }

    public static Map<String, Object> updateCategory(long id, String name) {
        return ArchiveStore.updateCategory(id, name);
    }

    public static void deleteCategory(long id) {
        ArchiveStore.deleteCategory(id);
    }

    public static List<Map<String, Object>> listCategories() {
        return ArchiveStore.listCategories();
    }

    public static Map<String, Object> addBook(String title, String author, String isbn, long categoryId, int stock, String coverUrl) {
        return ArchiveStore.addItem(title, author, isbn, categoryId, stock, coverUrl);
    }

    public static Map<String, Object> updateBook(long id, Map<String, Object> patch) {
        return ArchiveStore.updateItem(id, patch);
    }

    public static boolean deleteBook(long id) {
        return ArchiveStore.deleteItem(id);
    }

    public static Map<String, Object> getBook(long id) {
        return ArchiveStore.getItem(id);
    }

    public static Map<String, Object> pageBooks(String keyword, Long categoryId, int page, int size) {
        return ArchiveStore.pageItems(keyword, categoryId, page, size);
    }

    public static Map<String, Object> applyBorrow(String username, long bookId) {
        return TicketStore.apply(username, bookId);
    }

    public static Map<String, Object> approve(long borrowId, boolean pass, String remark) {
        return TicketStore.approve(borrowId, pass, remark, null);
    }

    public static Map<String, Object> approve(long borrowId, boolean pass, String remark, String operator) {
        return TicketStore.approve(borrowId, pass, remark, operator);
    }

    public static Map<String, Object> returnBook(long borrowId) {
        return TicketStore.complete(borrowId);
    }

    public static Map<String, Object> returnBook(long borrowId, String actorUid, boolean asSuperOrOwner) {
        return TicketStore.complete(borrowId, actorUid, asSuperOrOwner);
    }

    public static Map<String, Object> markOverdue(long borrowId) {
        return TicketStore.markOverdue(borrowId);
    }

    public static Map<String, Object> remind(long borrowId) {
        return TicketStore.remind(borrowId);
    }

    public static Map<String, Object> pageBorrows(String username, String status, int page, int size) {
        return TicketStore.page(username, status, page, size);
    }

    public static Map<String, Object> pageBorrows(
            String username, String status, int page, int size, String adminUid, boolean superAdmin) {
        return TicketStore.page(username, status, page, size, adminUid, superAdmin);
    }

    public static Map<String, Object> getBorrow(long id) {
        return TicketStore.get(id);
    }

    public static Map<String, Object> dashboard() {
        return TicketStore.dashboard("reader");
    }

    public static boolean runMainPathSelfCheck() {
        return TicketStore.runMainPathSelfCheck();
    }
}
