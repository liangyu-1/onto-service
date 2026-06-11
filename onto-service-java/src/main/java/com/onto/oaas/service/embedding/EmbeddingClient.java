package com.onto.oaas.service.embedding;

import java.util.ArrayList;
import java.util.List;
import lombok.Data;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

/**
 * Embedding 服务客户端，调用 vLLM/OpenAI 兼容的 embedding 接口。
 */
@Slf4j
@Service
public class EmbeddingClient {

    @Value("${vllm.embedding.base-url:http://localhost:8105}")
    private String baseUrl;

    @Value("${vllm.embedding.model:bge-m3}")
    private String model;

    private final RestTemplate restTemplate;

    public EmbeddingClient(RestTemplate restTemplate) {
        this.restTemplate = restTemplate;
    }

    /**
     * 批量生成文本嵌入向量。
     */
    public List<float[]> embed(List<String> texts) {
        if (texts == null || texts.isEmpty()) {
            return List.of();
        }

        String url = baseUrl + "/v1/embeddings";
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);

        EmbeddingRequest request = new EmbeddingRequest(model, texts, "float");
        HttpEntity<EmbeddingRequest> entity = new HttpEntity<>(request, headers);

        try {
            ResponseEntity<EmbeddingResponse> response = restTemplate.postForEntity(
                    url, entity, EmbeddingResponse.class);
            EmbeddingResponse body = response.getBody();
            if (body == null || body.getData() == null) {
                log.warn("Embedding service returned empty response");
                return List.of();
            }
            List<float[]> embeddings = new ArrayList<>();
            for (EmbeddingResponse.EmbeddingItem item : body.getData()) {
                embeddings.add(toFloatArray(item.getEmbedding()));
            }
            log.debug("Embedded {} texts, model={}", texts.size(), body.getModel());
            return embeddings;
        } catch (Exception e) {
            log.error("Failed to call embedding service at {}: {}", url, e.getMessage());
            throw new EmbeddingServiceException("Embedding service call failed", e);
        }
    }

    /**
     * 单文本嵌入（便捷方法）。
     */
    public float[] embed(String text) {
        List<float[]> results = embed(List.of(text));
        return results.isEmpty() ? new float[0] : results.get(0);
    }

    private float[] toFloatArray(List<Double> list) {
        float[] arr = new float[list.size()];
        for (int i = 0; i < list.size(); i++) {
            arr[i] = list.get(i).floatValue();
        }
        return arr;
    }

    @Data
    public static class EmbeddingRequest {
        private final String model;
        private final List<String> input;
        private final String encoding_format;
    }

    @Data
    public static class EmbeddingResponse {
        private String object;
        private List<EmbeddingItem> data;
        private String model;
        private Usage usage;

        @Data
        public static class EmbeddingItem {
            private String object;
            private int index;
            private List<Double> embedding;
        }

        @Data
        public static class Usage {
            private int prompt_tokens;
            private int total_tokens;
        }
    }
}
