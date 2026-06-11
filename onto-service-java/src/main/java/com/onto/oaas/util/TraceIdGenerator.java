package com.onto.oaas.util;

import java.util.UUID;

public final class TraceIdGenerator {

    private TraceIdGenerator() {
    }

    public static String generateTraceId() {
        return "trace-" + UUID.randomUUID().toString().replace("-", "").substring(0, 16);
    }

    public static String generateQueryId() {
        return "q-" + UUID.randomUUID().toString().replace("-", "").substring(0, 12);
    }
}
