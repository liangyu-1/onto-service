package com.onto.oaas.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 图边类型 DTO。
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class GraphEdgeTypeDto {

    private String type;
    private String source;
    private String target;
    private String description;
}
