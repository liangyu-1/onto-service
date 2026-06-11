package com.onto.oaas.dto;

import com.onto.oaas.model.enums.Direction;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Positive;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class TBoxSubgraphRequest {

    @NotBlank
    private String startObjectPath;

    @Positive
    @Builder.Default
    private int hops = 2;

    @Builder.Default
    private Direction direction = Direction.BOTH;

    @Valid
    @Builder.Default
    private SubgraphFilters filters = new SubgraphFilters();

    @Valid
    @Builder.Default
    private SubgraphOptions options = new SubgraphOptions();
}
