package com.onto.oaas.dto;

import java.util.List;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class TBoxRetrieveResponse {

    private String queryId;
    private String mode;
    private List<TBoxCandidateDto> objects;
}
