#!/bin/bash
BOOTSTRAP="${1:-localhost:9092}"
TOPIC="ontology-events"

echo "Sending test TBox events to Kafka: $BOOTSTRAP / topic=$TOPIC"

# 1. Domain Upsert
docker exec -i onto-kafka /opt/kafka/bin/kafka-console-producer.sh \
  --bootstrap-server localhost:9092 --topic "$TOPIC" \
  --property parse.key=true --property key.separator='|' <<'EVENT1'
equipment_domain|{"event_id":"evt_domain_001","event_sequence":1001,"event_type":"DOMAIN_UPSERT","payload":{"timestamp":"2026-05-21T10:00:00Z","domains":{"equipment_domain":{"name":"设备域","description":"描述设备、部件、故障等对象的领域","types":{}}},"code":"0","message":"success"}}
EVENT1
echo "Sent: DOMAIN_UPSERT"

# 2. Type Upsert - 注意：types 结束后需要 }}}} (equipment + types + equipment_domain + domains)
docker exec -i onto-kafka /opt/kafka/bin/kafka-console-producer.sh \
  --bootstrap-server localhost:9092 --topic "$TOPIC" \
  --property parse.key=true --property key.separator='|' <<'EVENT2'
equipment_domain.equipment|{"event_id":"evt_type_001","event_sequence":1002,"event_type":"TYPE_UPSERT","payload":{"timestamp":"2026-05-21T10:00:01Z","domains":{"equipment_domain":{"name":"设备域","description":"描述设备、部件、故障等对象的领域","types":{"equipment":{"name":"设备","description":"工业现场中的物理设备","display_property":"equipment_name","properties":{},"relationships":{},"functions":{}}}}},"code":"0","message":"success"}}
EVENT2
echo "Sent: TYPE_UPSERT"

# 3. Property Upsert
docker exec -i onto-kafka /opt/kafka/bin/kafka-console-producer.sh \
  --bootstrap-server localhost:9092 --topic "$TOPIC" \
  --property parse.key=true --property key.separator='|' <<'EVENT3'
equipment_domain.equipment.equipment_id|{"event_id":"evt_prop_001","event_sequence":1003,"event_type":"PROPERTY_UPSERT","payload":{"timestamp":"2026-05-21T10:00:02Z","domains":{"equipment_domain":{"name":"设备域","description":"描述设备、部件、故障等对象的领域","types":{"equipment":{"name":"设备","description":"工业现场中的物理设备","display_property":"equipment_name","properties":{"equipment_id":{"name":"设备ID","type":"string","description":"设备唯一标识","binding":{"datasource":"iot_ds","schema":"public","database":"iot_db","table":"dim_equipment","column":"equipment_id"},"pk_column":true}},"relationships":{},"functions":{}}}}},"code":"0","message":"success"}}
EVENT3
echo "Sent: PROPERTY_UPSERT"

# 4. Function Upsert
docker exec -i onto-kafka /opt/kafka/bin/kafka-console-producer.sh \
  --bootstrap-server localhost:9092 --topic "$TOPIC" \
  --property parse.key=true --property key.separator='|' <<'EVENT4'
equipment_domain.equipment.equipment_fault_stat|{"event_id":"evt_func_001","event_sequence":1004,"event_type":"FUNCTION_UPSERT","payload":{"timestamp":"2026-05-21T10:00:03Z","domains":{"equipment_domain":{"name":"设备域","description":"描述设备、部件、故障等对象的领域","types":{"equipment":{"name":"设备","description":"工业现场中的物理设备","display_property":"equipment_name","properties":{},"relationships":{},"functions":{"equipment_fault_stat":{"name":"设备故障统计","description":"按设备维度统计故障次数","dimensions":["equipment_domain.equipment.equipment_id","equipment_domain.equipment.equipment_name"],"measures":{"fault_count":{"name":"故障次数","description":"统计设备关联的故障数量","property":"fault_domain.fault.fault_id","agg":"count","segments":"fault_domain.fault.status = 'active'","relations":["equipment_domain.equipment.has_fault"]}}}}}}}},"code":"0","message":"success"}}
EVENT4
echo "Sent: FUNCTION_UPSERT"

# 5. Full Sync Required
docker exec -i onto-kafka /opt/kafka/bin/kafka-console-producer.sh \
  --bootstrap-server localhost:9092 --topic "$TOPIC" \
  --property parse.key=true --property key.separator='|' <<'EVENT5'
full_sync|{"event_id":"evt_ctrl_001","event_sequence":1005,"event_type":"FULL_SYNC_REQUIRED","payload":{"timestamp":"2026-05-21T10:00:04Z","domains":{},"code":"0","message":"full sync required"}}
EVENT5
echo "Sent: FULL_SYNC_REQUIRED"

echo ""
echo "All 5 test events sent!"
