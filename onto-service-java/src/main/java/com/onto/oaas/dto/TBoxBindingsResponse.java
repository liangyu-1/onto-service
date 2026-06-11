package com.onto.oaas.dto;

import java.util.List;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * Bindings 点查询响应 DTO。
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class TBoxBindingsResponse {

    private String queryId;
    private List<TBoxBindingDto> bindings;
    private List<String> notFound;
}
