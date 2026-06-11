package com.onto.oaas.dto;

import jakarta.validation.constraints.NotEmpty;
import java.util.List;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * Bindings 点查询请求 DTO。
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class TBoxBindingsRequest {

    @NotEmpty
    private List<String> objectPaths;
}
