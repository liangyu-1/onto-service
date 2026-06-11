package com.onto.oaas.controller;

import com.onto.oaas.dto.TBoxBindingDto;
import com.onto.oaas.dto.TBoxBindingsRequest;
import com.onto.oaas.dto.TBoxBindingsResponse;
import com.onto.oaas.model.Binding;
import com.onto.oaas.model.DatasourceDetail;
import com.onto.oaas.model.FunctionDef;
import com.onto.oaas.model.PropertyDef;
import com.onto.oaas.model.RuleDef;
import com.onto.oaas.model.enums.TBoxObjectType;
import com.onto.oaas.repository.TBoxGraphRepository;
import com.onto.oaas.service.fullsync.DataSourceClient;
import com.onto.oaas.util.ObjectPathUtil;
import com.onto.oaas.util.TraceIdGenerator;
import jakarta.validation.Valid;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * TBox Bindings 查询控制器。
 *
 * <p>根据 object_path 列表查询对应的数据绑定信息。</p>
 */
@RestController
@RequestMapping("/v1/tbox")
@RequiredArgsConstructor
@Slf4j
public class TBoxBindingsController {

    private final TBoxGraphRepository graphRepository;
    private final DataSourceClient dataSourceClient;

    @PostMapping("/bindings/query")
    public ResponseEntity<TBoxBindingsResponse> queryBindings(@Valid @RequestBody TBoxBindingsRequest request) {
        String queryId = TraceIdGenerator.generateQueryId();
        List<String> objectPaths = request.getObjectPaths();
        log.info("Bindings query request: queryId={}, paths={}", queryId, objectPaths);

        List<TBoxBindingDto> bindings = new ArrayList<>();
        List<String> notFound = new ArrayList<>();

        for (String objectPath : objectPaths) {
            Optional<TBoxBindingDto> dtoOpt = resolveBinding(objectPath);
            if (dtoOpt.isPresent()) {
                bindings.add(dtoOpt.get());
            } else {
                notFound.add(objectPath);
            }
        }

        return ResponseEntity.ok(TBoxBindingsResponse.builder()
                .queryId(queryId)
                .bindings(bindings)
                .notFound(notFound)
                .build());
    }

    private Optional<TBoxBindingDto> resolveBinding(String objectPath) {
        TBoxObjectType objectType = ObjectPathUtil.getObjectTypeFromPath(objectPath);
        String domainKey = ObjectPathUtil.getDomainKey(objectPath);
        String typeKey = ObjectPathUtil.getTypeKey(objectPath);

        switch (objectType) {
            case PROPERTY -> {
                Optional<PropertyDef> propOpt = graphRepository.findPropertyByPath(objectPath);
                if (propOpt.isPresent()) {
                    PropertyDef p = propOpt.get();
                    Binding binding = enrichBindingWithDatasource(p.getBinding());
                    return Optional.of(TBoxBindingDto.builder()
                            .objectPath(objectPath)
                            .objectType(TBoxObjectType.PROPERTY)
                            .name(p.getName())
                            .dataType(p.getType())
                            .binding(binding)
                            .pkColumn(p.isPkColumn())
                            .build());
                }
            }
            case RULE -> {
                Optional<Object> objOpt = graphRepository.findByObjectPath(objectPath);
                if (objOpt.isPresent() && objOpt.get() instanceof RuleDef r) {
                    return Optional.of(TBoxBindingDto.builder()
                            .objectPath(objectPath)
                            .objectType(TBoxObjectType.RULE)
                            .name(r.getName())
                            .ruleType(r.getType())
                            .definition(r.getDefinition())
                            .build());
                }
            }
            case FUNCTION -> {
                String funcKey = ObjectPathUtil.getFunctionKey(objectPath);
                if (domainKey != null && typeKey != null && funcKey != null) {
                    List<FunctionDef> funcs = graphRepository.findFunctionsByType(domainKey, typeKey);
                    Optional<FunctionDef> funcOpt = funcs.stream()
                            .filter(f -> f != null && funcKey.equals(f.getName()))
                            .findFirst();
                    if (funcOpt.isPresent()) {
                        FunctionDef f = funcOpt.get();
                        return Optional.of(TBoxBindingDto.builder()
                                .objectPath(objectPath)
                                .objectType(TBoxObjectType.FUNCTION)
                                .name(f.getName())
                                .build());
                    }
                }
            }
            default -> {
                // Domain, Type, Relationship 没有 binding 信息
                return Optional.of(TBoxBindingDto.builder()
                        .objectPath(objectPath)
                        .objectType(objectType)
                        .build());
            }
        }
        return Optional.empty();
    }

    /**
     * 实时补充 datasource 详情。若 binding 中 datasource 详情已存在则直接返回，否则调用本体管理系统接口查询。
     */
    private Binding enrichBindingWithDatasource(Binding binding) {
        if (binding == null || binding.getDatasource() == null) {
            return binding;
        }
        // 如果已经包含 datasource 详情，不再重复查询
        if (binding.getDatasourceType() != null || binding.getConnectionUrl() != null) {
            return binding;
        }
        DatasourceDetail detail = dataSourceClient.fetchDatasourceDetail(binding.getDatasource());
        if (detail == null) {
            return binding;
        }
        Binding enriched = new Binding();
        enriched.setDatasource(binding.getDatasource());
        enriched.setSchema(binding.getSchema());
        enriched.setDatabase(binding.getDatabase());
        enriched.setTable(binding.getTable());
        enriched.setColumn(binding.getColumn());
        enriched.setDatasourceName(detail.getDatasourceName());
        enriched.setDatasourceType(detail.getDatasourceType());
        enriched.setHost(detail.getHost());
        enriched.setPort(detail.getPort());
        enriched.setDatabaseName(detail.getDatabaseName());
        enriched.setDatabaseSchema(detail.getDatabaseSchema());
        enriched.setConnectionMode(detail.getConnectionMode());
        enriched.setConnectionUrl(detail.getConnectionUrl());
        enriched.setUsername(detail.getUsername());
        return enriched;
    }
}
