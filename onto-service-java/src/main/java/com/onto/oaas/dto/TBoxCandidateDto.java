package com.onto.oaas.dto;

import com.onto.oaas.model.enums.TBoxObjectType;
import java.util.List;
import java.util.Map;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class TBoxCandidateDto {

    private String objectPath;
    private TBoxObjectType objectType;
    private String name;
    private String description;
    private double score;
    private List<String> matchedFields;
    private Map<String, Object> context;
}
