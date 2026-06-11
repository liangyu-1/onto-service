package com.onto.oaas.dto;

import java.util.List;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class TBoxSubgraphResponse {

    private String queryId;
    private String mode;
    private String startObjectPath;
    private int hops;
    private List<SubgraphNodeDto> nodes;
    private List<SubgraphEdgeDto> edges;
    private boolean truncated;
}
