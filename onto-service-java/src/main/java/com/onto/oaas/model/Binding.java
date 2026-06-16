package com.onto.oaas.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class Binding {

    // 对象级绑定位置（来自本体对象定义）
    private Long datasource;
    private String schema;
    private String database;
    private String table;
    private String column;

    // 数据源详情（来自本体管理系统的 datasource 接口）
    private String datasourceName;
    private String datasourceType;
    private String host;
    private Integer port;
    private String databaseName;
    private String databaseSchema;
    private String connectionMode;
    private String connectionUrl;
    private String username;
    private String password;
}
