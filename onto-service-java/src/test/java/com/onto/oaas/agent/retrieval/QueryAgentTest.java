package com.onto.oaas.agent.retrieval;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;

import com.onto.oaas.agent.core.AgentBus;
import com.onto.oaas.model.QueryIntent;
import com.onto.oaas.model.enums.TBoxObjectType;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.context.ApplicationEventPublisher;

class QueryAgentTest {

    private QueryAgent queryAgent;

    @BeforeEach
    void setUp() {
        ApplicationEventPublisher publisher = mock(ApplicationEventPublisher.class);
        AgentBus agentBus = new AgentBus(publisher);
        queryAgent = new QueryAgent(agentBus);
    }

    @Test
    void shouldDetectDomainIntent() {
        QueryIntent intent = queryAgent.analyze("有哪些领域");
        assertThat(intent.getObjectTypeHints()).contains(TBoxObjectType.DOMAIN.name());
    }

    @Test
    void shouldDetectTypeIntent() {
        QueryIntent intent = queryAgent.analyze("查询所有类型");
        assertThat(intent.getObjectTypeHints()).contains(TBoxObjectType.TYPE.name());
    }

    @Test
    void shouldDetectPropertyIntent() {
        QueryIntent intent = queryAgent.analyze("设备的属性有哪些");
        assertThat(intent.getObjectTypeHints()).contains(TBoxObjectType.PROPERTY.name());
    }

    @Test
    void shouldDetectRelationshipIntent() {
        QueryIntent intent = queryAgent.analyze("存在什么关系");
        assertThat(intent.getObjectTypeHints()).contains(TBoxObjectType.RELATIONSHIP.name());
    }

    @Test
    void shouldDetectFunctionIntent() {
        QueryIntent intent = queryAgent.analyze("有哪些函数");
        assertThat(intent.getObjectTypeHints()).contains(TBoxObjectType.FUNCTION.name());
    }

    @Test
    void shouldDetectRuleIntent() {
        QueryIntent intent = queryAgent.analyze("统计规则有哪些");
        assertThat(intent.getObjectTypeHints()).contains(TBoxObjectType.RULE.name());
    }

    @Test
    void shouldHandleEmptyQuery() {
        QueryIntent intent = queryAgent.analyze("");
        assertThat(intent.getObjectTypeHints()).isEmpty();
        assertThat(intent.getPossibleObjectPaths()).isEmpty();
        assertThat(intent.getKeywordHints()).isEmpty();
    }

    @Test
    void shouldHandleNullQuery() {
        QueryIntent intent = queryAgent.analyze(null);
        assertThat(intent.getObjectTypeHints()).isEmpty();
        assertThat(intent.getPossibleObjectPaths()).isEmpty();
        assertThat(intent.getKeywordHints()).isEmpty();
    }

    @Test
    void shouldExtractPossiblePaths() {
        QueryIntent intent = queryAgent.analyze("equipment_domain.equipment.properties.id");
        assertThat(intent.getPossibleObjectPaths()).contains("equipment_domain.equipment.properties.id");
    }

    @Test
    void shouldExtractKeywords() {
        QueryIntent intent = queryAgent.analyze("查询 设备 的 属性");
        assertThat(intent.getKeywordHints()).contains("查询", "设备", "属性");
    }
}
