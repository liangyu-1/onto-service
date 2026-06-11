package com.onto.oaas.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class SubgraphEdgeDto {

    private String source;
    private String relationType;
    private String target;
}
