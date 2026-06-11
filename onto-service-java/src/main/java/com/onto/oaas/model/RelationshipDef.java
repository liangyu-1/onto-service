package com.onto.oaas.model;

import com.onto.oaas.model.enums.Cardinality;
import com.onto.oaas.model.enums.JoinType;
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
public class RelationshipDef {
    private String name;
    private String displayName;
    private String description;
    private List<Map<String, String>> linkProperties;
    private Cardinality cardinality;
    private JoinType type;
}
