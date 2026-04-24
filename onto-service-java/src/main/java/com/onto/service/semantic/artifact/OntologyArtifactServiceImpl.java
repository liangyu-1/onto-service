package com.onto.service.semantic.artifact;

import com.onto.service.entity.OntologyArtifact;
import com.onto.service.mapper.OntologyArtifactMapper;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;

/**
 * 本体工件服务实现
 */
@Service
public class OntologyArtifactServiceImpl implements OntologyArtifactService {

    @Autowired
    private OntologyArtifactMapper artifactMapper;

    @Override
    public OntologyArtifact upsert(OntologyArtifact artifact) {
        if (artifact.getCreatedAt() == null) {
            artifact.setCreatedAt(LocalDateTime.now());
        }
        OntologyArtifact existing = artifactMapper.selectOneByKey(
                artifact.getDomainName(),
                artifact.getVersion(),
                artifact.getArtifactKind(),
                artifact.getFormat(),
                artifact.getContentHash()
        );
        if (existing == null) {
            artifactMapper.insert(artifact);
            return artifact;
        }
        // 幂等：同 key 已存在则直接返回已有记录
        return existing;
    }

    @Override
    public Optional<OntologyArtifact> get(String domainName, String version, String artifactKind, String format, String contentHash) {
        return Optional.ofNullable(artifactMapper.selectOneByKey(domainName, version, artifactKind, format, contentHash));
    }

    @Override
    public Optional<OntologyArtifact> latest(String domainName, String version, String artifactKind, String format) {
        return Optional.ofNullable(artifactMapper.selectLatestByKindFormat(domainName, version, artifactKind, format));
    }

    @Override
    public List<OntologyArtifact> list(String domainName, String version) {
        return artifactMapper.selectByDomainVersion(domainName, version);
    }
}

