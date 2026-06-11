package com.onto.oaas.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class RuleDef {
    private String name;
    private String displayName;
    private String description;
    private String type;
    private String definition;
}
