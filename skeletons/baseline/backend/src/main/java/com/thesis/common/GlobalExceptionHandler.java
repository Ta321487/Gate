package com.thesis.common;

import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

@RestControllerAdvice
public class GlobalExceptionHandler {

    @ExceptionHandler(BizException.class)
    public R<?> handleBiz(BizException e) {
        return R.fail(e.getErrorCode(), e.getMessage());
    }

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public R<?> handleValid(MethodArgumentNotValidException e) {
        String msg = e.getBindingResult().getFieldErrors().stream()
                .findFirst()
                .map(err -> err.getField() + " " + err.getDefaultMessage())
                .orElse("参数错误");
        return R.fail(ErrorCode.BAD_REQUEST, msg);
    }

    @ExceptionHandler(Exception.class)
    public R<?> handleOther(Exception e) {
        return R.fail(ErrorCode.INTERNAL, e.getMessage() == null ? "服务器错误" : e.getMessage());
    }
}
