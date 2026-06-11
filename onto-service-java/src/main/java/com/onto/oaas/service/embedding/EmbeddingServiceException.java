package com.onto.oaas.service.embedding;

/**
 * Embedding 服务调用异常。
 */
public class EmbeddingServiceException extends RuntimeException {
    public EmbeddingServiceException(String message, Throwable cause) {
        super(message, cause);
    }
}
