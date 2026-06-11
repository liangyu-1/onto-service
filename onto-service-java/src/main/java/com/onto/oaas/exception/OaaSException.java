package com.onto.oaas.exception;

public class OaaSException extends RuntimeException {

    private final String code;

    public OaaSException(String message) {
        super(message);
        this.code = "OAAS_ERROR";
    }

    public OaaSException(String code, String message) {
        super(message);
        this.code = code;
    }

    public OaaSException(String code, String message, Throwable cause) {
        super(message, cause);
        this.code = code;
    }

    public String getCode() {
        return code;
    }
}
