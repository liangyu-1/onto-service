package com.onto.oaas.dto;

import com.onto.oaas.model.Binding;
import com.onto.oaas.model.enums.TBoxObjectType;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * Bindings 查询结果中的单个绑定信息 DTO。
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class TBoxBindingDto {

    private String objectPath;
    private TBoxObjectType objectType;
    private String name;
    private String dataType;
    private Binding binding;
    private Boolean pkColumn;

    // Rule 特有字段
    private String ruleType;
    private String definition;
}
