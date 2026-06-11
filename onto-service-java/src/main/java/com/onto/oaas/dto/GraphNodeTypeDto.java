package com.onto.oaas.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 图节点类型 DTO。
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class GraphNodeTypeDto {

    private String type;
    private String description;
}
