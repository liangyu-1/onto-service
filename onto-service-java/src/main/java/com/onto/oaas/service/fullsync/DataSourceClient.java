package com.onto.oaas.service.fullsync;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.onto.oaas.model.DatasourceDetail;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;
import org.springframework.web.util.UriComponentsBuilder;

@Slf4j
@Service
@RequiredArgsConstructor
public class DataSourceClient {

    @Value("${oaas.full-sync.base-url}")
    private String baseUrl;

    private final RestTemplate restTemplate;
    private final ObjectMapper objectMapper;

    private static final String DATASOURCE_PATH = "/ontology/api/open/datasources";

    /**
     * 查询数据源详情。
     */
    public DatasourceDetail fetchDatasourceDetail(Long datasourceId) {
        if (datasourceId == null) {
            return null;
        }
        String url = UriComponentsBuilder.fromHttpUrl(baseUrl)
                .path(DATASOURCE_PATH)
                .pathSegment(String.valueOf(datasourceId))
                .build()
                .toUriString();
        try {
            String rawJson = restTemplate.getForObject(url, String.class);
            if (rawJson == null || rawJson.isBlank()) {
                return null;
            }
            JsonNode rootNode = objectMapper.readTree(rawJson);
            if (!rootNode.has("datasource") || rootNode.get("datasource").isNull()) {
                log.warn("Datasource {} not found", datasourceId);
                return null;
            }
            return objectMapper.treeToValue(rootNode.get("datasource"), DatasourceDetail.class);
        } catch (Exception e) {
            log.error("Failed to fetch datasource detail for id={}: {}", datasourceId, e.getMessage());
            return null;
        }
    }
}
