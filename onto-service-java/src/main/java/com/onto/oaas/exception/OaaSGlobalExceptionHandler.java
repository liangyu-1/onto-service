package com.onto.oaas.exception;

import java.time.Instant;
import java.util.HashMap;
import java.util.Map;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.validation.FieldError;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

@Slf4j
@RestControllerAdvice
public class OaaSGlobalExceptionHandler {

    @ExceptionHandler(OaaSException.class)
    public ResponseEntity<Map<String, Object>> handleOaaSException(OaaSException ex) {
        log.warn("OaaS business exception: {}", ex.getMessage());
        Map<String, Object> body = new HashMap<>();
        body.put("code", ex.getCode());
        body.put("message", ex.getMessage());
        body.put("timestamp", Instant.now().toString());
        return ResponseEntity.status(HttpStatus.BAD_REQUEST).body(body);
    }

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<Map<String, Object>> handleValidation(MethodArgumentNotValidException ex) {
        Map<String, String> errors = new HashMap<>();
        ex.getBindingResult().getAllErrors().forEach(error -> {
            String fieldName = ((FieldError) error).getField();
            String errorMessage = error.getDefaultMessage();
            errors.put(fieldName, errorMessage);
        });
        Map<String, Object> body = new HashMap<>();
        body.put("code", "VALIDATION_ERROR");
        body.put("message", "Request validation failed");
        body.put("errors", errors);
        body.put("timestamp", Instant.now().toString());
        return ResponseEntity.status(HttpStatus.BAD_REQUEST).body(body);
    }

    @ExceptionHandler(Exception.class)
    public ResponseEntity<Map<String, Object>> handleGeneric(Exception ex) {
        log.error("Unexpected error", ex);
        Map<String, Object> body = new HashMap<>();
        body.put("code", "INTERNAL_ERROR");
        body.put("message", "Internal server error");
        body.put("timestamp", Instant.now().toString());
        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(body);
    }
}
