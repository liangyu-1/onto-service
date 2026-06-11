package com.onto.oaas.service.embedding;

import com.onto.oaas.model.TBoxIndexDocument;
import java.util.ArrayList;
import java.util.List;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

/**
 * 为索引文档批量生成 embedding 向量的服务。
 *
 * <p>在索引文档保存到仓库前，调用 Python Embedding 服务（BGE 模型）
 * 为每个文档的 {@code textForEmbedding} 生成向量。</p>
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class EmbeddingIndexService {

    private final EmbeddingClient embeddingClient;

    /**
     * 为文档列表批量生成 embedding 并填充到文档中。
     *
     * @param documents 待填充的索引文档列表
     * @return 填充了 embedding 的文档列表
     */
    public List<TBoxIndexDocument> enrichEmbeddings(List<TBoxIndexDocument> documents) {
        if (documents == null || documents.isEmpty()) {
            return documents;
        }

        List<String> texts = new ArrayList<>(documents.size());
        List<TBoxIndexDocument> toEnrich = new ArrayList<>();

        for (TBoxIndexDocument doc : documents) {
            String text = doc.getTextForEmbedding() != null ? doc.getTextForEmbedding() : doc.getName();
            if (text != null && !text.isBlank()) {
                texts.add(text);
                toEnrich.add(doc);
            }
        }

        if (texts.isEmpty()) {
            log.warn("No texts to embed for {} documents", documents.size());
            return documents;
        }

        try {
            List<float[]> embeddings = embeddingClient.embed(texts);
            if (embeddings.size() != toEnrich.size()) {
                log.warn("Embedding count mismatch: expected {}, got {}", toEnrich.size(), embeddings.size());
            }
            for (int i = 0; i < Math.min(embeddings.size(), toEnrich.size()); i++) {
                toEnrich.get(i).setEmbedding(embeddings.get(i));
            }
            log.info("Enriched {} documents with embeddings (dimension={})",
                    embeddings.size(), embeddings.isEmpty() ? 0 : embeddings.get(0).length);
        } catch (EmbeddingServiceException e) {
            log.error("Failed to enrich embeddings: {}", e.getMessage());
            // 不阻断流程，文档可以无 embedding 保存（向量召回会跳过）
        }

        return documents;
    }

    /**
     * 为单个文档生成 embedding。
     */
    public TBoxIndexDocument enrichEmbedding(TBoxIndexDocument document) {
        if (document == null) {
            return null;
        }
        String text = document.getTextForEmbedding() != null ? document.getTextForEmbedding() : document.getName();
        if (text == null || text.isBlank()) {
            return document;
        }
        try {
            float[] embedding = embeddingClient.embed(text);
            document.setEmbedding(embedding);
        } catch (EmbeddingServiceException e) {
            log.error("Failed to enrich embedding for {}: {}", document.getObjectPath(), e.getMessage());
        }
        return document;
    }
}
