package com.onto.service.action;

import lombok.Data;

import java.util.List;
import java.util.Map;

/**
 * 前置条件检查结果
 */
@Data
public class PrecheckResult {

    private Boolean passed;
    private List<String> failedConditions;
    private Map<String, Object> checkedValues;
    private String explanation;
}
