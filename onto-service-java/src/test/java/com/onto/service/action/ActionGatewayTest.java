package com.onto.service.action;

import com.onto.service.entity.OntologyAction;
import com.onto.service.mapper.OntologyActionMapper;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.test.context.ActiveProfiles;

import java.util.HashMap;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

@SpringBootTest
@ActiveProfiles("test")
public class ActionGatewayTest {

    @Autowired
    private ActionGateway actionGateway;

    @MockBean
    private OntologyActionMapper actionMapper;

    @Test
    public void testDryRunValidation() {
        OntologyAction action = new OntologyAction();
        action.setActionName("TestAction");
        action.setToolName("test_tool");
        action.setTargetType("ICSProcess");
        action.setInputSchemaJson("{\"type\":\"object\",\"properties\":{\"severity\":{\"type\":\"string\"}}}");
        action.setPreconditionSql("SELECT 1 as precondition_met");

        when(actionMapper.selectOne(any())).thenReturn(action);

        ActionRequest request = new ActionRequest();
        request.setDomainName("PlantGraph");
        request.setVersion("1.0.0");
        request.setActionName("TestAction");
        request.setTargetType("ICSProcess");
        request.setTargetObjectId("P1");
        request.setInput(new HashMap<>() {{ put("severity", "high"); }});

        DryRunResult result = actionGateway.dryRun(request);
        assertNotNull(result);
    }

    @Test
    public void testListTools() {
        List<OntologyAction> tools = actionGateway.listTools("PlantGraph", "1.0.0");
        assertNotNull(tools);
    }
}
