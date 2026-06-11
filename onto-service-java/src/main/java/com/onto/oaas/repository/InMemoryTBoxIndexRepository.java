package com.onto.oaas.repository;

import com.onto.oaas.model.TBoxIndexDocument;
import com.onto.oaas.model.enums.TBoxObjectType;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;
import java.util.stream.Collectors;
import org.springframework.stereotype.Repository;

@Repository
public class InMemoryTBoxIndexRepository implements TBoxIndexRepository {

    private final Map<String, Map<String, TBoxIndexDocument>> storageByBuffer = new ConcurrentHashMap<>();

    private Map<String, TBoxIndexDocument> storage(String buffer) {
        return storageByBuffer.computeIfAbsent(buffer, k -> new ConcurrentHashMap<>());
    }

    @Override
    public void save(TBoxIndexDocument document) {
        save(document, activeBuffer());
    }

    private void save(TBoxIndexDocument document, String buffer) {
        if (document != null && document.getObjectPath() != null) {
            storage(buffer).put(document.getObjectPath(), document);
        }
    }

    @Override
    public void saveBatch(List<TBoxIndexDocument> documents) {
        saveBatch(documents, activeBuffer());
    }

    @Override
    public void saveBatch(List<TBoxIndexDocument> documents, String buffer) {
        if (documents != null) {
            documents.forEach(doc -> save(doc, buffer));
        }
    }

    @Override
    public void deleteByObjectPath(String objectPath) {
        if (objectPath != null) {
            storage(activeBuffer()).remove(objectPath);
        }
    }

    @Override
    public List<TBoxIndexDocument> searchByKeyword(String query, List<TBoxObjectType> objectTypes, int limit) {
        String lowerQuery = query == null ? "" : query.toLowerCase();
        return storage(activeBuffer()).values().stream()
            .filter(doc -> objectTypes == null || objectTypes.isEmpty() || objectTypes.contains(doc.getObjectType()))
            .filter(doc -> matchesKeyword(doc, lowerQuery))
            .limit(limit > 0 ? limit : Long.MAX_VALUE)
            .collect(Collectors.toList());
    }

    private boolean matchesKeyword(TBoxIndexDocument doc, String lowerQuery) {
        if (lowerQuery.isEmpty()) {
            return true;
        }
        if (doc.getName() != null && doc.getName().toLowerCase().contains(lowerQuery)) {
            return true;
        }
        if (doc.getDescription() != null && doc.getDescription().toLowerCase().contains(lowerQuery)) {
            return true;
        }
        if (doc.getKeywords() != null) {
            for (String kw : doc.getKeywords()) {
                if (kw != null && kw.toLowerCase().contains(lowerQuery)) {
                    return true;
                }
            }
        }
        return false;
    }

    @Override
    public Optional<TBoxIndexDocument> findByObjectPath(String objectPath) {
        return Optional.ofNullable(storage(activeBuffer()).get(objectPath));
    }

    @Override
    public List<TBoxIndexDocument> exactMatchByPath(String objectPath) {
        TBoxIndexDocument doc = storage(activeBuffer()).get(objectPath);
        if (doc != null) {
            List<TBoxIndexDocument> result = new ArrayList<>();
            result.add(doc);
            return result;
        }
        return new ArrayList<>();
    }

    @Override
    public List<TBoxIndexDocument> searchByDomain(String domainKey) {
        return storage(activeBuffer()).values().stream()
            .filter(doc -> domainKey != null && domainKey.equals(doc.getDomainKey()))
            .collect(Collectors.toList());
    }

    /**
     * 向量相似度搜索：按 embedding 余弦相似度排序返回 topK。
     * 只返回有 embedding 的文档。
     */
    public List<TBoxIndexDocument> searchByVector(float[] queryEmbedding, List<TBoxObjectType> objectTypes, int topK) {
        if (queryEmbedding == null || queryEmbedding.length == 0) {
            return List.of();
        }
        return storage(activeBuffer()).values().stream()
            .filter(doc -> doc.getEmbedding() != null && doc.getEmbedding().length > 0)
            .filter(doc -> objectTypes == null || objectTypes.isEmpty() || objectTypes.contains(doc.getObjectType()))
            .map(doc -> new ScoredDoc(doc, cosineSimilarity(queryEmbedding, doc.getEmbedding())))
            .filter(sd -> sd.score > 0.0)
            .sorted(Comparator.comparingDouble((ScoredDoc sd) -> sd.score).reversed())
            .limit(topK > 0 ? topK : 10)
            .map(sd -> sd.doc)
            .collect(Collectors.toList());
    }

    private double cosineSimilarity(float[] a, float[] b) {
        if (a.length != b.length) {
            return 0.0;
        }
        double dot = 0.0;
        double normA = 0.0;
        double normB = 0.0;
        for (int i = 0; i < a.length; i++) {
            dot += a[i] * b[i];
            normA += a[i] * a[i];
            normB += b[i] * b[i];
        }
        if (normA == 0.0 || normB == 0.0) {
            return 0.0;
        }
        return dot / (Math.sqrt(normA) * Math.sqrt(normB));
    }

    private record ScoredDoc(TBoxIndexDocument doc, double score) {}

    @Override
    public void rebuildIndex() {
        storageByBuffer.clear();
    }

    @Override
    public void clearBuffer(String buffer) {
        storageByBuffer.remove(buffer);
    }

    @Override
    public void promoteBuffer(String fromBuffer, String toBuffer) {
        clearBuffer(toBuffer);
        Map<String, TBoxIndexDocument> moved = storageByBuffer.remove(fromBuffer);
        if (moved != null) {
            storageByBuffer.put(toBuffer, moved);
        }
    }

    @Override
    public long countByBuffer(String buffer) {
        Map<String, TBoxIndexDocument> buf = storageByBuffer.get(buffer);
        return buf == null ? 0L : buf.size();
    }
}
