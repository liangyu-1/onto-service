package com.onto.service.config;

import com.onto.service.catalog.OntologyCatalogBuilder;
import com.onto.service.catalog.impl.OntologyCatalogBuilderImpl;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * GoogleSQL 配置
 */
@Configuration
public class GoogleSqlConfig {

    @Bean
    public OntologyCatalogBuilder ontologyCatalogBuilder() {
        return new OntologyCatalogBuilderImpl();
    }
}
