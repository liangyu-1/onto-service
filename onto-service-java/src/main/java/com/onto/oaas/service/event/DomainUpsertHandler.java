package com.onto.oaas.service.event;

import com.onto.oaas.model.DomainDef;
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
public class DomainUpsertHandler implements EventHandler {

    private final TBoxGraphRepository graphRepository;
    private final TBoxIndexRepository indexRepository;
    private final TBoxIndexBuilder indexBuilder;

    @Override
    public boolean supports(EventType eventType) {
        return eventType == EventType.DOMAIN_UPSERT;
    }

    @Override
    public void handle(KafkaEventEnvelope<TBoxPayload> envelope) {
        TBoxPayload payload = envelope.getPayload();
        if (payload == null || payload.getDomains() == null) {
            log.warn("Empty payload or domains in DOMAIN_UPSERT event");
            return;
        }
        payload.getDomains().forEach((domainKey, domain) -> {
            graphRepository.saveDomain(domain, domainKey);
            log.debug("Saved domain to graph: {}", domainKey);
            indexRepository.save(indexBuilder.buildFromDomain(domainKey, domain));
            log.debug("Saved domain to index: {}", domainKey);
        });
    }
}
