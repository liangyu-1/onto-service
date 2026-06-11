package com.onto.oaas.service.ranking;

import java.util.List;
import java.util.Map;
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
 * Python LTR (Learning-to-Rank) 服务客户端。
 *
 * <p>调用 Python 服务的 /api/v1/ranking/predict 接口，获取排序分数。</p>
 */
@Slf4j
@Service
public class PythonLTRClient {

    @Value("${onto.grounding.python-service-url:http://localhost:5001}")
    private String baseUrl;

    private final RestTemplate restTemplate = new RestTemplate();

    /**
     * 预测候选文档的排序分数。
     */
    public List<Double> predict(List<Map<String, Object>> candidates) {
        String url = baseUrl + "/api/v1/ranking/predict";
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);

        PredictRequest request = new PredictRequest(candidates);
        HttpEntity<PredictRequest> entity = new HttpEntity<>(request, headers);

        try {
            ResponseEntity<PredictResponse> response = restTemplate.postForEntity(
                    url, entity, PredictResponse.class);
            PredictResponse body = response.getBody();
            if (body == null || body.scores == null) {
                log.warn("LTR service returned empty response");
                return List.of();
            }
            return body.scores;
        } catch (Exception e) {
            log.error("Failed to call LTR service: {}", e.getMessage());
            return List.of();
        }
    }

    /**
     * 获取模型信息。
     */
    public Map<String, Object> getModelInfo() {
        String url = baseUrl + "/api/v1/ranking/model-info";
        try {
            ResponseEntity<Map> response = restTemplate.getForEntity(url, Map.class);
            return response.getBody() != null ? response.getBody() : Map.of();
        } catch (Exception e) {
            log.error("Failed to get LTR model info: {}", e.getMessage());
            return Map.of();
        }
    }

    @Data
    public static class PredictRequest {
        private final List<Map<String, Object>> candidates;
    }

    @Data
    public static class PredictResponse {
        private List<Double> scores;
        private List<Integer> ranked_indices;
    }
}
