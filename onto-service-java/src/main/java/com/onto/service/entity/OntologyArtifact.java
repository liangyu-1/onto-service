package com.onto.service.entity;

import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * 本体工件实体（RDF/OWL 等）
 * 对应表: ontology_artifact
 */
@Data
@TableName("ontology_artifact")
public class OntologyArtifact {

    private String domainName;
    private String version;

    private String artifactKind;
    private String format;

    private String baseIri;
    private String content;
    private String contentHash;

    private String source;
    private LocalDateTime createdAt;
    private String createdBy;
}

