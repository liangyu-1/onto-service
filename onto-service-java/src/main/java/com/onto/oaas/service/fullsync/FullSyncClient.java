package com.onto.oaas.service.fullsync;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.onto.oaas.model.TBoxSnapshot;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;
import org.springframework.web.util.UriComponentsBuilder;

@Slf4j
@Service
@RequiredArgsConstructor
public class FullSyncClient {

    @Value("${oaas.full-sync.base-url}")
    private String baseUrl;

    @Value("${oaas.full-sync.snapshot-path:/ontology/api/open/domains}")
    private String snapshotPath;

    private final RestTemplate restTemplate;
    private final ObjectMapper objectMapper;
    private final ExternalSnapshotAdapter adapter;
    private final OntologyMgmtSnapshotAdapter ontologyMgmtAdapter;

    public TBoxSnapshot fetchSnapshot(String ontologyId, String ontologyVersion) {
        String url = buildUrl(ontologyId, ontologyVersion);
        log.info("Fetching TBox snapshot from: {}", url);

        // 先获取原始 JSON，再适配转换
        String rawJson = restTemplate.getForObject(url, String.class);
        if (rawJson == null || rawJson.isBlank()) {
            log.error("Empty response from external snapshot API");
            return null;
        }

        try {
            JsonNode rootNode = objectMapper.readTree(rawJson);

            // 判断是否是本体管理平台格式（有 "domains" 字段且外层有 code/message）
            if (rootNode.has("domains") && rootNode.has("code")) {
                log.info("Ontology management platform format detected, adapting...");
                TBoxSnapshot snapshot = ontologyMgmtAdapter.adapt(rootNode);
                log.info("Adapted snapshot: domains={}, types={}",
                        snapshot != null && snapshot.getDomains() != null ? snapshot.getDomains().size() : 0,
                        snapshot != null && snapshot.getDomains() != null && !snapshot.getDomains().isEmpty()
                                ? snapshot.getDomains().values().stream()
                                        .mapToInt(d -> d.getTypes() != null ? d.getTypes().size() : 0)
                                        .sum()
                                : 0);
                return snapshot;
            }

            // 判断是否是旧外部格式（有 "types" 字段但没有 "domains" 字段）
            if (rootNode.has("types") && !rootNode.has("domains")) {
                log.info("Legacy external snapshot format detected, adapting...");
                TBoxSnapshot snapshot = adapter.adapt(rootNode);
                log.info("Adapted snapshot: domains={}, types={}",
                        snapshot != null && snapshot.getDomains() != null ? snapshot.getDomains().size() : 0,
                        snapshot != null && snapshot.getDomains() != null && !snapshot.getDomains().isEmpty()
                                ? snapshot.getDomains().values().iterator().next().getTypes().size()
                                : 0);
                return snapshot;
            }

            // 已经是内部格式，直接解析
            TBoxSnapshot snapshot = objectMapper.readValue(rawJson, TBoxSnapshot.class);
            log.info("Fetched TBox snapshot, domains count: {}",
                    snapshot != null && snapshot.getDomains() != null ? snapshot.getDomains().size() : 0);
            return snapshot;

        } catch (Exception e) {
            log.error("Failed to parse snapshot response: {}", e.getMessage());
            return null;
        }
    }

    /**
     * 构建请求 URL。
     */
    private String buildUrl(String ontologyId, String ontologyVersion) {
        // 如果 baseUrl 已经包含完整路径，直接使用
        if (baseUrl.endsWith(snapshotPath) || baseUrl.contains("/ontology/api/open") || baseUrl.contains("/api/tpch")) {
            return baseUrl;
        }
        return UriComponentsBuilder.fromHttpUrl(baseUrl)
                .path(snapshotPath)
                .build()
                .toUriString();
    }
}
