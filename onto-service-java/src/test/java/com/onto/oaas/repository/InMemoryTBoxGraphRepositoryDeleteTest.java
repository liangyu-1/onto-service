package com.onto.oaas.repository;

import static org.assertj.core.api.Assertions.assertThat;

import com.onto.oaas.model.DomainDef;
import com.onto.oaas.model.FunctionDef;
import com.onto.oaas.model.RuleDef;
import com.onto.oaas.model.PropertyDef;
import com.onto.oaas.model.RelationshipDef;
import com.onto.oaas.model.TypeDef;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

class InMemoryTBoxGraphRepositoryDeleteTest {

    private InMemoryTBoxGraphRepository repository;

    @BeforeEach
    void setUp() {
        repository = new InMemoryTBoxGraphRepository();
        seedData();
    }

    private void seedData() {
        // Domain
        repository.saveDomain(DomainDef.builder().name("Equipment Domain").description("Equipment").build(), "equipment");
        // Type
        repository.saveType(TypeDef.builder().name("Device").description("Device type").build(), "equipment", "device");
        // Property
        repository.saveProperty(PropertyDef.builder().name("Device ID").type("string").build(), "equipment", "device", "device_id");
        // Relationship
        repository.saveRelationship(RelationshipDef.builder().name("Has Fault").description("Has fault rel").build(), "equipment", "device", "has_fault");
        // Function
        repository.saveFunction(FunctionDef.builder().name("Fault Stat").description("Fault statistics").build(), "equipment", "device", "fault_stat");
        // Rule
        repository.saveRule(RuleDef.builder().name("Fault Count").description("Count of faults").build(), "equipment", "device", "fault_stat", "fault_count");
    }

    @Test
    void deleteRule_shouldRemoveRuleAndEdges() {
        assertThat(repository.exists("equipment.device.functions.fault_stat.rules.fault_count")).isTrue();
        repository.deleteRule("equipment.device.functions.fault_stat.rules.fault_count");
        assertThat(repository.exists("equipment.device.functions.fault_stat.rules.fault_count")).isFalse();
        assertThat(repository.countObjects()).isEqualTo(5); // domain + type + prop + rel + func
    }

    @Test
    void deleteFunction_shouldCascadeDeleteRules() {
        assertThat(repository.exists("equipment.device.functions.fault_stat")).isTrue();
        assertThat(repository.exists("equipment.device.functions.fault_stat.rules.fault_count")).isTrue();
        repository.deleteFunction("equipment", "device", "fault_stat");
        assertThat(repository.exists("equipment.device.functions.fault_stat")).isFalse();
        assertThat(repository.exists("equipment.device.functions.fault_stat.rules.fault_count")).isFalse();
        assertThat(repository.countObjects()).isEqualTo(4);
    }

    @Test
    void deleteType_shouldCascadeDeleteAllChildren() {
        repository.deleteType("equipment", "device");
        assertThat(repository.exists("equipment.device")).isFalse();
        assertThat(repository.exists("equipment.device.properties.device_id")).isFalse();
        assertThat(repository.exists("equipment.device.relationships.has_fault")).isFalse();
        assertThat(repository.exists("equipment.device.functions.fault_stat")).isFalse();
        assertThat(repository.exists("equipment.device.functions.fault_stat.rules.fault_count")).isFalse();
        assertThat(repository.countObjects()).isEqualTo(1); // only domain remains
    }

    @Test
    void deleteDomain_shouldCascadeDeleteEverything() {
        repository.deleteDomain("equipment");
        assertThat(repository.exists("equipment")).isFalse();
        assertThat(repository.exists("equipment.device")).isFalse();
        assertThat(repository.countObjects()).isEqualTo(0);
    }

    @Test
    void deleteProperty_shouldRemoveProperty() {
        repository.deleteProperty("equipment.device.properties.device_id");
        assertThat(repository.exists("equipment.device.properties.device_id")).isFalse();
        assertThat(repository.countObjects()).isEqualTo(5);
    }

    @Test
    void deleteRelationship_shouldRemoveRelationship() {
        repository.deleteRelationship("equipment.device.relationships.has_fault");
        assertThat(repository.exists("equipment.device.relationships.has_fault")).isFalse();
        assertThat(repository.countObjects()).isEqualTo(5);
    }
}
