package com.onto.service.semantic.export;

import com.onto.service.entity.OntologyObjectType;
import com.onto.service.entity.OntologyProperty;
import com.onto.service.entity.OntologyRelationship;
import com.onto.service.semantic.OntologyObjectTypeService;
import com.onto.service.semantic.OntologyPropertyService;
import com.onto.service.semantic.OntologyRelationshipService;
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;

import java.util.List;

import static org.junit.jupiter.api.Assertions.assertTrue;

public class OwlExportServiceTest {

    @Test
    public void exportTurtleIncludesClassPropertyRelationship() {
        OntologyObjectTypeService otSvc = Mockito.mock(OntologyObjectTypeService.class);
        OntologyPropertyService propSvc = Mockito.mock(OntologyPropertyService.class);
        OntologyRelationshipService relSvc = Mockito.mock(OntologyRelationshipService.class);

        OntologyObjectType t = new OntologyObjectType();
        t.setDomainName("PlantGraph");
        t.setVersion("1.0.0");
        t.setLabelName("Equipment");
        t.setDisplayName("设备");

        OntologyProperty p = new OntologyProperty();
        p.setDomainName("PlantGraph");
        p.setVersion("1.0.0");
        p.setOwnerLabel("Equipment");
        p.setPropertyName("temperature");
        p.setValueType("DOUBLE");

        OntologyRelationship r = new OntologyRelationship();
        r.setDomainName("PlantGraph");
        r.setVersion("1.0.0");
        r.setLabelName("HAS_SENSOR");
        r.setSourceLabel("Equipment");
        r.setTargetLabel("Sensor");

        Mockito.when(otSvc.getObjectTypes("PlantGraph", "1.0.0")).thenReturn(List.of(t));
        Mockito.when(propSvc.getPropertiesByOwner("PlantGraph", "1.0.0", "Equipment")).thenReturn(List.of(p));
        Mockito.when(relSvc.getRelationships("PlantGraph", "1.0.0")).thenReturn(List.of(r));

        OwlExportService exporter = new OwlExportService();
        // inject mocks via reflection-less assignment (package-private not available), so use reflection
        TestUtil.setField(exporter, "objectTypeService", otSvc);
        TestUtil.setField(exporter, "propertyService", propSvc);
        TestUtil.setField(exporter, "relationshipService", relSvc);

        String ttl = exporter.exportTurtle("PlantGraph", "1.0.0", "urn:onto:PlantGraph:1.0.0");
        assertTrue(ttl.contains("onto:Equipment a owl:Class"));
        assertTrue(ttl.contains("a owl:DatatypeProperty"));
        assertTrue(ttl.contains("onto:HAS_SENSOR a owl:ObjectProperty"));
    }

    static class TestUtil {
        static void setField(Object target, String field, Object value) {
            try {
                var f = target.getClass().getDeclaredField(field);
                f.setAccessible(true);
                f.set(target, value);
            } catch (Exception e) {
                throw new RuntimeException(e);
            }
        }
    }
}

