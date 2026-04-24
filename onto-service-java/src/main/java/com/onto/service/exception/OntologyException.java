package com.onto.service.exception;

import lombok.Getter;

/**
 * 业务异常
 */
@Getter
public class OntologyException extends RuntimeException {

    private final int code;

    public OntologyException(String message) {
        super(message);
        this.code = 400;
    }

    public OntologyException(int code, String message) {
        super(message);
        this.code = code;
    }
}
