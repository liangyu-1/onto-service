package com.onto.oaas.model;

import com.fasterxml.jackson.annotation.JsonAnyGetter;
import com.fasterxml.jackson.annotation.JsonAnySetter;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class FunctionDef {
    private String name;
    private String displayName;
    private String description;
    private String type;
    private String definition;
    private List<String> dimensions;

    @Builder.Default
    private Map<String, RuleDef> rules = new HashMap<>();

    @JsonAnyGetter
    public Map<String, RuleDef> getRules() {
        return rules;
    }

    @JsonAnySetter
    public void setRule(String key, RuleDef value) {
        this.rules.put(key, value);
    }
}
