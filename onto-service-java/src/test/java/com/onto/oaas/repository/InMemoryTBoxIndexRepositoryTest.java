package com.onto.oaas.repository;

import static org.assertj.core.api.Assertions.assertThat;

import com.onto.oaas.model.TBoxIndexDocument;
import com.onto.oaas.model.enums.TBoxObjectType;
import java.time.Instant;
import java.util.List;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

class InMemoryTBoxIndexRepositoryTest {

    private InMemoryTBoxIndexRepository repository;

    @BeforeEach
    void setUp() {
        repository = new InMemoryTBoxIndexRepository();
    }

    private TBoxIndexDocument doc(String objectPath, TBoxObjectType type, String name, String description,
                                  List<String> keywords, String domainKey) {
        return TBoxIndexDocument.builder()
                .objectPath(objectPath)
                .objectType(type)
                .name(name)
                .description(description)
                .keywords(keywords)
                .domainKey(domainKey)
                .updatedTime(Instant.now())
                .build();
    }

    @Test
    void shouldSaveAndFindByObjectPath() {
        TBoxIndexDocument document = doc("d1.t1", TBoxObjectType.TYPE, "Type1", "desc", List.of("kw"), "d1");
        repository.save(document);

        var found = repository.findByObjectPath("d1.t1");
        assertThat(found).isPresent();
        assertThat(found.get().getName()).isEqualTo("Type1");
    }

    @Test
    void shouldSearchByKeywordMatchingName() {
        repository.save(doc("d1.t1", TBoxObjectType.TYPE, "Equipment", "desc", List.of(), "d1"));
        repository.save(doc("d1.t2", TBoxObjectType.TYPE, "Material", "desc", List.of(), "d1"));

        List<TBoxIndexDocument> results = repository.searchByKeyword("Equip", List.of(), 10);
        assertThat(results).hasSize(1);
        assertThat(results.get(0).getName()).isEqualTo("Equipment");
    }

    @Test
    void shouldSearchByKeywordMatchingDescription() {
        repository.save(doc("d1.t1", TBoxObjectType.TYPE, "T1", "This is an equipment description", List.of(), "d1"));
        repository.save(doc("d1.t2", TBoxObjectType.TYPE, "T2", "Another description", List.of(), "d1"));

        List<TBoxIndexDocument> results = repository.searchByKeyword("equipment", List.of(), 10);
        assertThat(results).hasSize(1);
        assertThat(results.get(0).getName()).isEqualTo("T1");
    }

    @Test
    void shouldSearchByKeywordMatchingKeywords() {
        repository.save(doc("d1.t1", TBoxObjectType.TYPE, "T1", "desc", List.of("machine", "tool"), "d1"));
        repository.save(doc("d1.t2", TBoxObjectType.TYPE, "T2", "desc", List.of("asset"), "d1"));

        List<TBoxIndexDocument> results = repository.searchByKeyword("machine", List.of(), 10);
        assertThat(results).hasSize(1);
        assertThat(results.get(0).getName()).isEqualTo("T1");
    }

    @Test
    void shouldSearchByDomain() {
        repository.save(doc("d1.t1", TBoxObjectType.TYPE, "T1", "desc", List.of(), "d1"));
        repository.save(doc("d2.t1", TBoxObjectType.TYPE, "T2", "desc", List.of(), "d2"));
        repository.save(doc("d1.t2", TBoxObjectType.PROPERTY, "P1", "desc", List.of(), "d1"));

        List<TBoxIndexDocument> results = repository.searchByDomain("d1");
        assertThat(results).hasSize(2);
        assertThat(results).extracting(TBoxIndexDocument::getName).containsExactlyInAnyOrder("T1", "P1");
    }

    @Test
    void shouldDeleteByObjectPath() {
        repository.save(doc("d1.t1", TBoxObjectType.TYPE, "T1", "desc", List.of(), "d1"));
        assertThat(repository.findByObjectPath("d1.t1")).isPresent();

        repository.deleteByObjectPath("d1.t1");
        assertThat(repository.findByObjectPath("d1.t1")).isEmpty();
    }

    @Test
    void shouldRebuildIndex() {
        repository.save(doc("d1.t1", TBoxObjectType.TYPE, "T1", "desc", List.of(), "d1"));
        repository.save(doc("d1.t2", TBoxObjectType.TYPE, "T2", "desc", List.of(), "d1"));
        assertThat(repository.searchByKeyword("T", List.of(), 10)).hasSize(2);

        repository.rebuildIndex();
        assertThat(repository.searchByKeyword("T", List.of(), 10)).isEmpty();
    }

    @Test
    void shouldSaveBatch() {
        List<TBoxIndexDocument> docs = List.of(
                doc("d1.t1", TBoxObjectType.TYPE, "T1", "desc", List.of(), "d1"),
                doc("d1.t2", TBoxObjectType.TYPE, "T2", "desc", List.of(), "d1")
        );
        repository.saveBatch(docs);

        assertThat(repository.findByObjectPath("d1.t1")).isPresent();
        assertThat(repository.findByObjectPath("d1.t2")).isPresent();
    }

    @Test
    void shouldSearchByKeywordWithObjectTypeFilter() {
        repository.save(doc("d1.t1", TBoxObjectType.TYPE, "Equipment", "desc", List.of(), "d1"));
        repository.save(doc("d1.t1.properties.p1", TBoxObjectType.PROPERTY, "Equipment", "desc", List.of(), "d1"));

        List<TBoxIndexDocument> results = repository.searchByKeyword("Equip", List.of(TBoxObjectType.PROPERTY), 10);
        assertThat(results).hasSize(1);
        assertThat(results.get(0).getObjectType()).isEqualTo(TBoxObjectType.PROPERTY);
    }

    @Test
    void shouldReturnEmptyWhenKeywordNotMatched() {
        repository.save(doc("d1.t1", TBoxObjectType.TYPE, "T1", "desc", List.of(), "d1"));
        List<TBoxIndexDocument> results = repository.searchByKeyword("nonexistent", List.of(), 10);
        assertThat(results).isEmpty();
    }

    @Test
    void shouldReturnAllWhenKeywordIsEmpty() {
        repository.save(doc("d1.t1", TBoxObjectType.TYPE, "T1", "desc", List.of(), "d1"));
        repository.save(doc("d1.t2", TBoxObjectType.TYPE, "T2", "desc", List.of(), "d1"));

        List<TBoxIndexDocument> results = repository.searchByKeyword("", List.of(), 10);
        assertThat(results).hasSize(2);
    }

    @Test
    void shouldExactMatchByPath() {
        repository.save(doc("d1.t1", TBoxObjectType.TYPE, "T1", "desc", List.of(), "d1"));
        List<TBoxIndexDocument> results = repository.exactMatchByPath("d1.t1");
        assertThat(results).hasSize(1);
        assertThat(results.get(0).getName()).isEqualTo("T1");
    }

    @Test
    void shouldReturnEmptyExactMatchWhenPathNotFound() {
        List<TBoxIndexDocument> results = repository.exactMatchByPath("nonexistent");
        assertThat(results).isEmpty();
    }

    @Test
    void shouldIgnoreNullDocumentOnSave() {
        repository.save(null);
        assertThat(repository.searchByKeyword("", List.of(), 10)).isEmpty();
    }

    @Test
    void shouldIgnoreNullObjectPathOnSave() {
        TBoxIndexDocument document = TBoxIndexDocument.builder()
                .objectPath(null)
                .objectType(TBoxObjectType.TYPE)
                .name("T1")
                .build();
        repository.save(document);
        assertThat(repository.searchByKeyword("", List.of(), 10)).isEmpty();
    }

    @Test
    void shouldRespectLimit() {
        repository.save(doc("d1.t1", TBoxObjectType.TYPE, "A", "desc", List.of(), "d1"));
        repository.save(doc("d1.t2", TBoxObjectType.TYPE, "B", "desc", List.of(), "d1"));
        repository.save(doc("d1.t3", TBoxObjectType.TYPE, "C", "desc", List.of(), "d1"));

        List<TBoxIndexDocument> results = repository.searchByKeyword("", List.of(), 2);
        assertThat(results).hasSize(2);
    }
}
