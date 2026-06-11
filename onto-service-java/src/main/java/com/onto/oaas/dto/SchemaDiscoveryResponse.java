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
public class SchemaDiscoveryResponse {

    private String timestamp;
    private Map<String, DomainSummaryDto> domains;
    private String code;
    private String message;
}
