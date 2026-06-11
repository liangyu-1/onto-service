package com.onto.oaas.repository;

import com.onto.oaas.model.TBoxIndexDocument;
import com.onto.oaas.model.enums.TBoxObjectType;
import java.util.List;
import java.util.Optional;

public interface TBoxIndexRepository {

    void save(TBoxIndexDocument document);

    void saveBatch(List<TBoxIndexDocument> documents);

    void saveBatch(List<TBoxIndexDocument> documents, String buffer);

    void deleteByObjectPath(String objectPath);

    List<TBoxIndexDocument> searchByKeyword(String query, List<TBoxObjectType> objectTypes, int limit);

    Optional<TBoxIndexDocument> findByObjectPath(String objectPath);

    List<TBoxIndexDocument> exactMatchByPath(String objectPath);

    List<TBoxIndexDocument> searchByDomain(String domainKey);

    void rebuildIndex();

    void clearBuffer(String buffer);

    void promoteBuffer(String fromBuffer, String toBuffer);

    long countByBuffer(String buffer);

    default String activeBuffer() {
        return "active";
    }

    default String stagingBuffer() {
        return "staging";
    }
}
