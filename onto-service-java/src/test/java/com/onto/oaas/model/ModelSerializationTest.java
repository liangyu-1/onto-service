package com.onto.oaas.model;

import static org.assertj.core.api.Assertions.assertThat;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import com.onto.oaas.model.enums.Cardinality;
import com.onto.oaas.model.enums.JoinType;
import com.onto.oaas.model.enums.TBoxObjectType;
import com.onto.oaas.model.event.KafkaEventEnvelope;
import com.onto.oaas.model.event.TBoxPayload;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

class ModelSerializationTest {

    private ObjectMapper objectMapper;

    @BeforeEach
    void setUp() {
        objectMapper = new ObjectMapper();
        objectMapper.registerModule(new JavaTimeModule());
    }

    @Test
    void shouldSerializeAndDeserializeTBoxSnapshot() throws JsonProcessingException {
        Binding binding = Binding.builder()
                .datasource(1L)
                .schema("prod")
                .database("ontology")
                .table("equipment")
                .column("equipment_name")
                .build();

        PropertyDef equipmentName = PropertyDef.builder()
                .name("equipment_name")
                .type("string")
                .description("设备名称")
                .binding(binding)
                .pkColumn(false)
                .build();

        PropertyDef equipmentId = PropertyDef.builder()
                .name("equipment_id")
                .type("string")
                .description("设备编号")
                .pkColumn(true)
                .build();

        Map<String, String> linkProp = Map.of("equipment_domain.equipment.equipment_id", "fault_domain.fault.equipment_id");

        RelationshipDef hasFault = RelationshipDef.builder()
                .name("has_fault")
                .description("设备存在故障")
                .linkProperties(List.of(linkProp))
                .cardinality(Cardinality.ONE2MANY)
                .type(JoinType.LEFT_JOIN)
                .build();

        RuleDef faultCount = RuleDef.builder()
                .name("fault_count")
                .description("故障次数")
                .type("expression")
                .definition("count(fault_id)")
                .build();

        FunctionDef equipmentFaultStat = FunctionDef.builder()
                .name("equipment_fault_stat")
                .description("设备故障统计")
                .dimensions(List.of("equipment_id"))
                .build();
        equipmentFaultStat.setRule("fault_count", faultCount);

        TypeDef equipment = TypeDef.builder()
                .name("equipment")
                .description("设备类型")
                .displayProperty("equipment_name")
                .build();
        equipment.setProperty("equipment_id", equipmentId);
        equipment.setProperty("equipment_name", equipmentName);
        equipment.setRelationship("has_fault", hasFault);
        equipment.setFunction("equipment_fault_stat", equipmentFaultStat);

        DomainDef equipmentDomain = DomainDef.builder()
                .name("equipment_domain")
                .description("设备领域")
                .build();
        equipmentDomain.setType("equipment", equipment);

        TBoxSnapshot snapshot = TBoxSnapshot.builder()
                .timestamp("2024-01-01T00:00:00Z")
                .code("200")
                .message("ok")
                .build();
        snapshot.setDomain("equipment_domain", equipmentDomain);

        String json = objectMapper.writeValueAsString(snapshot);
        assertThat(json).isNotBlank();

        TBoxSnapshot deserialized = objectMapper.readValue(json, TBoxSnapshot.class);
        assertThat(deserialized.getTimestamp()).isEqualTo("2024-01-01T00:00:00Z");
        assertThat(deserialized.getCode()).isEqualTo("200");
        assertThat(deserialized.getMessage()).isEqualTo("ok");
        assertThat(deserialized.getDomains()).containsKey("equipment_domain");

        DomainDef domain = deserialized.getDomains().get("equipment_domain");
        assertThat(domain.getName()).isEqualTo("equipment_domain");
        assertThat(domain.getDescription()).isEqualTo("设备领域");
        assertThat(domain.getTypes()).containsKey("equipment");

        TypeDef type = domain.getTypes().get("equipment");
        assertThat(type.getName()).isEqualTo("equipment");
        assertThat(type.getDisplayProperty()).isEqualTo("equipment_name");
        assertThat(type.getProperties()).containsKeys("equipment_id", "equipment_name");
        assertThat(type.getRelationships()).containsKey("has_fault");
        assertThat(type.getFunctions()).containsKey("equipment_fault_stat");

        PropertyDef prop = type.getProperties().get("equipment_name");
        assertThat(prop.getName()).isEqualTo("equipment_name");
        assertThat(prop.getType()).isEqualTo("string");
        assertThat(prop.getDescription()).isEqualTo("设备名称");
        assertThat(prop.isPkColumn()).isFalse();
        assertThat(prop.getBinding()).isNotNull();
        assertThat(prop.getBinding().getColumn()).isEqualTo("equipment_name");

        RelationshipDef rel = type.getRelationships().get("has_fault");
        assertThat(rel.getName()).isEqualTo("has_fault");
        assertThat(rel.getCardinality()).isEqualTo(Cardinality.ONE2MANY);
        assertThat(rel.getType()).isEqualTo(JoinType.LEFT_JOIN);
        assertThat(rel.getLinkProperties()).hasSize(1);

        FunctionDef func = type.getFunctions().get("equipment_fault_stat");
        assertThat(func.getName()).isEqualTo("equipment_fault_stat");
        assertThat(func.getRules()).containsKey("fault_count");

        RuleDef rule = func.getRules().get("fault_count");
        assertThat(rule.getName()).isEqualTo("fault_count");
    }

    @Test
    void shouldSerializeAndDeserializeKafkaEventEnvelope() throws JsonProcessingException {
        DomainDef domain = DomainDef.builder()
                .name("test_domain")
                .description("测试领域")
                .build();

        TBoxPayload payload = TBoxPayload.builder()
                .timestamp("2024-06-01T12:00:00Z")
                .code("200")
                .message("success")
                .build();
        payload.setDomain("test_domain", domain);

        KafkaEventEnvelope<TBoxPayload> envelope = KafkaEventEnvelope.<TBoxPayload>builder()
                .eventId("evt-123")
                .eventType("TBOX_UPSERT")
                .schemaVersion("1.0")
                .publishTime(Instant.parse("2024-06-01T12:00:00Z"))
                .payload(payload)
                .build();

        String json = objectMapper.writeValueAsString(envelope);
        assertThat(json).isNotBlank();

        KafkaEventEnvelope<?> deserialized = objectMapper.readValue(json, KafkaEventEnvelope.class);
        assertThat(deserialized.getEventId()).isEqualTo("evt-123");
        assertThat(deserialized.getEventType()).isEqualTo("TBOX_UPSERT");
        assertThat(deserialized.getSchemaVersion()).isEqualTo("1.0");
        assertThat(deserialized.getPublishTime()).isEqualTo(Instant.parse("2024-06-01T12:00:00Z"));

        TBoxPayload deserializedPayload = objectMapper.convertValue(deserialized.getPayload(), TBoxPayload.class);
        assertThat(deserializedPayload.getTimestamp()).isEqualTo("2024-06-01T12:00:00Z");
        assertThat(deserializedPayload.getCode()).isEqualTo("200");
        assertThat(deserializedPayload.getMessage()).isEqualTo("success");
        assertThat(deserializedPayload.getDomains()).containsKey("test_domain");
    }

    @Test
    void shouldSerializeAndDeserializeBinding() throws JsonProcessingException {
        Binding binding = Binding.builder()
                .datasource(1L)
                .schema("public")
                .database("db1")
                .table("t1")
                .column("c1")
                .build();

        String json = objectMapper.writeValueAsString(binding);
        Binding deserialized = objectMapper.readValue(json, Binding.class);

        assertThat(deserialized.getDatasource()).isEqualTo(1L);
        assertThat(deserialized.getSchema()).isEqualTo("public");
        assertThat(deserialized.getDatabase()).isEqualTo("db1");
        assertThat(deserialized.getTable()).isEqualTo("t1");
        assertThat(deserialized.getColumn()).isEqualTo("c1");
    }

    @Test
    void shouldSerializeAndDeserializeLinkProperty() throws JsonProcessingException {
        LinkProperty link = LinkProperty.builder()
                .sourcePath(Map.of("domain", "d1", "type", "t1"))
                .targetPath(Map.of("domain", "d2", "type", "t2"))
                .build();

        String json = objectMapper.writeValueAsString(link);
        LinkProperty deserialized = objectMapper.readValue(json, LinkProperty.class);

        assertThat(deserialized.getSourcePath()).containsEntry("domain", "d1");
        assertThat(deserialized.getTargetPath()).containsEntry("type", "t2");
    }

    @Test
    void shouldSerializeAndDeserializePropertyDef() throws JsonProcessingException {
        PropertyDef property = PropertyDef.builder()
                .name("p1")
                .type("int")
                .description("desc")
                .pkColumn(true)
                .build();

        String json = objectMapper.writeValueAsString(property);
        PropertyDef deserialized = objectMapper.readValue(json, PropertyDef.class);

        assertThat(deserialized.getName()).isEqualTo("p1");
        assertThat(deserialized.getType()).isEqualTo("int");
        assertThat(deserialized.getDescription()).isEqualTo("desc");
        assertThat(deserialized.isPkColumn()).isTrue();
    }

    @Test
    void shouldSerializeAndDeserializeRelationshipDef() throws JsonProcessingException {
        RelationshipDef rel = RelationshipDef.builder()
                .name("r1")
                .description("rel desc")
                .cardinality(Cardinality.MANY2MANY)
                .type(JoinType.INNER_JOIN)
                .build();

        String json = objectMapper.writeValueAsString(rel);
        RelationshipDef deserialized = objectMapper.readValue(json, RelationshipDef.class);

        assertThat(deserialized.getName()).isEqualTo("r1");
        assertThat(deserialized.getDescription()).isEqualTo("rel desc");
        assertThat(deserialized.getCardinality()).isEqualTo(Cardinality.MANY2MANY);
        assertThat(deserialized.getType()).isEqualTo(JoinType.INNER_JOIN);
    }

    @Test
    void shouldSerializeAndDeserializeFunctionDef() throws JsonProcessingException {
        FunctionDef function = FunctionDef.builder()
                .name("f1")
                .description("func desc")
                .dimensions(List.of("d1"))
                .build();

        String json = objectMapper.writeValueAsString(function);
        FunctionDef deserialized = objectMapper.readValue(json, FunctionDef.class);

        assertThat(deserialized.getName()).isEqualTo("f1");
        assertThat(deserialized.getDescription()).isEqualTo("func desc");
        assertThat(deserialized.getDimensions()).containsExactly("d1");
        assertThat(deserialized.getRules()).isEmpty();
    }

    @Test
    void shouldSerializeAndDeserializeRuleDef() throws JsonProcessingException {
        RuleDef rule = RuleDef.builder()
                .name("m1")
                .description("rule desc")
                .type("expression")
                .definition("sum(fault_count)")
                .build();

        String json = objectMapper.writeValueAsString(rule);
        RuleDef deserialized = objectMapper.readValue(json, RuleDef.class);

        assertThat(deserialized.getName()).isEqualTo("m1");
        assertThat(deserialized.getDescription()).isEqualTo("rule desc");
        assertThat(deserialized.getType()).isEqualTo("expression");
        assertThat(deserialized.getDefinition()).isEqualTo("sum(fault_count)");
    }
}
