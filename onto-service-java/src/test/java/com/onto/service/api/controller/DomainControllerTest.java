package com.onto.service.api.controller;

import com.onto.service.entity.OntologyDomain;
import com.onto.service.semantic.OntologyDomainService;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

import java.util.Arrays;

import static org.mockito.Mockito.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@WebMvcTest(DomainController.class)
public class DomainControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private OntologyDomainService domainService;

    @Test
    public void testCreateDomain() throws Exception {
        OntologyDomain domain = new OntologyDomain();
        domain.setDomainName("PlantGraph");
        domain.setVersion("1.0.0");

        when(domainService.createDomain(any(), any(), any())).thenReturn(domain);

        mockMvc.perform(post("/api/v1/domains")
                .contentType(MediaType.APPLICATION_JSON)
                .content("{\"domainName\":\"PlantGraph\",\"ddlSql\":\"CREATE...\",\"createdBy\":\"admin\"}"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.data.domainName").value("PlantGraph"));
    }

    @Test
    public void testGetDomainVersions() throws Exception {
        OntologyDomain d1 = new OntologyDomain();
        d1.setDomainName("PlantGraph");
        d1.setVersion("1.0.0");

        when(domainService.getDomainVersions("PlantGraph")).thenReturn(Arrays.asList(d1));

        mockMvc.perform(get("/api/v1/domains/PlantGraph/versions"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.data[0].version").value("1.0.0"));
    }
}
