package com.onto.oaas.model.event;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.onto.oaas.model.DomainDef;
import java.util.HashMap;
import java.util.Map;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class TBoxPayload {
    private String timestamp;

    @Builder.Default
    @JsonProperty("domains")
    private Map<String, DomainDef> domains = new HashMap<>();

    private String code;
    private String message;

    public void setDomain(String key, DomainDef value) {
        this.domains.put(key, value);
    }
}
