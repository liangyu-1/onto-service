package com.onto.oaas.dto;

import com.onto.oaas.model.enums.TBoxObjectType;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class SubgraphNodeDto {

    private String objectPath;
    private TBoxObjectType objectType;
    private String name;
    private String description;
    private int hopDistance;
}
