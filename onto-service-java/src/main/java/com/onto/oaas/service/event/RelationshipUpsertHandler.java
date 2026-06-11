package com.onto.oaas.service.event;

import com.onto.oaas.model.RelationshipDef;
import com.onto.oaas.model.enums.EventType;
import com.onto.oaas.model.event.KafkaEventEnvelope;
import com.onto.oaas.model.event.TBoxPayload;
import com.onto.oaas.repository.TBoxGraphRepository;
import com.onto.oaas.repository.TBoxIndexRepository;
import com.onto.oaas.service.TBoxIndexBuilder;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

@Slf4j
@Component
@RequiredArgsConstructor
public class RelationshipUpsertHandler implements EventHandler {

    private final TBoxGraphRepository graphRepository;
    private final TBoxIndexRepository indexRepository;
    private final TBoxIndexBuilder indexBuilder;

    @Override
    public boolean supports(EventType eventType) {
        return eventType == EventType.RELATIONSHIP_UPSERT;
    }

    @Override
    public void handle(KafkaEventEnvelope<TBoxPayload> envelope) {
        TBoxPayload payload = envelope.getPayload();
        if (payload == null || payload.getDomains() == null) {
            log.warn("Empty payload or domains in RELATIONSHIP_UPSERT event");
            return;
        }
        payload.getDomains().forEach((domainKey, domain) -> {
            if (domain.getTypes() != null) {
                domain.getTypes().forEach((typeKey, type) -> {
                    if (type.getRelationships() != null) {
                        type.getRelationships().forEach((relationshipKey, relationship) -> {
                            graphRepository.saveRelationship(relationship, domainKey, typeKey, relationshipKey);
                            log.debug("Saved relationship to graph: {}.{}.{}", domainKey, typeKey, relationshipKey);
                            indexRepository.save(indexBuilder.buildFromRelationship(domainKey, typeKey, relationshipKey, relationship));
                            log.debug("Saved relationship to index: {}.{}.{}", domainKey, typeKey, relationshipKey);
                        });
                    }
                });
            }
        });
    }
}
