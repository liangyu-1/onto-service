package com.onto.service.tbox.neo4j;

import org.neo4j.driver.Driver;
import org.neo4j.driver.Record;
import org.neo4j.driver.Result;
import org.neo4j.driver.Session;
import org.neo4j.driver.TransactionCallback;
import org.neo4j.driver.Values;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import java.util.List;
import java.util.Map;
import java.util.function.Function;

/**
 * 轻量 Neo4j 访问封装：集中 session/tx 管理，避免散落 driver 代码。
 */
@Component
public class Neo4jClient {

    @Autowired
    private Driver driver;

    public <T> T readTx(TransactionCallback<T> work) {
        try (Session session = driver.session()) {
            return session.executeRead(work);
        }
    }

    public <T> T writeTx(TransactionCallback<T> work) {
        try (Session session = driver.session()) {
            return session.executeWrite(work);
        }
    }

    public List<Record> query(String cypher, Map<String, Object> params) {
        return readTx(tx -> {
            Result r = tx.run(cypher, params == null ? Values.parameters() : Values.value(params));
            return r.list();
        });
    }

    public <T> List<T> queryList(String cypher, Map<String, Object> params, Function<Record, T> mapper) {
        return readTx(tx -> tx.run(cypher, params == null ? Values.parameters() : Values.value(params)).list(mapper));
    }
}

