package com.onto.oaas.util;

import com.onto.oaas.model.enums.TBoxObjectType;

public final class ObjectPathUtil {

    private static final String FUNCTIONS = "functions";
    private static final String RULES = "rules";
    private static final String PROPERTIES = "properties";
    private static final String RELATIONSHIPS = "relationships";

    private ObjectPathUtil() {
    }

    public static String[] splitPath(String objectPath) {
        if (objectPath == null || objectPath.isBlank()) {
            return new String[0];
        }
        return objectPath.split("\\.");
    }

    public static String getDomainKey(String objectPath) {
        String[] parts = splitPath(objectPath);
        return parts.length > 0 ? parts[0] : null;
    }

    public static String getTypeKey(String objectPath) {
        String[] parts = splitPath(objectPath);
        return parts.length > 1 ? parts[1] : null;
    }

    public static String getPropertyKey(String objectPath) {
        String[] parts = splitPath(objectPath);
        // path: domain.type.properties.property_name
        if (parts.length >= 4 && PROPERTIES.equals(parts[2])) {
            return parts[3];
        }
        // fallback for old format: domain.type.property_name
        if (parts.length == 3) {
            return parts[2];
        }
        return null;
    }

    public static String getRelationshipKey(String objectPath) {
        String[] parts = splitPath(objectPath);
        // path: domain.type.relationships.relationship_name
        if (parts.length >= 4 && RELATIONSHIPS.equals(parts[2])) {
            return parts[3];
        }
        // fallback for old format: domain.type.relationship_name
        if (parts.length == 3) {
            return parts[2];
        }
        return null;
    }

    public static String getFunctionKey(String objectPath) {
        String[] parts = splitPath(objectPath);
        // path: domain.type.functions.function_name
        if (parts.length >= 4 && FUNCTIONS.equals(parts[2])) {
            return parts[3];
        }
        // fallback for old format: domain.type.function_name
        if (parts.length == 3) {
            return parts[2];
        }
        return null;
    }

    public static String getRuleKey(String objectPath) {
        String[] parts = splitPath(objectPath);
        // path: domain.type.functions.function_name.rules.rule_name
        if (parts.length >= 6 && FUNCTIONS.equals(parts[2]) && RULES.equals(parts[4])) {
            return parts[5];
        }
        // For new format path like domain.type.functions.function_key (no rule), return null
        if (parts.length == 4 && FUNCTIONS.equals(parts[2])) {
            return null;
        }
        // fallback for old format: domain.type.function_name.rule_name
        if (parts.length == 4) {
            return parts[3];
        }
        return null;
    }

    public static TBoxObjectType getObjectTypeFromPath(String objectPath) {
        String[] parts = splitPath(objectPath);
        if (parts.length == 1) {
            return TBoxObjectType.DOMAIN;
        }
        if (parts.length == 2) {
            return TBoxObjectType.TYPE;
        }
        if (parts.length >= 4) {
            String category = parts[2];
            return switch (category) {
                case PROPERTIES -> TBoxObjectType.PROPERTY;
                case RELATIONSHIPS -> TBoxObjectType.RELATIONSHIP;
                case FUNCTIONS -> {
                    if (parts.length >= 6 && RULES.equals(parts[4])) {
                        yield TBoxObjectType.RULE;
                    }
                    yield TBoxObjectType.FUNCTION;
                }
                default -> TBoxObjectType.TYPE;
            };
        }
        // fallback for old format without category layer
        if (parts.length == 3) {
            return TBoxObjectType.PROPERTY; // most common old format
        }
        return TBoxObjectType.TYPE;
    }
}
