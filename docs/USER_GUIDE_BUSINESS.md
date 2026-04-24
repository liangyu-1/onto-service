# Ontology Service 业务用户操作手册

适用对象：业务人员、产品经理、数据分析师。

本文档以“操作步骤 + 预期结果”的方式说明如何使用系统完成查询、推理与动作执行。

入口：`http://localhost:8080/`

---

## 0) 前置条件（首次使用必须完成）

首次使用前，请确认环境已完成启动与初始化，否则页面查询可能为空。

### 0.1 启动服务

在项目根目录执行：

```bash
docker-compose up -d
```

### 0.2 初始化 ABOX（Doris）

执行以下脚本初始化 Doris 数据库与示例数据：

```bash
bash scripts/init_doris.sh
```

### 0.3 初始化 TBOX 示例（Neo4j，推荐）

执行以下脚本写入示例 TBOX（用于快速验证页面操作）：

```bash
bash scripts/seed_neo4j.sh
```

完成以上 3 步后，再进入后续“操作步骤”。

---

## 1) 使用目标（3 个闭环）

- **DATA（看数据）**：在「查询测试」里查到业务对象的数据（来自 Doris）
- **LOGIC（看结论）**：在「推理规则」里执行规则，产出派生事实（写 Doris）
- **ACTION（做动作）**：在「Action管理」里 dry-run → submit → 查 status（写 Doris）

---

## 2) 快速验证：执行一次语义查询（无需建模）

本节用于验证“页面可用 + 系统能把语义查询编译为 Doris SQL 并返回结果”。

### 2.1 打开页面

进入 `http://localhost:8080/`，点击顶部 Tab「**查询测试**」。

### 2.2 填写查询参数（示例）

- **域名称**：`PlantGraph`
- **版本**：`1.0.0`
- **targetType**：`BoilerProcess`
- **limit**：`10`
- **selectProperties**：

```json
["process_id"]
```

- **relationPath**：

```json
[]
```

- **filters**：

```json
{}
```

### 2.3 执行

点击「**执行语义查询**」。

### 2.4 预期结果

页面返回结果中应包含：
- **rows**：结果行（允许为空，但通常不应为空）
- **executedSql**：实际执行的 Doris SQL（用于验收/对账）

### 2.5 结果为空时的检查

若 `rows` 为空，请按顺序检查：
1. 是否已执行 `bash scripts/init_doris.sh`（Doris 中是否有示例数据）
2. 是否已执行 `bash scripts/seed_neo4j.sh`（Neo4j 中是否有对象/映射/关系）

---

## 3) 关系导航查询：沿关系从上游对象查询下游对象

本节用于验证“关系导航（JOIN）”是否生效。

仍在「查询测试」Tab，将参数调整为：

- **targetType**：`BoilerProcess`
- **relationPath**：

```json
["HAS_POINT", "HAS_SAMPLE"]
```

- **filters**：

```json
{"process_id":"P1"}
```

点击「执行语义查询」。

预期结果：
- `executedSql` 中出现 JOIN（表示关系导航已生效）
- `rows` 返回结果（字段取决于 selectProperties）

---

## 4) 业务建模：将业务名词对齐到数据表（需要接入自有数据时）

当你需要使用自有业务数据表、以及自定义业务对象/属性/规则/动作时，请按控制台顶部的建模顺序完成建模。

**域管理 → 对象类型 → 属性 → 关系 → TBOX/ABOX映射 → 推理规则 → Action管理**

下面按页面给出“必填项 + 操作步骤 + 预期结果”。

---

## 5) 分页面操作说明

### 5.1 域管理

#### 操作步骤

1. 在「创建域」区域填写域名（例如 `PlantGraph`）。
2. 点击「创建」。
3. 在「版本列表」区域点击「查询」，确认该域存在至少一个版本（例如 `1.0.0`）。

#### 预期结果

- 域创建成功，并在版本列表中可查询到版本号。

---

### 5.2 对象类型

#### 必填项

- **labelName**：对象类型英文名（例如 `Equipment`）

#### 可选项

- displayName：显示名称（例如 `设备`）
- parentLabel：父类（继承）
- aiContext：语义说明

#### 操作步骤

1. 填写必填项（以及可选项）。
2. 点击「创建」。
3. 在「对象类型列表」区域点击「查询」。

#### 预期结果

- 新增对象类型出现在列表中。

---

### 5.3 属性

#### 必填项

- **ownerLabel**：所属对象类型（例如 `Equipment`）
- **propertyName**：属性名称（例如 `temperature`）
- **valueType**：属性类型（例如 `DOUBLE`）

#### 常用项（来自数据表字段时）

- columnName：对应 Doris 的列名（例如 `temp_col`）

#### 操作步骤

1. 填写必填项。
2. 若该属性来自数据表字段，填写 columnName。
3. 点击「创建」。
4. 在列表区域点击「查询」。

#### 预期结果

- 新增属性出现在该对象类型的属性列表中。

---

### 5.4 关系

#### 必填项

- **labelName**：关系名（例如 `HAS_POINT`）
- **sourceLabel**：起点对象类型
- **targetLabel**：终点对象类型
- **sourceKey / targetKey**：JOIN 键（必须是 Doris 表中真实存在的列名）

#### 操作步骤

1. 填写必填项。
2. 点击「创建」。
3. 在关系列表区域点击「查询」。

#### 预期结果

- 关系出现在关系列表中。
- 在「查询测试」执行 relationPath 时，`executedSql` 会出现 JOIN。

---

### 5.5 TBOX/ABOX映射（最关键）

#### 必填项

- **className**：对象类型（例如 `Equipment`）
- **objectSourceName**：Doris 表/视图名
- **primaryKey**：主键列名

#### 操作步骤

1. 填写必填项。
2. 点击「创建」。
3. 在映射列表区域点击「查询」。

#### 预期结果

- 映射出现在列表中。
- 「查询测试」以该 className 作为 targetType 时能够找到数据源并生成 SQL。

---

### 5.6 推理规则（LOGIC）

#### 必填项

- **logicName**：规则名称
- **targetType**：输出对象类型
- **targetProperty**：输出属性
- **expressionSql**：规则表达式/SQL（MVP 支持受限用法）

#### 操作步骤

1. 填写必填项。
2. 点击「创建」。
3. 在规则列表区域点击「查询」。
4. 使用“执行规则”接口（或页面提供的执行按钮）触发计算。

#### 预期结果

- 规则可被查询到。
- 执行后在 Doris 的派生事实表中出现结果（以及运行记录）。

---

### 5.7 Action 管理（ACTION）

#### 创建 Action 定义

必填项：
- **actionName**：Action 名称（例如 `CreateWorkOrder`）
- **toolName**：工具名称（例如 `create_work_order`）

可选项：
- targetType、inputSchemaJson、preconditionSql / preconditionLogic 等

操作步骤：
1. 填写必填项（以及可选项）。
2. 点击「创建」。
3. 在 Action 列表区域点击「查询」确认创建成功。

#### 执行 Action（dry-run → submit → status）

操作步骤：
1. 在「执行 Action」区域填写 domain/version/actionName/targetObjectId。
2. 点击「Dry-run 校验」查看是否允许执行。
3. 点击「提交执行」获取 `actionId`。
4. 通过「查询状态」接口（或页面/工具）查询 `actionId` 的 status。

预期结果：
- dry-run 返回校验结果与预览。
- submit 返回 `actionId`，并在动作实例中可追踪。
- status 可查询到 pending/submitted/success/failed 等状态。

---

## 6) 常见问题与处理方法

- **查询一直空**：通常是 Doris 没初始化或 Neo4j 没 seed / 没建映射
- **关系导航不生效**：sourceKey/targetKey 写错（必须是 Doris 表真实列）
- **动作 dry-run 失败**：目标对象 ID 没填 / 前置条件不满足


