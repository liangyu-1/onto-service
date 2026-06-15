package com.onto.oaas.service.fullsync;

import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import java.nio.charset.StandardCharsets;
import java.util.Base64;
import java.util.UUID;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpHeaders;
import org.springframework.stereotype.Component;

/**
 * 本体管理系统 OpenAPI 鉴权头生成器。
 *
 * <p>签名算法：Base64(HMAC-SHA256(AppSecret, AppKey + "\n" + Timestamp + "\n" + Nonce))</p>
 */
@Slf4j
@Component
public class OntologyApiAuthHelper {

    @Value("${oaas.ontology-openapi.app-key:}")
    private String appKey;

    @Value("${oaas.ontology-openapi.app-secret:}")
    private String appSecret;

    public boolean isConfigured() {
        return appKey != null && !appKey.isBlank()
                && appSecret != null && !appSecret.isBlank();
    }

    public HttpHeaders createAuthHeaders() {
        HttpHeaders headers = new HttpHeaders();
        if (!isConfigured()) {
            log.debug("Ontology OpenAPI auth not configured, skipping auth headers");
            return headers;
        }

        String timestamp = String.valueOf(System.currentTimeMillis());
        String nonce = UUID.randomUUID().toString().replace("-", "");
        String signature = sign(appKey, appSecret, timestamp, nonce);

        headers.set("X-App-Key", appKey);
        headers.set("X-Timestamp", timestamp);
        headers.set("X-Nonce", nonce);
        headers.set("X-Signature", signature);
        return headers;
    }

    static String sign(String appKey, String appSecret, String timestamp, String nonce) {
        try {
            String payload = appKey + "\n" + timestamp + "\n" + nonce;
            Mac mac = Mac.getInstance("HmacSHA256");
            mac.init(new SecretKeySpec(appSecret.getBytes(StandardCharsets.UTF_8), "HmacSHA256"));
            byte[] bytes = mac.doFinal(payload.getBytes(StandardCharsets.UTF_8));
            return Base64.getEncoder().encodeToString(bytes);
        } catch (Exception e) {
            throw new RuntimeException("Failed to sign ontology OpenAPI request", e);
        }
    }
}
