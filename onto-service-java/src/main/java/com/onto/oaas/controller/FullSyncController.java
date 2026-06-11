package com.onto.oaas.controller;

import com.onto.oaas.service.fullsync.FullSyncService;
import com.onto.oaas.model.FullSyncCheckpoint;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

@RestController
@RequestMapping("/v1/tbox")
@RequiredArgsConstructor
public class FullSyncController {

    private final FullSyncService fullSyncService;

    @PostMapping("/sync/full")
    public ResponseEntity<Map<String, Object>> triggerFullSync(
            @RequestParam(defaultValue = "default") String ontologyId,
            @RequestParam(defaultValue = "latest") String ontologyVersion) {
        FullSyncCheckpoint checkpoint = fullSyncService.executeFullSync(ontologyId, ontologyVersion);
        return ResponseEntity.ok(Map.of(
                "checkpointId", checkpoint.getCheckpointId(),
                "status", checkpoint.getStatus(),
                "domainCount", checkpoint.getDomainCount(),
                "typeCount", checkpoint.getTypeCount(),
                "propertyCount", checkpoint.getPropertyCount(),
                "relationshipCount", checkpoint.getRelationshipCount(),
                "functionCount", checkpoint.getFunctionCount(),
                "ruleCount", checkpoint.getRuleCount()
        ));
    }
}
