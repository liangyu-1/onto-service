package com.onto.service.semantic;

import com.onto.service.entity.OntologyDomain;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;

import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

@SpringBootTest
@ActiveProfiles("test")
public class OntologyDomainServiceTest {

    @Autowired
    private OntologyDomainService domainService;

    @Test
    public void testCreateDomain() {
        OntologyDomain domain = domainService.createDomain(
            "TestPlant", "CREATE PROPERTY GRAPH TestPlant ...", "test-user");
        
        assertNotNull(domain);
        assertEquals("TestPlant", domain.getDomainName());
        assertEquals("1.0.0", domain.getVersion());
        assertEquals("draft", domain.getStatus());
        assertNotNull(domain.getDdlHash());
    }

    @Test
    public void testPublishVersion() {
        OntologyDomain v1 = domainService.publishVersion(
            "TestPlant2", "CREATE PROPERTY GRAPH TestPlant2 ...", "test-user");
        
        assertNotNull(v1);
        assertEquals("1.0.0", v1.getVersion());

        OntologyDomain v2 = domainService.publishVersion(
            "TestPlant2", "CREATE PROPERTY GRAPH TestPlant2 v2 ...", "test-user");
        
        assertEquals("1.0.1", v2.getVersion());
    }

    @Test
    public void testGetDomainVersions() {
        domainService.createDomain("TestPlant3", "DDL v1", "test-user");
        domainService.publishVersion("TestPlant3", "DDL v2", "test-user");
        
        List<OntologyDomain> versions = domainService.getDomainVersions("TestPlant3");
        assertTrue(versions.size() >= 2);
    }
}
