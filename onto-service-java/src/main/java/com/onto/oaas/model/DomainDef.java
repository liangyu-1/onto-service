package com.onto.oaas.model;

import com.fasterxml.jackson.annotation.JsonAnyGetter;
import com.fasterxml.jackson.annotation.JsonAnySetter;
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
public class DomainDef {
    private String id;
    private String name;
    private String displayName;
    private String description;

    @Builder.Default
    private Map<String, TypeDef> types = new HashMap<>();

    @JsonAnyGetter
    public Map<String, TypeDef> getTypes() {
        return types;
    }

    @JsonAnySetter
    public void setType(String key, TypeDef value) {
        this.types.put(key, value);
    }
}
