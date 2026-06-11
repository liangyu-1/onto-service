package com.onto.oaas.model;

import java.util.List;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class QueryIntent {
    private List<String> possibleObjectPaths;
    private List<String> objectTypeHints;
    private List<String> keywordHints;
}
