package com.onto.oaas.service.event;

import com.onto.oaas.model.RuleDef;
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
public class RuleUpsertHandler implements EventHandler {

    private final TBoxGraphRepository graphRepository;
    private final TBoxIndexRepository indexRepository;
    private final TBoxIndexBuilder indexBuilder;

    @Override
    public boolean supports(EventType eventType) {
        return eventType == EventType.RULE_UPSERT;
    }

    @Override
    public void handle(KafkaEventEnvelope<TBoxPayload> envelope) {
        TBoxPayload payload = envelope.getPayload();
        if (payload == null || payload.getDomains() == null) {
            log.warn("Empty payload or domains in RULE_UPSERT event");
            return;
        }
        payload.getDomains().forEach((domainKey, domain) -> {
            if (domain.getTypes() != null) {
                domain.getTypes().forEach((typeKey, type) -> {
                    if (type.getFunctions() != null) {
                        type.getFunctions().forEach((functionKey, function) -> {
                            if (function.getRules() != null) {
                                function.getRules().forEach((ruleKey, rule) -> {
                                    graphRepository.saveRule(rule, domainKey, typeKey, functionKey, ruleKey);
                                    log.debug("Saved rule to graph: {}.{}.{}.{}" , domainKey, typeKey, functionKey, ruleKey);
                                    indexRepository.save(indexBuilder.buildFromRule(domainKey, typeKey, functionKey, ruleKey, rule));
                                    log.debug("Saved rule to index: {}.{}.{}.{}" , domainKey, typeKey, functionKey, ruleKey);
                                });
                            }
                        });
                    }
                });
            }
        });
    }
}
