package com.onto.service.query;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;

import java.util.Arrays;
import java.util.HashMap;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

@SpringBootTest
@ActiveProfiles("test")
public class QueryAdapterTest {

    @Autowired
    private QueryAdapter queryAdapter;

    @Test
    public void testGenerateDorisSql() {
        ResolvedSemanticPlan plan = new ResolvedSemanticPlan();
        plan.setSourceTables(Arrays.asList("dim_process"));
        
        Map<String, String> projections = new HashMap<>();
        projections.put("process_id", "process_id");
        projections.put("security_state", "security_state");
        plan.setColumnProjections(projections);
        
        plan.setWhereClause("process_id = 'P1'");
        plan.setLimit(100);

        String sql = queryAdapter.generateDorisSql("PlantGraph", "1.0.0", plan);
        
        assertNotNull(sql);
        assertTrue(sql.contains("SELECT"));
        assertTrue(sql.contains("FROM dim_process"));
        assertTrue(sql.contains("WHERE"));
        assertTrue(sql.contains("LIMIT 100"));
    }

    @Test
    public void testExplainQuery() {
        SemanticQuery query = new SemanticQuery();
        query.setTargetType("ICSProcess");
        query.setSelectProperties(Arrays.asList("security_state"));
        query.setIntent("select");

        Explanation explanation = queryAdapter.explainQuery("PlantGraph", "1.0.0", query);
        
        assertNotNull(explanation);
        assertNotNull(explanation.getNaturalLanguageText());
        assertNotNull(explanation.getDataSources());
    }
}
