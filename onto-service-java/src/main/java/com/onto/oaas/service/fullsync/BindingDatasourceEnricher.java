package com.onto.oaas.service.fullsync;

import com.onto.oaas.model.Binding;
import com.onto.oaas.model.DatasourceDetail;
import com.onto.oaas.model.DomainDef;
import com.onto.oaas.model.PropertyDef;
import com.onto.oaas.model.TBoxSnapshot;
import com.onto.oaas.model.TypeDef;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

@Slf4j
@Service
@RequiredArgsConstructor
public class BindingDatasourceEnricher {

    private final DataSourceClient dataSourceClient;

    /**
     * 遍历 snapshot 中所有 Property 的 binding，补充 datasource 详情。
     */
    public void enrich(TBoxSnapshot snapshot) {
        if (snapshot == null || snapshot.getDomains() == null) {
            return;
        }
        // 1. 收集所有 datasourceId
        Set<Long> datasourceIds = new HashSet<>();
        for (DomainDef domain : snapshot.getDomains().values()) {
            if (domain.getTypes() == null) {
                continue;
            }
            for (TypeDef type : domain.getTypes().values()) {
                if (type.getProperties() == null) {
                    continue;
                }
                for (PropertyDef property : type.getProperties().values()) {
                    Binding binding = property.getBinding();
                    if (binding != null && binding.getDatasource() != null) {
                        datasourceIds.add(binding.getDatasource());
                    }
                }
            }
        }
        if (datasourceIds.isEmpty()) {
            return;
        }

        // 2. 批量获取 datasource 详情（逐个调用，缓存结果）
        Map<Long, DatasourceDetail> detailMap = new HashMap<>();
        for (Long id : datasourceIds) {
            DatasourceDetail detail = dataSourceClient.fetchDatasourceDetail(id);
            if (detail != null) {
                detailMap.put(id, detail);
                log.info("[DataSourceEnrich] Fetched datasource detail: id={}, name={}, type={}",
                        detail.getId(), detail.getDatasourceName(), detail.getDatasourceType());
            }
        }

        // 3. 填充到 binding
        for (DomainDef domain : snapshot.getDomains().values()) {
            if (domain.getTypes() == null) {
                continue;
            }
            for (TypeDef type : domain.getTypes().values()) {
                if (type.getProperties() == null) {
                    continue;
                }
                for (PropertyDef property : type.getProperties().values()) {
                    Binding binding = property.getBinding();
                    if (binding == null || binding.getDatasource() == null) {
                        continue;
                    }
                    DatasourceDetail detail = detailMap.get(binding.getDatasource());
                    if (detail != null) {
                        fillBinding(binding, detail);
                    }
                }
            }
        }
    }

    private void fillBinding(Binding binding, DatasourceDetail detail) {
        binding.setDatasourceName(detail.getDatasourceName());
        binding.setDatasourceType(detail.getDatasourceType());
        binding.setHost(detail.getHost());
        binding.setPort(detail.getPort());
        binding.setDatabaseName(detail.getDatabaseName());
        binding.setDatabaseSchema(detail.getDatabaseSchema());
        binding.setConnectionMode(detail.getConnectionMode());
        binding.setConnectionUrl(detail.getConnectionUrl());
        binding.setUsername(detail.getUsername());
    }
}
