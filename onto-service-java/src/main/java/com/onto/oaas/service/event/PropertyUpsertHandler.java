package com.onto.oaas.service.event;

import com.onto.oaas.model.PropertyDef;
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
public class PropertyUpsertHandler implements EventHandler {

    private final TBoxGraphRepository graphRepository;
    private final TBoxIndexRepository indexRepository;
    private final TBoxIndexBuilder indexBuilder;

    @Override
    public boolean supports(EventType eventType) {
        return eventType == EventType.PROPERTY_UPSERT;
    }

    @Override
    public void handle(KafkaEventEnvelope<TBoxPayload> envelope) {
        TBoxPayload payload = envelope.getPayload();
        if (payload == null || payload.getDomains() == null) {
            log.warn("Empty payload or domains in PROPERTY_UPSERT event");
            return;
        }
        payload.getDomains().forEach((domainKey, domain) -> {
            if (domain.getTypes() != null) {
                domain.getTypes().forEach((typeKey, type) -> {
                    if (type.getProperties() != null) {
                        type.getProperties().forEach((propertyKey, property) -> {
                            graphRepository.saveProperty(property, domainKey, typeKey, propertyKey);
                            log.debug("Saved property to graph: {}.{}.{}", domainKey, typeKey, propertyKey);
                            indexRepository.save(indexBuilder.buildFromProperty(domainKey, typeKey, propertyKey, property));
                            log.debug("Saved property to index: {}.{}.{}", domainKey, typeKey, propertyKey);
                        });
                    }
                });
            }
        });
    }
}
