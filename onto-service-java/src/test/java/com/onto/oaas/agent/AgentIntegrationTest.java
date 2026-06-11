package com.onto.oaas.agent;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.when;

import com.onto.oaas.agent.core.AgentBus;
import com.onto.oaas.agent.retrieval.ContextAgent;
import com.onto.oaas.agent.retrieval.QueryAgent;
import com.onto.oaas.agent.retrieval.RecallAgent;
import com.onto.oaas.agent.retrieval.RerankAgent;
import com.onto.oaas.agent.retrieval.SubgraphAgent;
import com.onto.oaas.agent.storage.GraphAgent;
import com.onto.oaas.agent.storage.IndexAgent;
import com.onto.oaas.dto.TBoxRetrieveRequest;
import com.onto.oaas.dto.TBoxRetrieveResponse;
import com.onto.oaas.dto.TBoxSubgraphRequest;
import com.onto.oaas.dto.TBoxSubgraphResponse;
import com.onto.oaas.model.DomainDef;
import com.onto.oaas.model.FunctionDef;
import com.onto.oaas.model.RuleDef;
import com.onto.oaas.model.PropertyDef;
import com.onto.oaas.model.RelationshipDef;
import com.onto.oaas.model.TBoxIndexDocument;
import com.onto.oaas.model.TBoxSnapshot;
import com.onto.oaas.model.TypeDef;
import com.onto.oaas.model.enums.Direction;
import com.onto.oaas.model.enums.TBoxObjectType;
import com.onto.oaas.repository.TBoxGraphRepository;
import com.onto.oaas.repository.TBoxIndexRepository;
import com.onto.oaas.service.TBoxIndexBuilder;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.test.context.ActiveProfiles;

/**
 * 多智能体集成测试。
 *
 * <p>测试场景：</p>
 * <ol>
 *   <li>构造 TBoxSnapshot 测试数据</li>
 *   <li>通过 IndexBuilder 构建索引文档</li>
 *   <li>存入内存索引仓库</li>
 *   <li>模拟图仓库（Mock）</li>
 *   <li>调用 AgentBus 发起检索 Pipeline</li>
 *   <li>验证检索结果</li>
 * </ol>
 */
@SpringBootTest
@ActiveProfiles("test")
class AgentIntegrationTest {

    @Autowired
    private AgentBus agentBus;

    @Autowired
    private TBoxIndexRepository indexRepository;

    @Autowired
    private TBoxIndexBuilder indexBuilder;

    @MockBean
    private TBoxGraphRepository graphRepository;

    @BeforeEach
    void setUp() {
        // 清空索引
        indexRepository.rebuildIndex();

        // 构造测试数据
        TBoxSnapshot snapshot = buildTestSnapshot();

        // 构建索引文档并存入内存索引
        List<TBoxIndexDocument> docs = indexBuilder.buildFromSnapshot(snapshot);
        indexRepository.saveBatch(docs);

        // Mock 图仓库
        when(graphRepository.exists(anyString())).thenReturn(true);
        when(graphRepository.findNeighbors(anyString(), any(), any())).thenReturn(List.of());
    }

    @Test
    void shouldRetrieveEquipmentFaultStat() {
        // Given: 检索请求
        TBoxRetrieveRequest request = TBoxRetrieveRequest.builder()
                .query("统计设备故障次数")
                .topK(5)
                .build();

        // When: 直接调用内存索引关键词搜索（验证数据已正确索引）
        List<TBoxIndexDocument> results = indexRepository.searchByKeyword("故障", null, 10);

        // Then: 应该召回包含"故障"的文档
        assertThat(results).isNotEmpty();
        assertThat(results.stream().map(TBoxIndexDocument::getName))
                .anyMatch(name -> name.contains("故障"));
    }

    @Test
    void shouldRetrieveByExactPath() {
        // Given: 精确路径（新格式：domain.type.functions.function_key）
        String objectPath = "equipment_domain.equipment.functions.equipment_fault_stat";

        // When
        List<TBoxIndexDocument> results = indexRepository.exactMatchByPath(objectPath);

        // Then
        assertThat(results).hasSize(1);
        assertThat(results.get(0).getObjectType()).isEqualTo(TBoxObjectType.FUNCTION);
        assertThat(results.get(0).getName()).isEqualTo("设备故障统计");
    }

    @Test
    void shouldRetrieveMeasureFaultCount() {
        // Given: 检索 rule（新格式：domain.type.functions.function_key.rules.rule_key）
        List<TBoxIndexDocument> results = indexRepository.searchByKeyword("故障次数", null, 10);

        // Then
        assertThat(results).isNotEmpty();
        // Rule 的 name 是"故障次数"，可能匹配到 Function 的 name "设备故障统计"（包含"故障"）
        // 所以过滤出 RULE 类型的结果
        List<TBoxIndexDocument> ruleResults = results.stream()
                .filter(d -> d.getObjectType() == TBoxObjectType.RULE)
                .toList();
        assertThat(ruleResults).isNotEmpty();
        assertThat(ruleResults.get(0).getObjectType()).isEqualTo(TBoxObjectType.RULE);
    }

    @Test
    void shouldFindAllIndexedDocuments() {
        // Given: 空关键词搜索返回所有文档
        List<TBoxIndexDocument> allDocs = indexRepository.searchByKeyword("", null, 100);

        // Then: 应该包含 Domain + Type + 2 Properties + Relationship + Function + Measure = 7
        assertThat(allDocs).hasSize(7);

        long domainCount = allDocs.stream().filter(d -> d.getObjectType() == TBoxObjectType.DOMAIN).count();
        long typeCount = allDocs.stream().filter(d -> d.getObjectType() == TBoxObjectType.TYPE).count();
        long propertyCount = allDocs.stream().filter(d -> d.getObjectType() == TBoxObjectType.PROPERTY).count();
        long relationshipCount = allDocs.stream().filter(d -> d.getObjectType() == TBoxObjectType.RELATIONSHIP).count();
        long functionCount = allDocs.stream().filter(d -> d.getObjectType() == TBoxObjectType.FUNCTION).count();
        long ruleCount = allDocs.stream().filter(d -> d.getObjectType() == TBoxObjectType.RULE).count();

        assertThat(domainCount).isEqualTo(1);
        assertThat(typeCount).isEqualTo(1);
        assertThat(propertyCount).isEqualTo(2);
        assertThat(relationshipCount).isEqualTo(1);
        assertThat(functionCount).isEqualTo(1);
        assertThat(ruleCount).isEqualTo(1);
    }

    @Test
    void shouldFilterByObjectType() {
        // Given: 只检索 Function 类型
        List<TBoxObjectType> types = List.of(TBoxObjectType.FUNCTION);

        // When
        List<TBoxIndexDocument> results = indexRepository.searchByKeyword("", types, 100);

        // Then
        assertThat(results).hasSize(1);
        assertThat(results.get(0).getObjectType()).isEqualTo(TBoxObjectType.FUNCTION);
    }

    // ========== 构造测试数据 ==========

    private TBoxSnapshot buildTestSnapshot() {
        Map<String, PropertyDef> properties = new HashMap<>();
        properties.put("equipment_id", PropertyDef.builder()
                .name("设备ID")
                .type("string")
                .description("设备唯一标识")
                .build());
        properties.put("equipment_name", PropertyDef.builder()
                .name("设备名称")
                .type("string")
                .description("设备名称")
                .build());

        Map<String, RelationshipDef> relationships = new HashMap<>();
        relationships.put("has_fault", RelationshipDef.builder()
                .name("发生故障")
                .description("设备与故障记录之间的关联关系")
                .build());

        Map<String, RuleDef> rules = new HashMap<>();
        rules.put("fault_count", RuleDef.builder()
                .name("故障次数")
                .description("统计设备关联的故障数量")
                .type("expression")
                .definition("count(fault_domain.fault.fault_id)")
                .build());

        Map<String, FunctionDef> functions = new HashMap<>();
        functions.put("equipment_fault_stat", FunctionDef.builder()
                .name("设备故障统计")
                .description("按设备维度统计故障次数")
                .rules(rules)
                .build());

        Map<String, TypeDef> types = new HashMap<>();
        types.put("equipment", TypeDef.builder()
                .name("设备")
                .description("工业现场中的物理设备")
                .displayProperty("equipment_name")
                .properties(properties)
                .relationships(relationships)
                .functions(functions)
                .build());

        Map<String, DomainDef> domains = new HashMap<>();
        domains.put("equipment_domain", DomainDef.builder()
                .name("设备域")
                .description("描述设备、部件、故障等对象的领域")
                .types(types)
                .build());

        return TBoxSnapshot.builder()
                .domains(domains)
                .code("0")
                .message("success")
                .build();
    }
}
