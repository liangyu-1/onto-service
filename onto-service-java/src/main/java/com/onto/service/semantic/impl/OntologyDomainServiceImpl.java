package com.onto.service.semantic.impl;

import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.onto.service.entity.OntologyDomain;
import com.onto.service.mapper.OntologyDomainMapper;
import com.onto.service.semantic.OntologyDomainService;
import org.springframework.stereotype.Service;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.HexFormat;
import java.util.List;

/**
 * 本体域服务实现
 */
@Service
public class OntologyDomainServiceImpl extends ServiceImpl<OntologyDomainMapper, OntologyDomain> implements OntologyDomainService {

    @Override
    public OntologyDomain createDomain(String domainName, String ddlSql, String createdBy) {
        OntologyDomain domain = new OntologyDomain();
        domain.setId(domainName + ":1.0.0");
        domain.setDomainName(domainName);
        domain.setVersion("1.0.0");
        domain.setDdlSql(ddlSql);
        domain.setStatus("draft");
        domain.setCreatedAt(LocalDateTime.now());
        domain.setCreatedBy(createdBy);
        domain.setDdlHash(computeHash(ddlSql));
        baseMapper.insert(domain);
        return domain;
    }

    @Override
    public OntologyDomain publishVersion(String domainName, String ddlSql, String createdBy) {
        // 获取当前最新版本号
        List<OntologyDomain> versions = baseMapper.selectByDomainName(domainName);
        String newVersion = generateNextVersion(versions);

        OntologyDomain domain = new OntologyDomain();
        domain.setId(domainName + ":" + newVersion);
        domain.setDomainName(domainName);
        domain.setVersion(newVersion);
        domain.setDdlSql(ddlSql);
        domain.setStatus("published");
        domain.setCreatedAt(LocalDateTime.now());
        domain.setCreatedBy(createdBy);
        domain.setDdlHash(computeHash(ddlSql));
        baseMapper.insert(domain);
        return domain;
    }

    @Override
    public OntologyDomain getDomainVersion(String domainName, String version) {
        return baseMapper.selectById(domainName + ":" + version);
    }

    @Override
    public List<OntologyDomain> getDomainVersions(String domainName) {
        return baseMapper.selectByDomainName(domainName);
    }

    @Override
    public OntologyDomain getLatestPublishedVersion(String domainName) {
        return baseMapper.selectLatestPublished(domainName);
    }

    private String computeHash(String content) {
        if (content == null || content.isEmpty()) {
            return "";
        }
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] hash = digest.digest(content.getBytes(StandardCharsets.UTF_8));
            return HexFormat.of().formatHex(hash);
        } catch (Exception e) {
            return "";
        }
    }

    private String generateNextVersion(List<OntologyDomain> versions) {
        if (versions == null || versions.isEmpty()) {
            return "1.0.0";
        }
        // 简单版本递增逻辑
        String latest = versions.get(0).getVersion();
        String[] parts = latest.split("\\.");
        int major = Integer.parseInt(parts[0]);
        int minor = Integer.parseInt(parts[1]);
        int patch = Integer.parseInt(parts[2]);
        patch++;
        if (patch > 99) {
            patch = 0;
            minor++;
        }
        if (minor > 99) {
            minor = 0;
            major++;
        }
        return String.format("%d.%d.%d", major, minor, patch);
    }
}
