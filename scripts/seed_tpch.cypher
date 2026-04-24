// Seed TPCH Domain + TBOX + ABOX mappings (authoritative in Neo4j)

MERGE (d:DomainVersion {domainName:'TPCH', version:'1.0.0'})
  SET d.status='draft', d.createdBy='seed', d.createdAt=toString(datetime());

// Object types
MERGE (ot1:ObjectType {domainName:'TPCH', version:'1.0.0', labelName:'Customer'}) SET ot1.displayName='Customer';
MERGE (ot2:ObjectType {domainName:'TPCH', version:'1.0.0', labelName:'Orders'}) SET ot2.displayName='Orders';
MERGE (ot3:ObjectType {domainName:'TPCH', version:'1.0.0', labelName:'Lineitem'}) SET ot3.displayName='Lineitem';
MERGE (ot4:ObjectType {domainName:'TPCH', version:'1.0.0', labelName:'Part'}) SET ot4.displayName='Part';
MERGE (ot5:ObjectType {domainName:'TPCH', version:'1.0.0', labelName:'Supplier'}) SET ot5.displayName='Supplier';
MERGE (ot6:ObjectType {domainName:'TPCH', version:'1.0.0', labelName:'Partsupp'}) SET ot6.displayName='Partsupp';
MERGE (ot7:ObjectType {domainName:'TPCH', version:'1.0.0', labelName:'Nation'}) SET ot7.displayName='Nation';
MERGE (ot8:ObjectType {domainName:'TPCH', version:'1.0.0', labelName:'Region'}) SET ot8.displayName='Region';

// Properties (minimal: keys + a few business columns)
MERGE (p1:Property {domainName:'TPCH', version:'1.0.0', ownerLabel:'Customer', propertyName:'custkey'}) SET p1.valueType='INT', p1.columnName='c_custkey';
MERGE (p2:Property {domainName:'TPCH', version:'1.0.0', ownerLabel:'Customer', propertyName:'name'}) SET p2.valueType='STRING', p2.columnName='c_name';
MERGE (p3:Property {domainName:'TPCH', version:'1.0.0', ownerLabel:'Orders', propertyName:'orderkey'}) SET p3.valueType='INT', p3.columnName='o_orderkey';
MERGE (p4:Property {domainName:'TPCH', version:'1.0.0', ownerLabel:'Orders', propertyName:'custkey'}) SET p4.valueType='INT', p4.columnName='o_custkey';
MERGE (p5:Property {domainName:'TPCH', version:'1.0.0', ownerLabel:'Orders', propertyName:'orderdate'}) SET p5.valueType='DATE', p5.columnName='o_orderdate';
MERGE (p6:Property {domainName:'TPCH', version:'1.0.0', ownerLabel:'Lineitem', propertyName:'orderkey'}) SET p6.valueType='INT', p6.columnName='l_orderkey';
MERGE (p7:Property {domainName:'TPCH', version:'1.0.0', ownerLabel:'Lineitem', propertyName:'partkey'}) SET p7.valueType='INT', p7.columnName='l_partkey';
MERGE (p8:Property {domainName:'TPCH', version:'1.0.0', ownerLabel:'Lineitem', propertyName:'suppkey'}) SET p8.valueType='INT', p8.columnName='l_suppkey';
MERGE (p9:Property {domainName:'TPCH', version:'1.0.0', ownerLabel:'Lineitem', propertyName:'quantity'}) SET p9.valueType='DOUBLE', p9.columnName='l_quantity';
MERGE (p10:Property {domainName:'TPCH', version:'1.0.0', ownerLabel:'Part', propertyName:'partkey'}) SET p10.valueType='INT', p10.columnName='p_partkey';
MERGE (p11:Property {domainName:'TPCH', version:'1.0.0', ownerLabel:'Part', propertyName:'name'}) SET p11.valueType='STRING', p11.columnName='p_name';
MERGE (p12:Property {domainName:'TPCH', version:'1.0.0', ownerLabel:'Supplier', propertyName:'suppkey'}) SET p12.valueType='INT', p12.columnName='s_suppkey';
MERGE (p13:Property {domainName:'TPCH', version:'1.0.0', ownerLabel:'Supplier', propertyName:'name'}) SET p13.valueType='STRING', p13.columnName='s_name';
MERGE (p14:Property {domainName:'TPCH', version:'1.0.0', ownerLabel:'Nation', propertyName:'nationkey'}) SET p14.valueType='INT', p14.columnName='n_nationkey';
MERGE (p15:Property {domainName:'TPCH', version:'1.0.0', ownerLabel:'Nation', propertyName:'name'}) SET p15.valueType='STRING', p15.columnName='n_name';
MERGE (p16:Property {domainName:'TPCH', version:'1.0.0', ownerLabel:'Region', propertyName:'regionkey'}) SET p16.valueType='INT', p16.columnName='r_regionkey';
MERGE (p17:Property {domainName:'TPCH', version:'1.0.0', ownerLabel:'Region', propertyName:'name'}) SET p17.valueType='STRING', p17.columnName='r_name';

// Attach properties
MATCH (t:ObjectType {domainName:'TPCH', version:'1.0.0', labelName:'Customer'}), (p:Property {domainName:'TPCH', version:'1.0.0', ownerLabel:'Customer'}) MERGE (t)-[:HAS_PROPERTY]->(p);
MATCH (t:ObjectType {domainName:'TPCH', version:'1.0.0', labelName:'Orders'}), (p:Property {domainName:'TPCH', version:'1.0.0', ownerLabel:'Orders'}) MERGE (t)-[:HAS_PROPERTY]->(p);
MATCH (t:ObjectType {domainName:'TPCH', version:'1.0.0', labelName:'Lineitem'}), (p:Property {domainName:'TPCH', version:'1.0.0', ownerLabel:'Lineitem'}) MERGE (t)-[:HAS_PROPERTY]->(p);
MATCH (t:ObjectType {domainName:'TPCH', version:'1.0.0', labelName:'Part'}), (p:Property {domainName:'TPCH', version:'1.0.0', ownerLabel:'Part'}) MERGE (t)-[:HAS_PROPERTY]->(p);
MATCH (t:ObjectType {domainName:'TPCH', version:'1.0.0', labelName:'Supplier'}), (p:Property {domainName:'TPCH', version:'1.0.0', ownerLabel:'Supplier'}) MERGE (t)-[:HAS_PROPERTY]->(p);
MATCH (t:ObjectType {domainName:'TPCH', version:'1.0.0', labelName:'Nation'}), (p:Property {domainName:'TPCH', version:'1.0.0', ownerLabel:'Nation'}) MERGE (t)-[:HAS_PROPERTY]->(p);
MATCH (t:ObjectType {domainName:'TPCH', version:'1.0.0', labelName:'Region'}), (p:Property {domainName:'TPCH', version:'1.0.0', ownerLabel:'Region'}) MERGE (t)-[:HAS_PROPERTY]->(p);

// ABOX mappings to Doris tables (in database ontology)
MERGE (m1:AboxMapping {domainName:'TPCH', version:'1.0.0', className:'Customer'})
  SET m1.mappingStrategy='class_table', m1.objectSourceName='tpch_customer', m1.sourceKind='physical_table', m1.primaryKey='c_custkey';
MERGE (m2:AboxMapping {domainName:'TPCH', version:'1.0.0', className:'Orders'})
  SET m2.mappingStrategy='class_table', m2.objectSourceName='tpch_orders', m2.sourceKind='physical_table', m2.primaryKey='o_orderkey';
MERGE (m3:AboxMapping {domainName:'TPCH', version:'1.0.0', className:'Lineitem'})
  SET m3.mappingStrategy='class_table', m3.objectSourceName='tpch_lineitem', m3.sourceKind='physical_table', m3.primaryKey='l_orderkey';
MERGE (m4:AboxMapping {domainName:'TPCH', version:'1.0.0', className:'Part'})
  SET m4.mappingStrategy='class_table', m4.objectSourceName='tpch_part', m4.sourceKind='physical_table', m4.primaryKey='p_partkey';
MERGE (m5:AboxMapping {domainName:'TPCH', version:'1.0.0', className:'Supplier'})
  SET m5.mappingStrategy='class_table', m5.objectSourceName='tpch_supplier', m5.sourceKind='physical_table', m5.primaryKey='s_suppkey';
MERGE (m6:AboxMapping {domainName:'TPCH', version:'1.0.0', className:'Partsupp'})
  SET m6.mappingStrategy='class_table', m6.objectSourceName='tpch_partsupp', m6.sourceKind='physical_table', m6.primaryKey='ps_partkey';
MERGE (m7:AboxMapping {domainName:'TPCH', version:'1.0.0', className:'Nation'})
  SET m7.mappingStrategy='class_table', m7.objectSourceName='tpch_nation', m7.sourceKind='physical_table', m7.primaryKey='n_nationkey';
MERGE (m8:AboxMapping {domainName:'TPCH', version:'1.0.0', className:'Region'})
  SET m8.mappingStrategy='class_table', m8.objectSourceName='tpch_region', m8.sourceKind='physical_table', m8.primaryKey='r_regionkey';

MATCH (t:ObjectType {domainName:'TPCH', version:'1.0.0', labelName:'Customer'}), (m:AboxMapping {domainName:'TPCH', version:'1.0.0', className:'Customer'}) MERGE (t)-[:HAS_ABOX_MAPPING]->(m);
MATCH (t:ObjectType {domainName:'TPCH', version:'1.0.0', labelName:'Orders'}), (m:AboxMapping {domainName:'TPCH', version:'1.0.0', className:'Orders'}) MERGE (t)-[:HAS_ABOX_MAPPING]->(m);
MATCH (t:ObjectType {domainName:'TPCH', version:'1.0.0', labelName:'Lineitem'}), (m:AboxMapping {domainName:'TPCH', version:'1.0.0', className:'Lineitem'}) MERGE (t)-[:HAS_ABOX_MAPPING]->(m);
MATCH (t:ObjectType {domainName:'TPCH', version:'1.0.0', labelName:'Part'}), (m:AboxMapping {domainName:'TPCH', version:'1.0.0', className:'Part'}) MERGE (t)-[:HAS_ABOX_MAPPING]->(m);
MATCH (t:ObjectType {domainName:'TPCH', version:'1.0.0', labelName:'Supplier'}), (m:AboxMapping {domainName:'TPCH', version:'1.0.0', className:'Supplier'}) MERGE (t)-[:HAS_ABOX_MAPPING]->(m);
MATCH (t:ObjectType {domainName:'TPCH', version:'1.0.0', labelName:'Partsupp'}), (m:AboxMapping {domainName:'TPCH', version:'1.0.0', className:'Partsupp'}) MERGE (t)-[:HAS_ABOX_MAPPING]->(m);
MATCH (t:ObjectType {domainName:'TPCH', version:'1.0.0', labelName:'Nation'}), (m:AboxMapping {domainName:'TPCH', version:'1.0.0', className:'Nation'}) MERGE (t)-[:HAS_ABOX_MAPPING]->(m);
MATCH (t:ObjectType {domainName:'TPCH', version:'1.0.0', labelName:'Region'}), (m:AboxMapping {domainName:'TPCH', version:'1.0.0', className:'Region'}) MERGE (t)-[:HAS_ABOX_MAPPING]->(m);

// Relationships (JOIN navigation)
MERGE (r1:RelationType {domainName:'TPCH', version:'1.0.0', labelName:'CUSTOMER_ORDERS'})
  SET r1.sourceLabel='Customer', r1.targetLabel='Orders', r1.sourceKey='c_custkey', r1.targetKey='o_custkey', r1.cardinality='one_to_many', r1.outgoingName='orders';
MERGE (r2:RelationType {domainName:'TPCH', version:'1.0.0', labelName:'ORDER_LINEITEM'})
  SET r2.sourceLabel='Orders', r2.targetLabel='Lineitem', r2.sourceKey='o_orderkey', r2.targetKey='l_orderkey', r2.cardinality='one_to_many', r2.outgoingName='lineitems';
MERGE (r3:RelationType {domainName:'TPCH', version:'1.0.0', labelName:'LINEITEM_PART'})
  SET r3.sourceLabel='Lineitem', r3.targetLabel='Part', r3.sourceKey='l_partkey', r3.targetKey='p_partkey', r3.cardinality='many_to_one', r3.outgoingName='part';
MERGE (r4:RelationType {domainName:'TPCH', version:'1.0.0', labelName:'LINEITEM_SUPPLIER'})
  SET r4.sourceLabel='Lineitem', r4.targetLabel='Supplier', r4.sourceKey='l_suppkey', r4.targetKey='s_suppkey', r4.cardinality='many_to_one', r4.outgoingName='supplier';

MATCH (r:RelationType {domainName:'TPCH', version:'1.0.0'}), (s:ObjectType {domainName:'TPCH', version:'1.0.0', labelName:r.sourceLabel}), (t:ObjectType {domainName:'TPCH', version:'1.0.0', labelName:r.targetLabel})
MERGE (r)-[:SOURCE_TYPE]->(s)
MERGE (r)-[:TARGET_TYPE]->(t);

