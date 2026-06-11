package com.onto.oaas.service.event;

import com.onto.oaas.model.enums.EventType;
import com.onto.oaas.model.event.KafkaEventEnvelope;
import com.onto.oaas.model.event.TBoxPayload;
import com.onto.oaas.repository.TBoxIndexRepository;
import com.onto.oaas.service.fullsync.FullSyncService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

@Slf4j
@Component
@RequiredArgsConstructor
public class ControlEventHandler implements EventHandler {

    private final TBoxIndexRepository indexRepository;
    private final FullSyncService fullSyncService;

    @Value("${oaas.full-sync.enabled:true}")
    private boolean fullSyncEnabled;

    @Override
    public boolean supports(EventType eventType) {
        return eventType == EventType.REBUILD_INDEX || eventType == EventType.FULL_SYNC_REQUIRED;
    }

    @Override
    public void handle(KafkaEventEnvelope<TBoxPayload> envelope) {
        EventType eventType = EventType.valueOf(envelope.getEventType());
        switch (eventType) {
            case REBUILD_INDEX -> {
                log.info("Handling REBUILD_INDEX control event");
                indexRepository.rebuildIndex();
                log.info("Index rebuild completed");
            }
            case FULL_SYNC_REQUIRED -> {
                if (!fullSyncEnabled) {
                    log.warn("FULL_SYNC_REQUIRED event ignored: full-sync is disabled (oaas.full-sync.enabled=false)");
                    return;
                }
                log.info("Handling FULL_SYNC_REQUIRED control event");
                TBoxPayload payload = envelope.getPayload();
                String ontologyId = payload != null ? payload.getCode() : null;
                String ontologyVersion = payload != null ? payload.getMessage() : null;
                if (ontologyId == null || ontologyVersion == null) {
                    log.warn("Missing ontologyId or ontologyVersion in FULL_SYNC_REQUIRED payload");
                    return;
                }
                fullSyncService.executeFullSync(ontologyId, ontologyVersion);
                log.info("Full sync triggered for ontologyId={}, version={}", ontologyId, ontologyVersion);
            }
            default -> log.warn("Unsupported control event type: {}", eventType);
        }
    }
}
