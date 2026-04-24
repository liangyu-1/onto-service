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

    // OntologyCatalogBuilderImpl is already a @Component, no need to define it here again
}
