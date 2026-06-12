package com.onto.oaas.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class RetrieveOptions {

    @Builder.Default
    private boolean enableKeywordRecall = true;

    @Builder.Default
    private boolean enableVectorRecall = true;

    @Builder.Default
    private boolean includeContext = false;

    @Builder.Default
    private boolean skipIntentAnalysis = false;
}
