package com.onto.oaas.model;

import com.onto.oaas.model.enums.TBoxObjectType;
import java.time.Instant;
import java.util.List;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class TBoxIndexDocument {
    private String objectPath;
    private TBoxObjectType objectType;
    private String name;
    private String description;
    private String textForEmbedding;
    private List<String> keywords;
    private String domainKey;
    private String typeKey;
    private String functionKey;
    private String ruleKey;
    private String ruleType;
    private String definition;
    private Binding binding;
    private Instant updatedTime;

    /** 语义嵌入向量（由 BGE 模型生成） */
    private float[] embedding;
}
