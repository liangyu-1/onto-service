package com.onto.oaas.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class GraphEdge {
    private String sourcePath;
    private String relationType;
    private String targetPath;
}
