// Seed minimal TBOX in Neo4j for HAI end-to-end demo

MERGE (d:DomainVersion {domainName:'PlantGraph', version:'1.0.0'})
  SET d.status='draft', d.createdBy='seed', d.createdAt=toString(datetime());

// Object types
MERGE (ot1:ObjectType {domainName:'PlantGraph', version:'1.0.0', labelName:'ICSProcess'})
  SET ot1.displayName='工艺过程', ot1.description='Industrial process';
MERGE (ot2:ObjectType {domainName:'PlantGraph', version:'1.0.0', labelName:'BoilerProcess'})
  SET ot2.parentLabel='ICSProcess', ot2.displayName='锅炉过程';
MERGE (ot3:ObjectType {domainName:'PlantGraph', version:'1.0.0', labelName:'SCADAPoint'})
  SET ot3.displayName='点位';
MERGE (ot4:ObjectType {domainName:'PlantGraph', version:'1.0.0', labelName:'PointSample'})
  SET ot4.displayName='采样';
MERGE (ot5:ObjectType {domainName:'PlantGraph', version:'1.0.0', labelName:'AttackWindow'})
  SET ot5.displayName='攻击窗口';

// Properties (minimal)
MERGE (p1:Property {domainName:'PlantGraph', version:'1.0.0', ownerLabel:'ICSProcess', propertyName:'process_id'})
  SET p1.valueType='STRING', p1.columnName='process_id';
MERGE (p2:Property {domainName:'PlantGraph', version:'1.0.0', ownerLabel:'SCADAPoint', propertyName:'tag_name'})
  SET p2.valueType='STRING', p2.columnName='point_tag';
MERGE (p3:Property {domainName:'PlantGraph', version:'1.0.0', ownerLabel:'PointSample', propertyName:'ts'})
  SET p3.valueType='TIMESTAMP', p3.columnName='ts';
MERGE (p4:Property {domainName:'PlantGraph', version:'1.0.0', ownerLabel:'PointSample', propertyName:'value'})
  SET p4.valueType='DOUBLE', p4.columnName='value';
MERGE (p5:Property {domainName:'PlantGraph', version:'1.0.0', ownerLabel:'PointSample', propertyName:'attack_label'})
  SET p5.valueType='BOOLEAN', p5.columnName='attack';

// Attach properties to types
MATCH (t1:ObjectType {domainName:'PlantGraph', version:'1.0.0', labelName:'ICSProcess'}), (p1:Property {domainName:'PlantGraph', version:'1.0.0', ownerLabel:'ICSProcess', propertyName:'process_id'})
MERGE (t1)-[:HAS_PROPERTY]->(p1);
MATCH (t2:ObjectType {domainName:'PlantGraph', version:'1.0.0', labelName:'SCADAPoint'}), (p2:Property {domainName:'PlantGraph', version:'1.0.0', ownerLabel:'SCADAPoint', propertyName:'tag_name'})
MERGE (t2)-[:HAS_PROPERTY]->(p2);
MATCH (t3:ObjectType {domainName:'PlantGraph', version:'1.0.0', labelName:'PointSample'}), (p3:Property {domainName:'PlantGraph', version:'1.0.0', ownerLabel:'PointSample', propertyName:'ts'})
MERGE (t3)-[:HAS_PROPERTY]->(p3);
MATCH (t3:ObjectType {domainName:'PlantGraph', version:'1.0.0', labelName:'PointSample'}), (p4:Property {domainName:'PlantGraph', version:'1.0.0', ownerLabel:'PointSample', propertyName:'value'})
MERGE (t3)-[:HAS_PROPERTY]->(p4);
MATCH (t3:ObjectType {domainName:'PlantGraph', version:'1.0.0', labelName:'PointSample'}), (p5:Property {domainName:'PlantGraph', version:'1.0.0', ownerLabel:'PointSample', propertyName:'attack_label'})
MERGE (t3)-[:HAS_PROPERTY]->(p5);

// ABOX mappings
MERGE (m1:AboxMapping {domainName:'PlantGraph', version:'1.0.0', className:'BoilerProcess'})
  SET m1.mappingStrategy='class_table', m1.objectSourceName='hai_process_catalog', m1.sourceKind='physical_table', m1.primaryKey='process_id', m1.typeFilterSql='';
MERGE (m2:AboxMapping {domainName:'PlantGraph', version:'1.0.0', className:'SCADAPoint'})
  SET m2.mappingStrategy='class_table', m2.objectSourceName='hai_point_catalog', m2.sourceKind='physical_table', m2.primaryKey='point_tag';
MERGE (m3:AboxMapping {domainName:'PlantGraph', version:'1.0.0', className:'PointSample'})
  SET m3.mappingStrategy='class_table', m3.objectSourceName='hai_point_sample', m3.sourceKind='physical_table', m3.primaryKey='point_tag';

MATCH (t:ObjectType {domainName:'PlantGraph', version:'1.0.0', labelName:'BoilerProcess'}), (m1:AboxMapping {domainName:'PlantGraph', version:'1.0.0', className:'BoilerProcess'})
MERGE (t)-[:HAS_ABOX_MAPPING]->(m1);
MATCH (t:ObjectType {domainName:'PlantGraph', version:'1.0.0', labelName:'SCADAPoint'}), (m2:AboxMapping {domainName:'PlantGraph', version:'1.0.0', className:'SCADAPoint'})
MERGE (t)-[:HAS_ABOX_MAPPING]->(m2);
MATCH (t:ObjectType {domainName:'PlantGraph', version:'1.0.0', labelName:'PointSample'}), (m3:AboxMapping {domainName:'PlantGraph', version:'1.0.0', className:'PointSample'})
MERGE (t)-[:HAS_ABOX_MAPPING]->(m3);

// Relation types (for QueryAdapter joins)
MERGE (r1:RelationType {domainName:'PlantGraph', version:'1.0.0', labelName:'HAS_POINT'})
  SET r1.sourceLabel='BoilerProcess', r1.targetLabel='SCADAPoint', r1.sourceKey='process_id', r1.targetKey='process_id', r1.cardinality='one_to_many';
MERGE (r2:RelationType {domainName:'PlantGraph', version:'1.0.0', labelName:'HAS_SAMPLE'})
  SET r2.sourceLabel='SCADAPoint', r2.targetLabel='PointSample', r2.sourceKey='point_tag', r2.targetKey='point_tag', r2.cardinality='one_to_many';

MATCH (r1:RelationType {domainName:'PlantGraph', version:'1.0.0', labelName:'HAS_POINT'}), (s:ObjectType {domainName:'PlantGraph', version:'1.0.0', labelName:'BoilerProcess'}), (t:ObjectType {domainName:'PlantGraph', version:'1.0.0', labelName:'SCADAPoint'})
MERGE (r1)-[:SOURCE_TYPE]->(s)
MERGE (r1)-[:TARGET_TYPE]->(t);

MATCH (r2:RelationType {domainName:'PlantGraph', version:'1.0.0', labelName:'HAS_SAMPLE'}), (s:ObjectType {domainName:'PlantGraph', version:'1.0.0', labelName:'SCADAPoint'}), (t:ObjectType {domainName:'PlantGraph', version:'1.0.0', labelName:'PointSample'})
MERGE (r2)-[:SOURCE_TYPE]->(s)
MERGE (r2)-[:TARGET_TYPE]->(t);

