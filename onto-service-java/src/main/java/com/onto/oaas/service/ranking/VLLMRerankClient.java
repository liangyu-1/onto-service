package com.onto.oaas.service.ranking;

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
 * vLLM Reranker 服务客户端。
 *
 * <p>调用 vLLM 的 /v1/rerank 接口，获取 query-documents 的相关性分数。</p>
 */
@Slf4j
@Service
public class VLLMRerankClient {

    @Value("${vllm.rerank.base-url:http://localhost:8104}")
    private String baseUrl;

    @Value("${vllm.rerank.model:Qwen3-Reranker-4B}")
    private String model;

    private final RestTemplate restTemplate;

    public VLLMRerankClient(RestTemplate restTemplate) {
        this.restTemplate = restTemplate;
    }

    /**
     * 对 query-documents 对进行重排序评分。
     *
     * @param query     查询文本
     * @param documents 候选文档文本列表
     * @param topN      返回 Top-N 结果
     * @return 按 relevance_score 降序排列的结果列表
     */
    public List<RerankResult> rerank(String query, List<String> documents, int topN) {
        if (query == null || query.isBlank() || documents == null || documents.isEmpty()) {
            return List.of();
        }

        String url = baseUrl + "/v1/rerank";
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);

        RerankRequest request = new RerankRequest(model, query, documents, topN);
        HttpEntity<RerankRequest> entity = new HttpEntity<>(request, headers);

        try {
            ResponseEntity<RerankResponse> response = restTemplate.postForEntity(
                    url, entity, RerankResponse.class);
            RerankResponse body = response.getBody();
            if (body == null || body.getResults() == null) {
                log.warn("Rerank service returned empty response");
                return List.of();
            }
            log.debug("Reranked {} docs for query, topN={}", documents.size(), topN);
            return body.getResults();
        } catch (Exception e) {
            log.error("Failed to call rerank service at {}: {}", url, e.getMessage());
            return List.of();
        }
    }

    @Data
    public static class RerankRequest {
        private final String model;
        private final String query;
        private final List<String> documents;
        private final int top_n;
    }

    @Data
    public static class RerankResponse {
        private String model;
        private List<RerankResult> results;
        private int total_tokens;
    }

    @Data
    public static class RerankResult {
        private int index;
        private double relevance_score;
        private String text;
    }
}
