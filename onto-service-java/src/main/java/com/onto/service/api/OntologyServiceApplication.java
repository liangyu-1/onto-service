package com.onto.service.api;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/**
 * Ontology Service Spring Boot 应用入口
 */
@SpringBootApplication(scanBasePackages = "com.onto.service")
public class OntologyServiceApplication {

    public static void main(String[] args) {
        SpringApplication.run(OntologyServiceApplication.class, args);
    }
}
