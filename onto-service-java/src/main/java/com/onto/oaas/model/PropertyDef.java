package com.onto.oaas.model;

import com.fasterxml.jackson.annotation.JsonAlias;
import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class PropertyDef {
    private String id;
    private String name;
    private String displayName;
    private String type;
    private String description;
    private Binding binding;
    @JsonProperty("pk_column")
    @JsonAlias("pkColumn")
    private boolean pkColumn;
}
