package com.onto.oaas.dto;

import jakarta.validation.constraints.Positive;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class SubgraphOptions {

    @Positive
    @Builder.Default
    private int maxNodes = 100;

    @Positive
    @Builder.Default
    private int maxEdges = 200;

    @Builder.Default
    private boolean includeNodeDetail = true;
}
