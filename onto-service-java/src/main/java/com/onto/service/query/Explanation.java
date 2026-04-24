package com.onto.service.query;

import lombok.Data;

import java.util.List;
import java.util.Map;

/**
 * 查询结果解释
 */
@Data
public class Explanation {

    /**
     * 自然语言解释文本
     */
    private String naturalLanguageText;

    /**
     * 涉及的 Logic 规则
     */
    private List<String> involvedLogicRules;

    /**
     * 证据链
     */
    private List<Evidence> evidenceChain;

    /**
     * 数据来源
     */
    private List<String> dataSources;

    @Data
    public static class Evidence {
        private String logicName;
        private String description;
        private Map<String, Object> evidenceData;
    }
}
