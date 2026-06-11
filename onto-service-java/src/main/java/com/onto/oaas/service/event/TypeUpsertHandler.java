package com.onto.oaas.service.event;

import com.onto.oaas.model.TypeDef;
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
public class TypeUpsertHandler implements EventHandler {

    private final TBoxGraphRepository graphRepository;
    private final TBoxIndexRepository indexRepository;
    private final TBoxIndexBuilder indexBuilder;

    @Override
    public boolean supports(EventType eventType) {
        return eventType == EventType.TYPE_UPSERT;
    }

    @Override
    public void handle(KafkaEventEnvelope<TBoxPayload> envelope) {
        TBoxPayload payload = envelope.getPayload();
        if (payload == null || payload.getDomains() == null) {
            log.warn("Empty payload or domains in TYPE_UPSERT event");
            return;
        }
        payload.getDomains().forEach((domainKey, domain) -> {
            if (domain.getTypes() != null) {
                domain.getTypes().forEach((typeKey, type) -> {
                    graphRepository.saveType(type, domainKey, typeKey);
                    log.debug("Saved type to graph: {}.{}", domainKey, typeKey);
                    indexRepository.save(indexBuilder.buildFromType(domainKey, typeKey, type));
                    log.debug("Saved type to index: {}.{}", domainKey, typeKey);
                });
            }
        });
    }
}
