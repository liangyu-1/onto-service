package com.onto.service.action;

import lombok.Data;

import java.util.List;
import java.util.Map;

/**
 * Dry-run 结果
 */
@Data
public class DryRunResult {

    private Boolean valid;
    private String actionId;
    private List<String> warnings;
    private List<String> errors;
    private Map<String, Object> preview;
    private String precheckResultJson;
}
