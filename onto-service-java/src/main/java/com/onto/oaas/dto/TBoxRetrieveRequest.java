package com.onto.oaas.dto;

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
public class TBoxRetrieveRequest {

    @NotBlank
    private String query;

    @Positive
    @Builder.Default
    private int topK = 10;

    @Valid
    @Builder.Default
    private TBoxFilters filters = new TBoxFilters();

    @Valid
    @Builder.Default
    private RetrieveOptions options = new RetrieveOptions();
}
