package com.onto.oaas.service.event;

import com.onto.oaas.model.enums.EventType;
import com.onto.oaas.model.event.KafkaEventEnvelope;
import com.onto.oaas.model.event.TBoxPayload;

public interface EventHandler {

    boolean supports(EventType eventType);

    void handle(KafkaEventEnvelope<TBoxPayload> envelope);
}
