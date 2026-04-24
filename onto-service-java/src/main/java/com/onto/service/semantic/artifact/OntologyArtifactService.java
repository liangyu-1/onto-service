package com.onto.service.semantic.artifact;

import com.onto.service.entity.OntologyArtifact;

import java.util.List;
import java.util.Optional;

/**
 * 本体工件服务接口（RDF/OWL 等）
 */
public interface OntologyArtifactService {

    OntologyArtifact upsert(OntologyArtifact artifact);

    Optional<OntologyArtifact> get(String domainName, String version, String artifactKind, String format, String contentHash);

    Optional<OntologyArtifact> latest(String domainName, String version, String artifactKind, String format);

    List<OntologyArtifact> list(String domainName, String version);
}

