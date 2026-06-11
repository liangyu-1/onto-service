package com.onto.oaas.util;

import static org.assertj.core.api.Assertions.assertThat;

import com.onto.oaas.model.enums.TBoxObjectType;
import org.junit.jupiter.api.Test;

class ObjectPathUtilTest {

    @Test
    void shouldExtractDomainKey() {
        assertThat(ObjectPathUtil.getDomainKey("equipment_domain.equipment")).isEqualTo("equipment_domain");
        assertThat(ObjectPathUtil.getDomainKey("single_domain")).isEqualTo("single_domain");
        assertThat(ObjectPathUtil.getDomainKey("")).isNull();
        assertThat(ObjectPathUtil.getDomainKey(null)).isNull();
    }

    @Test
    void shouldExtractTypeKey() {
        assertThat(ObjectPathUtil.getTypeKey("equipment_domain.equipment")).isEqualTo("equipment");
        assertThat(ObjectPathUtil.getTypeKey("equipment_domain.equipment.properties.id")).isEqualTo("equipment");
        assertThat(ObjectPathUtil.getTypeKey("single_domain")).isNull();
    }

    @Test
    void shouldExtractPropertyKey() {
        assertThat(ObjectPathUtil.getPropertyKey("equipment_domain.equipment.properties.equipment_id"))
                .isEqualTo("equipment_id");
        assertThat(ObjectPathUtil.getPropertyKey("equipment_domain.equipment.relationships.has_fault"))
                .isNull();
        assertThat(ObjectPathUtil.getPropertyKey("equipment_domain.equipment")).isNull();
    }

    @Test
    void shouldExtractRelationshipKey() {
        assertThat(ObjectPathUtil.getRelationshipKey("equipment_domain.equipment.relationships.has_fault"))
                .isEqualTo("has_fault");
        assertThat(ObjectPathUtil.getRelationshipKey("equipment_domain.equipment.properties.id"))
                .isNull();
    }

    @Test
    void shouldExtractFunctionKey() {
        assertThat(ObjectPathUtil.getFunctionKey("equipment_domain.equipment.functions.equipment_fault_stat"))
                .isEqualTo("equipment_fault_stat");
        assertThat(ObjectPathUtil.getFunctionKey("equipment_domain.equipment.rules.m1"))
                .isNull();
    }

    @Test
    void shouldExtractRuleKey() {
        assertThat(ObjectPathUtil.getRuleKey(
                "equipment_domain.equipment.functions.equipment_fault_stat.rules.fault_count"))
                .isEqualTo("fault_count");
        // Old format fallback: domain.type.functions.function_key (no rule key)
        assertThat(ObjectPathUtil.getRuleKey("equipment_domain.equipment.functions.f1"))
                .isNull();
    }

    @Test
    void shouldInferObjectTypeFromPath() {
        assertThat(ObjectPathUtil.getObjectTypeFromPath("equipment_domain")).isEqualTo(TBoxObjectType.DOMAIN);
        assertThat(ObjectPathUtil.getObjectTypeFromPath("equipment_domain.equipment")).isEqualTo(TBoxObjectType.TYPE);
        assertThat(ObjectPathUtil.getObjectTypeFromPath("equipment_domain.equipment.properties.id"))
                .isEqualTo(TBoxObjectType.PROPERTY);
        assertThat(ObjectPathUtil.getObjectTypeFromPath("equipment_domain.equipment.relationships.has_fault"))
                .isEqualTo(TBoxObjectType.RELATIONSHIP);
        assertThat(ObjectPathUtil.getObjectTypeFromPath("equipment_domain.equipment.functions.f1"))
                .isEqualTo(TBoxObjectType.FUNCTION);
        assertThat(ObjectPathUtil.getObjectTypeFromPath(
                "equipment_domain.equipment.functions.f1.rules.m1"))
                .isEqualTo(TBoxObjectType.RULE);
    }
}
