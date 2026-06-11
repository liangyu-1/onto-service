package com.onto.oaas.dto;

import java.util.Map;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class DomainSummaryDto {

    private String name;
    private String description;
    private int typeCount;
    private Map<String, TypeSummaryDto> types;
}
