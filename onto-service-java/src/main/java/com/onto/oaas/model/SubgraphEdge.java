package com.onto.oaas.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class SubgraphEdge {
    private String source;
    private String relationType;
    private String target;
}
