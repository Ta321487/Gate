package com.thesis.common;

public enum ErrorCode {
    OK(0),
    BAD_REQUEST(40000),
    UNAUTHORIZED(40100),
    CAPTCHA_INVALID(40101),
    FORBIDDEN(40300),
    NOT_FOUND(40400),
    INTERNAL(50000);

    private final int code;

    ErrorCode(int code) { this.code = code; }
    public int getCode() { return code; }
}
