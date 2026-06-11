package com.onto.oaas.service.query;

import com.onto.oaas.model.QueryIntentV2;
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
 * Python 查询理解服务客户端。
 *
 * <p>调用 Python 服务的 /api/v1/query/analyze 接口，获取语义查询理解结果。</p>
 */
@Slf4j
@Service
public class PythonQueryUnderstandingClient {

    @Value("${onto.grounding.python-service-url:http://localhost:5001}")
    private String baseUrl;

    private final RestTemplate restTemplate = new RestTemplate();

    /**
     * 分析查询意图、实体链接、结构约束。
     */
    public QueryIntentV2 analyze(String query) {
        String url = baseUrl + "/api/v1/query/analyze";
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);

        AnalyzeRequest request = new AnalyzeRequest(query);
        HttpEntity<AnalyzeRequest> entity = new HttpEntity<>(request, headers);

        try {
            ResponseEntity<AnalyzeResponse> response = restTemplate.postForEntity(
                    url, entity, AnalyzeResponse.class);
            AnalyzeResponse body = response.getBody();
            if (body == null) {
                log.warn("Query understanding service returned empty response");
                return null;
            }
            return toQueryIntentV2(body);
        } catch (Exception e) {
            log.error("Failed to call query understanding service: {}", e.getMessage());
            return null;
        }
    }

    private QueryIntentV2 toQueryIntentV2(AnalyzeResponse resp) {
        List<QueryIntentV2.StructureConstraint> constraints = resp.constraints != null
                ? resp.constraints.stream()
                    .map(c -> QueryIntentV2.StructureConstraint.builder()
                            .type(c.get("type"))
                            .value(c.get("value"))
                            .description(c.get("description"))
                            .build())
                    .toList()
                : List.of();

        return QueryIntentV2.builder()
                .intent(resp.intent)
                .linkedEntityPaths(resp.linked_entities != null ? resp.linked_entities : List.of())
                .constraints(constraints)
                .expandedQueries(resp.expanded_queries != null ? resp.expanded_queries : List.of())
                .keywordHints(resp.keywords != null ? resp.keywords : List.of())
                .build();
    }

    @Data
    public static class AnalyzeRequest {
        private final String query;
    }

    @Data
    public static class AnalyzeResponse {
        private String intent;
        private List<String> linked_entities;
        private List<Map<String, String>> constraints;
        private List<String> expanded_queries;
        private List<String> keywords;
        private double confidence;
    }
}
