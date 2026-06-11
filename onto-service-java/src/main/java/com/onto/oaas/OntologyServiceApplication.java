package com.onto.oaas;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.kafka.annotation.EnableKafka;

@EnableKafka
@SpringBootApplication(
    scanBasePackages = "com.onto.oaas",
    exclude = {
        org.springframework.boot.autoconfigure.jdbc.DataSourceAutoConfiguration.class
    }
)
public class OntologyServiceApplication {
    public static void main(String[] args) {
        SpringApplication.run(OntologyServiceApplication.class, args);
    }
}
