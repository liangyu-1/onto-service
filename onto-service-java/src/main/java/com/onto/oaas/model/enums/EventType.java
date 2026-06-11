package com.onto.oaas.model.enums;

public enum EventType {
    DOMAIN_UPSERT,
    TYPE_UPSERT,
    PROPERTY_UPSERT,
    RELATIONSHIP_UPSERT,
    FUNCTION_UPSERT,
    RULE_UPSERT,
    REBUILD_INDEX,
    FULL_SYNC_REQUIRED,
    DELETE
}
