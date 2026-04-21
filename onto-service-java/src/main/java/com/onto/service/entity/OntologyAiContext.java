package com.onto.service.entity;

import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;
import java.util.List;

/**
 * AI Context 实体
 * 对应表: ontology_ai_context
 */
@Data
@TableName("ontology_ai_context")
public class OntologyAiContext {

    private String domainName;
    private String version;
    private String entityType;
    private String entityName;
    private String contextJson;
    private List<Float> embedding;
    private LocalDateTime updatedAt;
}
