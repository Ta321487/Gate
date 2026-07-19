package com.thesis.common;

import java.util.HashMap;
import java.util.Map;

public class R<T> {
    private int code;
    private String message;
    private T data;

    public static <T> R<T> ok(T data) {
        R<T> r = new R<>();
        r.code = ErrorCode.OK.getCode();
        r.message = "ok";
        r.data = data;
        return r;
    }

    public static <T> R<T> fail(ErrorCode code, String message) {
        R<T> r = new R<>();
        r.code = code.getCode();
        r.message = message;
        return r;
    }

    public static R<Map<String, Object>> page(Object list, long total, int page, int size) {
        Map<String, Object> m = new HashMap<>();
        m.put("list", list);
        m.put("total", total);
        m.put("page", page);
        m.put("size", size);
        return ok(m);
    }

    public int getCode() { return code; }
    public String getMessage() { return message; }
    public T getData() { return data; }
}
