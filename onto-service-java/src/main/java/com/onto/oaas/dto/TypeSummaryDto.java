package com.onto.oaas.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class TypeSummaryDto {

    private String name;
    private String description;
    private int propertyCount;
    private int relationshipCount;
    private int functionCount;
}
