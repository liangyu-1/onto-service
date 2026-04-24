package com.onto.service.exception;

import com.onto.service.common.Result;
import lombok.extern.slf4j.Slf4j;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

/**
 * 全局异常处理
 */
@Slf4j
@RestControllerAdvice
public class GlobalExceptionHandler {

    @ExceptionHandler(Exception.class)
    public Result<Void> handleException(Exception e) {
        log.error("System error: ", e);
        return Result.error(e.getMessage());
    }

    @ExceptionHandler(OntologyException.class)
    public Result<Void> handleOntologyException(OntologyException e) {
        log.error("Ontology error: ", e);
        return Result.error(e.getCode(), e.getMessage());
    }
}
