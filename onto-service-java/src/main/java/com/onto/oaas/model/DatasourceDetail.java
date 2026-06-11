package com.onto.oaas.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class DatasourceDetail {

    private Long id;
    private Long tenantId;
    private String datasourceName;
    private String datasourceType;
    private String host;
    private Integer port;
    private String databaseName;
    private String databaseSchema;
    private String databaseVersion;
    private String connectionUrl;
    private String connectionMode;
    private String username;
    private String password;
    private String description;
}
