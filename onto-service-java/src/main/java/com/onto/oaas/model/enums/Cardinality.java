package com.onto.oaas.model.enums;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonValue;

public enum Cardinality {
    ONE2ONE("one2one"),
    ONE2MANY("one2many"),
    MANY2ONE("many2one"),
    MANY2MANY("many2many");

    private final String value;

    Cardinality(String value) {
        this.value = value;
    }

    @JsonValue
    public String getValue() {
        return value;
    }

    @JsonCreator
    public static Cardinality fromValue(String value) {
        if (value == null) return null;
        for (Cardinality c : values()) {
            if (c.value.equalsIgnoreCase(value.replace("-", "").replace("_", ""))) {
                return c;
            }
        }
        // 尝试直接匹配枚举名
        try {
            return Cardinality.valueOf(value.toUpperCase());
        } catch (IllegalArgumentException e) {
            return null;
        }
    }
}
