package com.onto.oaas.service.health;

import org.neo4j.driver.Driver;
import org.springframework.boot.actuate.health.Health;
import org.springframework.boot.actuate.health.HealthIndicator;
import org.springframework.stereotype.Component;
import javax.sql.DataSource;
import java.sql.Connection;
import java.util.Optional;

@Component
public class OaaSHealthIndicator implements HealthIndicator {
    private final Driver neo4jDriver;
    private final Optional<DataSource> dataSource;

    public OaaSHealthIndicator(Driver neo4jDriver, Optional<DataSource> dataSource) {
        this.neo4jDriver = neo4jDriver;
        this.dataSource = dataSource;
    }

    @Override
    public Health health() {
        Health.Builder builder = Health.up();
        
        try {
            neo4jDriver.verifyConnectivity();
            builder.withDetail("neo4j", "UP");
        } catch (Exception e) {
            builder.down().withDetail("neo4j", "Connection failed: " + e.getMessage());
        }
        
        dataSource.ifPresentOrElse(ds -> {
            try (Connection conn = ds.getConnection()) {
                if (conn.isValid(5)) {
                    builder.withDetail("database", "UP");
                } else {
                    builder.withDetail("database", "Connection invalid");
                }
            } catch (Exception e) {
                builder.withDetail("database", "Connection failed: " + e.getMessage());
            }
        }, () -> builder.withDetail("database", "Not configured (using in-memory mode)"));
        
        return builder.build();
    }
}
