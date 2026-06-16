package com.onto.oaas.service.fullsync;

import static org.assertj.core.api.Assertions.assertThat;

import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import java.nio.charset.StandardCharsets;
import java.util.Base64;
import org.junit.jupiter.api.Test;
import org.springframework.test.util.ReflectionTestUtils;

class OntologyApiAuthHelperTest {

    @Test
    void shouldGenerateCorrectSignature() throws Exception {
        String appKey = "ccbdca3adf8d42f197a4961b4420048e";
        String appSecret = "7MzYulwHp9++pkZAsOCxwFJPnJV8xmVJ";

        OntologyApiAuthHelper helper = new OntologyApiAuthHelper();
        ReflectionTestUtils.setField(helper, "appKey", appKey);
        ReflectionTestUtils.setField(helper, "appSecret", appSecret);

        assertThat(helper.isConfigured()).isTrue();

        var headers = helper.createAuthHeaders();
        assertThat(headers).containsKey("X-App-Key");
        assertThat(headers).containsKey("X-Timestamp");
        assertThat(headers).containsKey("X-Nonce");
        assertThat(headers).containsKey("X-Signature");

        String key = headers.getFirst("X-App-Key");
        String timestamp = headers.getFirst("X-Timestamp");
        String nonce = headers.getFirst("X-Nonce");
        String signature = headers.getFirst("X-Signature");

        assertThat(key).isEqualTo(appKey);
        assertThat(timestamp).matches("\\d{13}");
        assertThat(nonce).hasSize(32);

        String payload = appKey + "\n" + timestamp + "\n" + nonce;
        Mac mac = Mac.getInstance("HmacSHA256");
        mac.init(new SecretKeySpec(appSecret.getBytes(StandardCharsets.UTF_8), "HmacSHA256"));
        String expected = Base64.getEncoder().encodeToString(mac.doFinal(payload.getBytes(StandardCharsets.UTF_8)));
        assertThat(signature).isEqualTo(expected);
    }

    @Test
    void shouldSkipHeadersWhenNotConfigured() {
        OntologyApiAuthHelper helper = new OntologyApiAuthHelper();
        assertThat(helper.isConfigured()).isFalse();
        var headers = helper.createAuthHeaders();
        assertThat(headers).isEmpty();
    }
}
