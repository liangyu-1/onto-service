package com.onto.oaas.model;

import java.util.Map;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class LinkProperty {
    private Map<String, String> sourcePath;
    private Map<String, String> targetPath;
}
