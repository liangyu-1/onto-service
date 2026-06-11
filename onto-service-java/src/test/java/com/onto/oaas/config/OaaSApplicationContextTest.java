package com.onto.oaas.config;

import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;

@SpringBootTest(classes = com.onto.oaas.OntologyServiceApplication.class)
@ActiveProfiles("test")
class OaaSApplicationContextTest {

    @Test
    void contextLoads() {
    }
}
