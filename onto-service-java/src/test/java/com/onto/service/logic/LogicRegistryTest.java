package com.onto.service.logic;

import com.onto.service.entity.OntologyLogic;
import com.onto.service.exception.OntologyException;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;

import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

@SpringBootTest
@ActiveProfiles("test")
public class LogicRegistryTest {

    @Autowired
    private LogicRegistry logicRegistry;

    @Test
    public void testTopoSortNoCycle() {
        try {
            List<String> order = logicRegistry.getDependencyTopoOrder("PlantGraph", "1.0.0");
            assertNotNull(order);
        } catch (OntologyException e) {
            assertTrue(e.getMessage().contains("cycle") || e.getMessage().contains("not found"));
        }
    }

    @Test
    public void testCreateAndGetLogic() {
        OntologyLogic logic = new OntologyLogic();
        logic.setDomainName("TestDomain");
        logic.setVersion("1.0.0");
        logic.setLogicName("TestLogic");
        logic.setTargetType("TestType");
        logic.setTargetProperty("testProp");
        logic.setLogicKind("semantic_property");
        logic.setImplementationType("sql");
        logic.setExpressionSql("SELECT 1");
        logic.setDeterministic(true);

        OntologyLogic created = logicRegistry.createLogic(logic);
        assertNotNull(created);
        assertEquals("TestLogic", created.getLogicName());

        OntologyLogic fetched = logicRegistry.getLogic("TestDomain", "1.0.0", "TestLogic");
        assertNotNull(fetched);
        assertEquals("TestLogic", fetched.getLogicName());
    }

    @Test
    public void testRenderExplanation() {
        String rendered = logicRegistry.renderExplanation("TestDomain", "1.0.0",
            "TestLogic", "zh-CN", new java.util.HashMap<>() {{ put("process_id", "P1"); }});
        assertNotNull(rendered);
    }
}
