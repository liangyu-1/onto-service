package com.onto.oaas.model;

import com.fasterxml.jackson.annotation.JsonAlias;
import com.fasterxml.jackson.annotation.JsonAnyGetter;
import com.fasterxml.jackson.annotation.JsonAnySetter;
import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.HashMap;
import java.util.Map;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class TypeDef {
    private String id;
    private String name;
    private String displayName;
    private String description;
    @JsonProperty("display_property")
    @JsonAlias("displayProperty")
    private String displayProperty;

    @Builder.Default
    private Map<String, PropertyDef> properties = new HashMap<>();

    @Builder.Default
    private Map<String, RelationshipDef> relationships = new HashMap<>();

    @Builder.Default
    private Map<String, FunctionDef> functions = new HashMap<>();

    @JsonAnyGetter
    public Map<String, PropertyDef> getProperties() {
        return properties;
    }

    @JsonAnySetter
    public void setProperty(String key, PropertyDef value) {
        this.properties.put(key, value);
    }

    public void setRelationship(String key, RelationshipDef value) {
        this.relationships.put(key, value);
    }

    public void setFunction(String key, FunctionDef value) {
        this.functions.put(key, value);
    }
}
