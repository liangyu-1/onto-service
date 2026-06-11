package com.onto.oaas.dto;

import com.onto.oaas.model.Binding;
import com.onto.oaas.model.enums.TBoxObjectType;
import java.util.Map;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class TBoxObjectDetailResponse {

    private String objectPath;
    private TBoxObjectType objectType;
    private String name;
    private String description;
    private String dataType;
    private Binding binding;
    private Boolean pkColumn;
    private Map<String, Object> context;
}
