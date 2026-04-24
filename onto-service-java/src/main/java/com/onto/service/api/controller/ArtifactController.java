package com.onto.service.api.controller;

import com.onto.service.common.Result;
import com.onto.service.entity.OntologyArtifact;
import com.onto.service.semantic.artifact.OntologyArtifactService;
import com.onto.service.semantic.export.OwlExportService;
import lombok.Data;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.*;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.time.LocalDateTime;
import java.util.HexFormat;
import java.util.List;
import java.util.Optional;

/**
 * RDF/OWL 工件导入导出 API
 */
@RestController
@RequestMapping("/api/v1/artifacts")
public class ArtifactController {

    public static final String ARTIFACT_KIND_RDF_OWL = "rdf_owl";

    @Autowired
    private OntologyArtifactService artifactService;

    @Autowired
    private OwlExportService owlExportService;

    @GetMapping("/{domainName}/{version}")
    public Result<List<OntologyArtifact>> listArtifacts(@PathVariable String domainName,
                                                        @PathVariable String version) {
        return Result.success(artifactService.list(domainName, version));
    }

    @GetMapping(value = "/{domainName}/{version}/rdf-owl", produces = MediaType.TEXT_PLAIN_VALUE)
    public String exportRdfOwl(@PathVariable String domainName,
                              @PathVariable String version,
                              @RequestParam(required = false, defaultValue = "ttl") String format,
                              @RequestParam(required = false) String baseIri,
                              @RequestParam(required = false, defaultValue = "true") boolean persist) {
        String fmt = normalizeFormat(format);
        Optional<OntologyArtifact> existing = artifactService.latest(domainName, version, ARTIFACT_KIND_RDF_OWL, fmt);
        if (existing.isPresent()) {
            return existing.get().getContent();
        }

        if (!"ttl".equals(fmt)) {
            // 最小实现：先只支持导出 ttl；其它格式通过上传存储满足互通/审计
            throw new IllegalArgumentException("only ttl export is supported for now");
        }

        String ttl = owlExportService.exportTurtle(domainName, version, baseIri);
        if (persist) {
            OntologyArtifact artifact = new OntologyArtifact();
            artifact.setDomainName(domainName);
            artifact.setVersion(version);
            artifact.setArtifactKind(ARTIFACT_KIND_RDF_OWL);
            artifact.setFormat(fmt);
            artifact.setBaseIri(baseIri);
            artifact.setContent(ttl);
            artifact.setContentHash(sha256Hex(ttl));
            artifact.setSource("generated");
            artifact.setCreatedAt(LocalDateTime.now());
            artifact.setCreatedBy("system");
            artifactService.upsert(artifact);
        }
        return ttl;
    }

    @PostMapping("/{domainName}/{version}/rdf-owl")
    public Result<OntologyArtifact> uploadRdfOwl(@PathVariable String domainName,
                                                @PathVariable String version,
                                                @RequestBody UploadArtifactRequest request) {
        String fmt = normalizeFormat(request.getFormat());
        OntologyArtifact artifact = new OntologyArtifact();
        artifact.setDomainName(domainName);
        artifact.setVersion(version);
        artifact.setArtifactKind(ARTIFACT_KIND_RDF_OWL);
        artifact.setFormat(fmt);
        artifact.setBaseIri(request.getBaseIri());
        artifact.setContent(request.getContent());
        artifact.setContentHash(sha256Hex(request.getContent()));
        artifact.setSource("uploaded");
        artifact.setCreatedAt(LocalDateTime.now());
        artifact.setCreatedBy(request.getCreatedBy());
        return Result.success(artifactService.upsert(artifact));
    }

    private static String normalizeFormat(String format) {
        String f = format == null ? "ttl" : format.trim().toLowerCase();
        if (f.isEmpty()) f = "ttl";
        return f;
    }

    private static String sha256Hex(String content) {
        if (content == null) content = "";
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] hash = digest.digest(content.getBytes(StandardCharsets.UTF_8));
            return HexFormat.of().formatHex(hash);
        } catch (Exception e) {
            return "";
        }
    }

    @Data
    public static class UploadArtifactRequest {
        private String format;
        private String baseIri;
        private String content;
        private String createdBy;
    }
}

