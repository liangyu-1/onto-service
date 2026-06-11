package com.onto.oaas.model;

import java.util.List;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 增强版查询意图（V2），支持语义查询理解。
 *
 * <p>包含实体链接结果、意图类型、结构约束和查询扩展。</p>
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class QueryIntentV2 {

    /** 实体链接结果：查询中的实体映射到本体的 objectPath */
    private List<String> linkedEntityPaths;

    /** 查询意图类型 */
    private String intent;

    /** 结构约束：如 "...的指标" → 需要找 Measure */
    private List<StructureConstraint> constraints;

    /** 查询扩展：同义词、上下位词 */
    private List<String> expandedQueries;

    /** 原始关键词（兼容 V1） */
    private List<String> keywordHints;

    /** 对象类型提示（兼容 V1） */
    private List<String> objectTypeHints;

    /** 可能的 objectPath（兼容 V1） */
    private List<String> possibleObjectPaths;

    /**
     * 结构约束定义。
     */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class StructureConstraint {
        /** 约束类型：PATH_PREFIX / TYPE_FILTER / RELATIONSHIP / HOP_DISTANCE */
        private String type;
        /** 约束值 */
        private String value;
        /** 约束描述 */
        private String description;
    }
}
