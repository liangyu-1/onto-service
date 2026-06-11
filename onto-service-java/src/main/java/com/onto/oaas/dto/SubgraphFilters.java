package com.onto.oaas.dto;

import com.onto.oaas.model.enums.TBoxObjectType;
import java.util.List;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class SubgraphFilters {

    @Builder.Default
    private List<TBoxObjectType> objectTypes = List.of();

    @Builder.Default
    private List<String> relationTypes = List.of();
}
