package com.onto.service.api.controller;

import com.onto.service.entity.OntologyArtifact;
import com.onto.service.semantic.artifact.OntologyArtifactService;
import com.onto.service.semantic.export.OwlExportService;
import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

import java.util.Optional;

import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

public class ArtifactControllerTest {

    private static MockMvc mockMvcFor(OntologyArtifactService artifactService, OwlExportService owlExportService) {
        ArtifactController controller = new ArtifactController();
        TestUtil.setField(controller, "artifactService", artifactService);
        TestUtil.setField(controller, "owlExportService", owlExportService);
        return MockMvcBuilders.standaloneSetup(controller).build();
    }

    @Test
    public void testExportRdfOwlReturnsExisting() throws Exception {
        OntologyArtifactService artifactService = mock(OntologyArtifactService.class);
        OwlExportService owlExportService = mock(OwlExportService.class);
        MockMvc mockMvc = mockMvcFor(artifactService, owlExportService);

        OntologyArtifact a = new OntologyArtifact();
        a.setDomainName("PlantGraph");
        a.setVersion("1.0.0");
        a.setArtifactKind("rdf_owl");
        a.setFormat("ttl");
        a.setContent("@prefix onto: <urn:onto:PlantGraph:1.0.0#> .\n");

        when(artifactService.latest(eq("PlantGraph"), eq("1.0.0"), eq("rdf_owl"), eq("ttl")))
                .thenReturn(Optional.of(a));

        mockMvc.perform(get("/api/v1/artifacts/PlantGraph/1.0.0/rdf-owl")
                        .queryParam("format", "ttl"))
                .andExpect(status().isOk())
                .andExpect(content().contentTypeCompatibleWith(MediaType.TEXT_PLAIN))
                .andExpect(content().string(a.getContent()));
    }

    @Test
    public void testUploadRdfOwl() throws Exception {
        OntologyArtifactService artifactService = mock(OntologyArtifactService.class);
        OwlExportService owlExportService = mock(OwlExportService.class);
        MockMvc mockMvc = mockMvcFor(artifactService, owlExportService);

        OntologyArtifact saved = new OntologyArtifact();
        saved.setDomainName("PlantGraph");
        saved.setVersion("1.0.0");
        saved.setArtifactKind("rdf_owl");
        saved.setFormat("ttl");
        saved.setContent("x");
        saved.setContentHash("abc");

        when(artifactService.upsert(any())).thenReturn(saved);

        mockMvc.perform(post("/api/v1/artifacts/PlantGraph/1.0.0/rdf-owl")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"format\":\"ttl\",\"baseIri\":\"urn:onto:PlantGraph:1.0.0\",\"content\":\"x\",\"createdBy\":\"admin\"}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.data.artifactKind").value("rdf_owl"))
                .andExpect(jsonPath("$.data.format").value("ttl"));
    }

    static class TestUtil {
        static void setField(Object target, String field, Object value) {
            try {
                var f = target.getClass().getDeclaredField(field);
                f.setAccessible(true);
                f.set(target, value);
            } catch (Exception e) {
                throw new RuntimeException(e);
            }
        }
    }
}

