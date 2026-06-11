package com.onto.oaas.model;

import java.util.List;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class SubgraphResult {
    private String startObjectPath;
    private int hops;
    private List<SubgraphNode> nodes;
    private List<SubgraphEdge> edges;
    private boolean truncated;
}
