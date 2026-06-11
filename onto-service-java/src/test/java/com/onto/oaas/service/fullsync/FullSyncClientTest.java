package com.onto.oaas.service.fullsync;

import static org.assertj.core.api.Assertions.assertThat;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.onto.oaas.model.DomainDef;
import com.onto.oaas.model.TBoxSnapshot;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.test.web.client.MockRestServiceServer;
import org.springframework.test.web.client.match.MockRestRequestMatchers;
import org.springframework.test.web.client.response.MockRestResponseCreators;
import org.springframework.web.client.RestTemplate;

class FullSyncClientTest {

    private RestTemplate restTemplate;
    private MockRestServiceServer mockServer;
    private FullSyncClient fullSyncClient;

    @BeforeEach
    void setUp() {
        restTemplate = new RestTemplate();
        mockServer = MockRestServiceServer.createServer(restTemplate);
        ObjectMapper objectMapper = new ObjectMapper();
        ExternalSnapshotAdapter adapter = new ExternalSnapshotAdapter(objectMapper);
        OntologyMgmtSnapshotAdapter ontologyMgmtAdapter = new OntologyMgmtSnapshotAdapter(objectMapper);
        fullSyncClient = new FullSyncClient(restTemplate, objectMapper, adapter, ontologyMgmtAdapter);
        // baseUrl and snapshotPath are injected via @Value; use reflection to set them for test
        org.springframework.test.util.ReflectionTestUtils.setField(fullSyncClient, "baseUrl", "http://localhost:8081");
        org.springframework.test.util.ReflectionTestUtils.setField(fullSyncClient, "snapshotPath", "/api/snapshot");
    }

    @Test
    void shouldFetchSnapshot() throws Exception {
        TBoxSnapshot snapshot = TBoxSnapshot.builder()
                .timestamp("2024-01-01T00:00:00Z")
                .code("200")
                .message("ok")
                .build();
        DomainDef domain = DomainDef.builder()
                .name("equipment_domain")
                .description("设备领域")
                .build();
        snapshot.setDomain("equipment_domain", domain);

        ObjectMapper objectMapper = new ObjectMapper();
        String json = objectMapper.writeValueAsString(snapshot);

        mockServer.expect(MockRestRequestMatchers.requestTo("http://localhost:8081/api/snapshot"))
                .andRespond(MockRestResponseCreators.withSuccess(json, MediaType.APPLICATION_JSON));

        TBoxSnapshot result = fullSyncClient.fetchSnapshot("ont-1", "v1");
        assertThat(result).isNotNull();
        assertThat(result.getTimestamp()).isEqualTo("2024-01-01T00:00:00Z");
        assertThat(result.getDomains()).containsKey("equipment_domain");

        mockServer.verify();
    }

    @Test
    void shouldFetchSnapshotWithEmptyDomains() throws Exception {
        TBoxSnapshot snapshot = TBoxSnapshot.builder()
                .timestamp("2024-02-01T00:00:00Z")
                .code("200")
                .message("ok")
                .build();

        ObjectMapper objectMapper = new ObjectMapper();
        String json = objectMapper.writeValueAsString(snapshot);

        mockServer.expect(MockRestRequestMatchers.requestTo("http://localhost:8081/api/snapshot"))
                .andRespond(MockRestResponseCreators.withSuccess(json, MediaType.APPLICATION_JSON));

        TBoxSnapshot result = fullSyncClient.fetchSnapshot("ont-2", "v2");
        assertThat(result).isNotNull();
        assertThat(result.getDomains()).isEmpty();

        mockServer.verify();
    }

    @Test
    void shouldFetchSnapshotWithComplexStructure() throws Exception {
        TBoxSnapshot snapshot = TBoxSnapshot.builder()
                .timestamp("2024-03-01T00:00:00Z")
                .code("200")
                .message("ok")
                .build();

        DomainDef d1 = DomainDef.builder().name("d1").description("domain1").build();
        DomainDef d2 = DomainDef.builder().name("d2").description("domain2").build();
        snapshot.setDomain("d1", d1);
        snapshot.setDomain("d2", d2);

        ObjectMapper objectMapper = new ObjectMapper();
        String json = objectMapper.writeValueAsString(snapshot);

        mockServer.expect(MockRestRequestMatchers.requestTo("http://localhost:8081/api/snapshot"))
                .andRespond(MockRestResponseCreators.withSuccess(json, MediaType.APPLICATION_JSON));

        TBoxSnapshot result = fullSyncClient.fetchSnapshot("ont-3", "v3");
        assertThat(result).isNotNull();
        assertThat(result.getDomains()).hasSize(2);
        assertThat(result.getDomains()).containsKeys("d1", "d2");

        mockServer.verify();
    }
}
