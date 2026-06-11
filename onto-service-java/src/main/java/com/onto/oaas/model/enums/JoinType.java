package com.onto.oaas.model.enums;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonValue;

public enum JoinType {
    INNER_JOIN("innerjoin"),
    LEFT_JOIN("leftjoin"),
    RIGHT_JOIN("rightjoin"),
    FULL_JOIN("fulljoin");

    private final String value;

    JoinType(String value) {
        this.value = value;
    }

    @JsonValue
    public String getValue() {
        return value;
    }

    @JsonCreator
    public static JoinType fromValue(String value) {
        if (value == null) return null;
        for (JoinType t : values()) {
            if (t.value.equalsIgnoreCase(value.replace("-", "").replace("_", ""))) {
                return t;
            }
        }
        try {
            return JoinType.valueOf(value.toUpperCase());
        } catch (IllegalArgumentException e) {
            return null;
        }
    }
}
