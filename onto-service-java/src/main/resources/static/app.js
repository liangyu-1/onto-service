const API = '/api/v1';

/** DomainController 返回裸 JSON；其余接口多为 Result { code, message, data } */
function unwrapApiPayload(data) {
  if (data != null && typeof data === 'object' && !Array.isArray(data)
      && typeof data.code === 'number' && Object.prototype.hasOwnProperty.call(data, 'data')) {
    return data.data;
  }
  return data;
}

function toRowList(data) {
  const p = unwrapApiPayload(data);
  if (p == null) return [];
  return Array.isArray(p) ? p : [p];
}

/**
 * 与《本体平台设计方案》Semantic Layer 元数据顺序一致：
 * ontology_domain → node_type → property → edge_type → class_abox_mapping → ontology_logic → ontology_action
 */
const TAB_ORDER = ['domains', 'objectTypes', 'properties', 'relationships', 'aboxMappings', 'logic', 'actions'];

const WF_NEXT_HINT = {
  objectTypes: '请先在本体域中创建并查询到至少一个版本。',
  properties: '请先在「对象类型」中至少定义一个类型标签。',
  relationships: '请先在「属性」中至少为一个对象类型定义属性。',
  aboxMappings: '请先在「关系」中至少创建一条关系。',
  logic: '请先在「TBOX/ABOX 映射」中至少完成一条类映射。',
  actions: '请先在「推理规则」中至少定义一条规则。'
};

let wfMaxUnlockedIndex = 0;

/** 与当前建模上下文一致：优先各 Tab 的查询/编辑域，避免只用 d_query 与刚提交的表单不一致 */
function workspaceDomain() {
  const keys = ['ot_qdomain', 'ot_domain', 'p_qdomain', 'p_domain', 'r_qdomain', 'r_domain', 'm_qdomain', 'm_domain', 'l_qdomain', 'l_domain', 'a_qdomain', 'a_domain', 'e_domain', 'd_query'];
  for (let i = 0; i < keys.length; i++) {
    const v = val(keys[i]);
    if (v && String(v).trim()) return String(v).trim();
  }
  return 'PlantGraph';
}

function workspaceVersionHint() {
  const keys = ['ot_qversion', 'ot_version', 'p_qversion', 'p_version', 'r_qversion', 'r_version', 'm_qversion', 'm_version', 'l_qversion', 'l_version', 'a_qversion', 'a_version', 'e_version'];
  for (let i = 0; i < keys.length; i++) {
    const v = val(keys[i]);
    if (v && String(v).trim()) return String(v).trim();
  }
  return '';
}

function pickWorkingVersion(versions, preferred) {
  const pref = (preferred || '').trim();
  if (pref && versions.some(v => v.version === pref)) return pref;
  return versions.length ? versions[versions.length - 1].version : '1.0.0';
}

function syncWorkspaceInputs(domain, version) {
  const pairs = [
    ['ot_domain', domain], ['ot_qdomain', domain],
    ['p_domain', domain], ['p_qdomain', domain],
    ['r_domain', domain], ['r_qdomain', domain],
    ['l_domain', domain], ['l_qdomain', domain],
    ['m_domain', domain], ['m_qdomain', domain],
    ['a_domain', domain], ['a_qdomain', domain],
    ['e_domain', domain],
    ['ot_version', version], ['ot_qversion', version],
    ['p_version', version], ['p_qversion', version],
    ['r_version', version], ['r_qversion', version],
    ['l_version', version], ['l_qversion', version],
    ['m_version', version], ['m_qversion', version],
    ['a_version', version], ['a_qversion', version],
    ['e_version', version],
    ['rdf_domain', domain],
    ['rdf_version', version]
  ];
  pairs.forEach(([id, v]) => {
    const el = document.getElementById(id);
    if (el) el.value = v;
  });
}

function setPanelEditGated(panelId, canEdit) {
  const panel = document.getElementById(panelId);
  if (!panel) return;
  panel.querySelectorAll('.wf-gate-edit input, .wf-gate-edit select, .wf-gate-edit textarea, .wf-gate-edit button').forEach(el => {
    el.disabled = !canEdit;
  });
}

function updateWorkflowUi() {
  document.querySelectorAll('.tab').forEach(tab => {
    const idx = TAB_ORDER.indexOf(tab.dataset.tab);
    tab.classList.toggle('tab-muted', idx > wfMaxUnlockedIndex);
    tab.classList.toggle('tab-next', idx === wfMaxUnlockedIndex + 1 && wfMaxUnlockedIndex < TAB_ORDER.length - 1);
  });
  TAB_ORDER.forEach((pid, idx) => {
    if (pid === 'domains') return;
    setPanelEditGated(pid, idx <= wfMaxUnlockedIndex);
  });
  const b = document.getElementById('wf_banner');
  if (!b) return;
  if (wfMaxUnlockedIndex >= TAB_ORDER.length - 1) {
    b.textContent = '';
    b.classList.remove('visible');
    return;
  }
  const nextId = TAB_ORDER[wfMaxUnlockedIndex + 1];
  const hint = nextId ? WF_NEXT_HINT[nextId] : '';
  if (hint) {
    b.textContent = hint;
    b.classList.add('visible');
  } else {
    b.textContent = '';
    b.classList.remove('visible');
  }
}

async function refreshWorkflowLocks() {
  const domain = workspaceDomain();
  const verRes = await request(API + '/domains/' + encodeURIComponent(domain) + '/versions', 'GET');
  const versions = verRes.ok ? toRowList(verRes.data) : [];
  const hasVersion = versions.length > 0;
  if (!hasVersion) {
    wfMaxUnlockedIndex = 0;
    updateWorkflowUi();
    return;
  }
  const version = pickWorkingVersion(versions, workspaceVersionHint());

  const otRes = await request(
    API + '/semantic/' + encodeURIComponent(domain) + '/' + encodeURIComponent(version) + '/object-types',
    'GET');
  const types = otRes.ok ? toRowList(otRes.data) : [];
  const hasObjectType = types.length > 0;

  let hasProperty = false;
  if (hasObjectType) {
    for (let i = 0; i < types.length; i++) {
      const label = types[i].labelName;
      const pr = await request(
        API + '/semantic/' + encodeURIComponent(domain) + '/' + encodeURIComponent(version) +
          '/object-types/' + encodeURIComponent(label) + '/properties?visibleOnly=false',
        'GET');
      if (pr.ok && toRowList(pr.data).length > 0) {
        hasProperty = true;
        break;
      }
    }
  }

  const relRes = await request(
    API + '/semantic/' + encodeURIComponent(domain) + '/' + encodeURIComponent(version) + '/relationships',
    'GET');
  const rels = relRes.ok ? toRowList(relRes.data) : [];
  const hasRelationshipReady = hasProperty && rels.length > 0;

  const mapRes = await request(
    API + '/abox-mappings/' + encodeURIComponent(domain) + '/' + encodeURIComponent(version),
    'GET');
  const maps = mapRes.ok ? toRowList(mapRes.data) : [];
  const hasAnyMapping = hasRelationshipReady && maps.length > 0;

  const logicRes = await request(API + '/logic/' + encodeURIComponent(domain) + '/' + encodeURIComponent(version), 'GET');
  const logics = logicRes.ok ? toRowList(logicRes.data) : [];
  const hasAnyLogic = hasAnyMapping && logics.length > 0;

  let max = 0;
  if (hasVersion) max = 1;
  if (hasObjectType) max = 2;
  if (hasProperty) max = 3;
  if (hasRelationshipReady) max = 4;
  if (hasAnyMapping) max = 5;
  if (hasAnyLogic) max = 6;
  wfMaxUnlockedIndex = max;
  updateWorkflowUi();
}

function showTab(name, btn) {
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
  const tabBtn = btn || document.querySelector('.tab[data-tab="' + name + '"]');
  if (tabBtn) tabBtn.classList.add('active');
  const panel = document.getElementById(name);
  if (panel) panel.classList.add('active');
  updateWorkflowUi();
}

/**
 * 创建成功后进入下一 Tab。list* 已调用 refreshWorkflowLocks 后，仍用 max(wf, next) 防止读库略慢导致门禁低于「刚完成的下一步」。
 */
function goToNextTabAfterCreate(currentStepIndex) {
  const next = currentStepIndex + 1;
  if (next >= TAB_ORDER.length) return;
  wfMaxUnlockedIndex = Math.max(wfMaxUnlockedIndex, next);
  updateWorkflowUi();
  showTab(TAB_ORDER[next], null);
  const p = document.getElementById(TAB_ORDER[next]);
  if (p && p.scrollIntoView) p.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

document.querySelectorAll('.tab').forEach(tab => {
  tab.addEventListener('click', function() { showTab(this.dataset.tab, this); });
});

function showResult(id, data, isError) {
  const el = document.getElementById(id);
  if (!el) return;
  el.className = 'result' + (isError ? ' error' : '');
  el.textContent = typeof data === 'string' ? data : JSON.stringify(data, null, 2);
}

async function request(url, method, body) {
  try {
    const m = method || 'GET';
    const headers = {};
    if (body != null) headers['Content-Type'] = 'application/json';
    const res = await fetch(url, {
      method: m,
      headers,
      body: body ? JSON.stringify(body) : undefined
    });
    const text = await res.text();
    let data;
    try { data = JSON.parse(text); } catch(e) { data = text; }
    return { ok: res.ok, status: res.status, data };
  } catch (e) {
    return { ok: false, status: 0, data: 'Network error: ' + e.message };
  }
}

function val(id) { return document.getElementById(id)?.value || ''; }
function bool(id) { return document.getElementById(id)?.checked || false; }
function parseJson(str) { try { return str ? JSON.parse(str) : null; } catch(e) { return null; } }

function renderTable(containerId, rows, columns, emptyMsg) {
  const el = document.getElementById(containerId);
  if (!rows || rows.length === 0) { el.innerHTML = '<div class="empty">' + (emptyMsg || '暂无数据') + '</div>'; return; }
  let html = '<table><thead><tr>';
  columns.forEach(c => { html += '<th>' + c.label + '</th>'; });
  html += '</tr></thead><tbody>';
  rows.forEach(row => {
    html += '<tr>';
    columns.forEach(c => {
      let v = row[c.key];
      if (v === null || v === undefined) v = '';
      if (c.format) v = c.format(v, row);
      html += '<td>' + v + '</td>';
    });
    html += '</tr>';
  });
  html += '</tbody></table>';
  el.innerHTML = html;
}

// ========== 域管理 ==========
async function createDomain() {
  const body = { domainName: val('d_name'), status: val('d_status'), ddlSql: val('d_ddl'), createdBy: 'admin' };
  const { ok, data } = await request(API + '/domains', 'POST', body);
  showResult('d_result', data, !ok);
  if (ok) {
    document.getElementById('d_query').value = body.domainName;
    await listDomains();
    goToNextTabAfterCreate(0);
  } else {
    await refreshWorkflowLocks();
  }
}

async function listDomains() {
  const name = val('d_query') || 'PlantGraph';
  const el = document.getElementById('d_list');
  el.innerHTML = '<div class="loading">加载中...</div>';
  const { ok, data } = await request(API + '/domains/' + encodeURIComponent(name) + '/versions', 'GET');
  if (!ok) {
    el.innerHTML = '<div class="empty">查询失败: ' + JSON.stringify(data) + '</div>';
    await refreshWorkflowLocks();
    return;
  }
  const list = toRowList(data);
  renderTable('d_list', list, [
    { key: 'domainName', label: '域名称' },
    { key: 'version', label: '版本' },
    { key: 'status', label: '状态', format: v => '<span class="badge ' + v + '">' + v + '</span>' },
    { key: 'createdAt', label: '创建时间' }
  ], '暂无版本数据');
  if (list.length) {
    const row = list[list.length - 1];
    syncWorkspaceInputs(row.domainName, row.version);
  }
  await refreshWorkflowLocks();
}

// ========== RDF/OWL 工件 ==========
async function exportRdfOwl() {
  const domain = val('rdf_domain') || workspaceDomain();
  const version = val('rdf_version') || workspaceVersionHint() || '1.0.0';
  const format = val('rdf_format') || 'ttl';
  const baseIri = val('rdf_baseIri') || '';
  const url = API + '/artifacts/' + encodeURIComponent(domain) + '/' + encodeURIComponent(version) +
    '/rdf-owl?format=' + encodeURIComponent(format) +
    (baseIri ? ('&baseIri=' + encodeURIComponent(baseIri)) : '') +
    '&persist=true';
  const { ok, data } = await request(url, 'GET');
  if (!ok) {
    showResult('rdf_result', data, true);
    return;
  }
  const text = typeof data === 'string' ? data : JSON.stringify(data, null, 2);
  const ta = document.getElementById('rdf_content');
  if (ta) ta.value = text;
  showResult('rdf_result', { ok: true, domain, version, format, persisted: true }, false);
}

async function uploadRdfOwl() {
  const domain = val('rdf_domain') || workspaceDomain();
  const version = val('rdf_version') || workspaceVersionHint() || '1.0.0';
  const format = val('rdf_format') || 'ttl';
  const baseIri = val('rdf_baseIri') || '';
  const content = val('rdf_content') || '';
  const body = { format, baseIri, content, createdBy: 'admin' };
  const { ok, data } = await request(
    API + '/artifacts/' + encodeURIComponent(domain) + '/' + encodeURIComponent(version) + '/rdf-owl',
    'POST',
    body
  );
  showResult('rdf_result', data, !ok);
}

async function listRdfOwlArtifacts() {
  const domain = val('rdf_domain') || workspaceDomain();
  const version = val('rdf_version') || workspaceVersionHint() || '1.0.0';
  const { ok, data } = await request(API + '/artifacts/' + encodeURIComponent(domain) + '/' + encodeURIComponent(version), 'GET');
  if (!ok) {
    showResult('rdf_result', data, true);
    return;
  }
  const rows = toRowList(data).filter(r => r && r.artifactKind === 'rdf_owl');
  showResult('rdf_result', rows, false);
}

// ========== 对象类型 ==========
async function createObjectType() {
  const body = {
    labelName: val('ot_label'), parentLabel: val('ot_parent') || null,
    displayName: val('ot_display') || null, description: val('ot_desc') || null
  };
  const { ok, data } = await request(API + '/semantic/' + val('ot_domain') + '/' + val('ot_version') + '/object-types', 'POST', body);
  showResult('ot_result', data, !ok);
  if (ok) {
    syncWorkspaceInputs(val('ot_domain'), val('ot_version'));
    await listObjectTypes();
    goToNextTabAfterCreate(1);
  }
}

async function listObjectTypes() {
  const el = document.getElementById('ot_list');
  el.innerHTML = '<div class="loading">加载中...</div>';
  const { ok, data } = await request(API + '/semantic/' + val('ot_qdomain') + '/' + val('ot_qversion') + '/object-types', 'GET');
  if (!ok) { el.innerHTML = '<div class="empty">查询失败</div>'; await refreshWorkflowLocks(); return; }
  renderTable('ot_list', toRowList(data), [
    { key: 'labelName', label: '标签' },
    { key: 'displayName', label: '显示名' },
    { key: 'parentLabel', label: '父类型' },
    { key: 'description', label: '描述' }
  ]);
  await refreshWorkflowLocks();
}

// ========== 属性 ==========
async function createProperty() {
  const body = {
    propertyName: val('p_name'), ownerLabel: val('p_owner'), valueType: val('p_type'),
    columnName: val('p_column') || null, expressionSql: val('p_expr') || null,
    isMeasure: bool('p_isMeasure'), semanticRole: val('p_role') || null,
    description: val('p_desc') || null
  };
  const { ok, data } = await request(API + '/semantic/' + val('p_domain') + '/' + val('p_version') + '/properties', 'POST', body);
  showResult('p_result', data, !ok);
  if (ok) {
    syncWorkspaceInputs(val('p_domain'), val('p_version'));
    document.getElementById('p_qowner').value = val('p_owner');
    await listProperties();
    goToNextTabAfterCreate(2);
  }
}

async function listProperties() {
  const el = document.getElementById('p_list');
  el.innerHTML = '<div class="loading">加载中...</div>';
  const { ok, data } = await request(API + '/semantic/' + val('p_qdomain') + '/' + val('p_qversion') + '/object-types/' + val('p_qowner') + '/properties?visibleOnly=false', 'GET');
  if (!ok) { el.innerHTML = '<div class="empty">查询失败</div>'; await refreshWorkflowLocks(); return; }
  renderTable('p_list', toRowList(data), [
    { key: 'propertyName', label: '属性名' },
    { key: 'valueType', label: '值类型' },
    { key: 'columnName', label: '映射列' },
    { key: 'isMeasure', label: '是否指标', format: v => v ? '是' : '否' },
    { key: 'semanticRole', label: '语义角色' },
    { key: 'description', label: '描述' }
  ]);
  await refreshWorkflowLocks();
}

// ========== 关系 ==========
async function createRelationship() {
  const body = {
    labelName: val('r_label'), sourceLabel: val('r_source'), targetLabel: val('r_target'),
    edgeTable: val('r_edgeTable') || null, sourceKey: val('r_sourceKey') || null,
    targetKey: val('r_targetKey') || null, cardinality: val('r_cardinality') || null,
    outgoingName: val('r_out') || null, incomingName: val('r_in') || null,
    outgoingIsMulti: bool('r_outMulti'), incomingIsMulti: bool('r_inMulti'),
    description: val('r_desc') || null
  };
  const { ok, data } = await request(API + '/semantic/' + val('r_domain') + '/' + val('r_version') + '/relationships', 'POST', body);
  showResult('r_result', data, !ok);
  if (ok) {
    syncWorkspaceInputs(val('r_domain'), val('r_version'));
    await listRelationships();
    goToNextTabAfterCreate(3);
  }
}

async function listRelationships() {
  const el = document.getElementById('r_list');
  el.innerHTML = '<div class="loading">加载中...</div>';
  const { ok, data } = await request(API + '/semantic/' + val('r_qdomain') + '/' + val('r_qversion') + '/relationships', 'GET');
  if (!ok) { el.innerHTML = '<div class="empty">查询失败</div>'; await refreshWorkflowLocks(); return; }
  renderTable('r_list', toRowList(data), [
    { key: 'labelName', label: '关系名' },
    { key: 'sourceLabel', label: '源类型' },
    { key: 'targetLabel', label: '目标类型' },
    { key: 'cardinality', label: '基数' },
    { key: 'edgeTable', label: '边表' }
  ]);
  await refreshWorkflowLocks();
}

// ========== TBOX/ABOX 映射 ==========
async function createMapping() {
  const body = {
    className: val('m_class'), parentClass: val('m_parent') || null,
    mappingStrategy: val('m_strategy') || null, objectSourceName: val('m_sourceName') || null,
    sourceKind: val('m_sourceKind') || null, primaryKey: val('m_pk') || null,
    discriminatorColumn: val('m_disc') || null, typeFilterSql: val('m_filter') || null,
    propertyProjectionJson: val('m_proj') || null, viewSql: val('m_viewSql') || null,
    materializationStrategy: val('m_material') || null, aiContext: val('m_ai') || null
  };
  const { ok, data } = await request(API + '/abox-mappings/' + val('m_domain') + '/' + val('m_version'), 'POST', body);
  showResult('m_result', data, !ok);
  if (ok) {
    syncWorkspaceInputs(val('m_domain'), val('m_version'));
    await listMappings();
    goToNextTabAfterCreate(4);
  }
}

async function listMappings() {
  const el = document.getElementById('m_list');
  el.innerHTML = '<div class="loading">加载中...</div>';
  const { ok, data } = await request(API + '/abox-mappings/' + val('m_qdomain') + '/' + val('m_qversion'), 'GET');
  if (!ok) { el.innerHTML = '<div class="empty">查询失败</div>'; await refreshWorkflowLocks(); return; }
  renderTable('m_list', toRowList(data), [
    { key: 'className', label: '类名' },
    { key: 'mappingStrategy', label: '映射策略' },
    { key: 'objectSourceName', label: '源名称' },
    { key: 'sourceKind', label: '源类型' },
    { key: 'primaryKey', label: '主键' }
  ]);
  await refreshWorkflowLocks();
}

// ========== 推理规则 ==========
async function createLogic() {
  const body = {
    logicName: val('l_name'), targetType: val('l_targetType') || null,
    targetProperty: val('l_targetProp') || null, logicKind: val('l_kind') || null,
    implementationType: val('l_impl') || null, expressionSql: val('l_sql') || null,
    outputType: val('l_outputType') || null, executionModeHint: val('l_mode') || null,
    deterministic: bool('l_deterministic'), description: val('l_desc') || null
  };
  const { ok, data } = await request(API + '/logic/' + val('l_domain') + '/' + val('l_version'), 'POST', body);
  showResult('l_result', data, !ok);
  if (ok) {
    syncWorkspaceInputs(val('l_domain'), val('l_version'));
    await listLogic();
    goToNextTabAfterCreate(5);
  }
}

async function listLogic() {
  const el = document.getElementById('l_list');
  el.innerHTML = '<div class="loading">加载中...</div>';
  const { ok, data } = await request(API + '/logic/' + val('l_qdomain') + '/' + val('l_qversion'), 'GET');
  if (!ok) { el.innerHTML = '<div class="empty">查询失败</div>'; await refreshWorkflowLocks(); return; }
  renderTable('l_list', toRowList(data), [
    { key: 'logicName', label: '规则名' },
    { key: 'logicKind', label: '类型' },
    { key: 'targetType', label: '目标类型' },
    { key: 'implementationType', label: '实现' },
    { key: 'executionModeHint', label: '执行模式' }
  ]);
  await refreshWorkflowLocks();
}

// ========== Action 管理 ==========
async function createAction() {
  const body = {
    actionName: val('a_name'), toolName: val('a_tool') || null,
    targetType: val('a_target') || null, invocationMode: val('a_mode') || null,
    inputSchemaJson: val('a_inputSchema') || null, outputSchemaJson: val('a_outputSchema') || null,
    preconditionSql: val('a_preSql') || null, preconditionLogic: val('a_preLogic') || null,
    externalPlatform: val('a_platform') || null, externalActionRef: val('a_ref') || null,
    dryRunRequired: bool('a_dryRun'), aiContext: val('a_ai') || null
  };
  const { ok, data } = await request(API + '/actions/definitions/' + val('a_domain') + '/' + val('a_version'), 'POST', body);
  showResult('a_result', data, !ok);
  if (ok) {
    syncWorkspaceInputs(val('a_domain'), val('a_version'));
    await listActions();
    goToNextTabAfterCreate(6);
  }
}

async function listActions() {
  const el = document.getElementById('a_list');
  el.innerHTML = '<div class="loading">加载中...</div>';
  const { ok, data } = await request(API + '/actions/definitions/' + val('a_qdomain') + '/' + val('a_qversion'), 'GET');
  if (!ok) { el.innerHTML = '<div class="empty">查询失败</div>'; await refreshWorkflowLocks(); return; }
  renderTable('a_list', toRowList(data), [
    { key: 'actionName', label: 'Action名' },
    { key: 'toolName', label: 'Tool名' },
    { key: 'targetType', label: '目标类型' },
    { key: 'invocationMode', label: '调用模式' },
    { key: 'dryRunRequired', label: '必须先dry-run', format: v => v ? '是' : '否' }
  ]);
  await refreshWorkflowLocks();
}

async function dryRunAction() {
  const body = {
    domainName: val('e_domain'), version: val('e_version'), actionName: val('e_name'),
    targetObjectId: val('e_targetId'), input: parseJson(val('e_input')),
    dryRun: true, requestedBy: val('e_by')
  };
  const { ok, data } = await request(API + '/actions/dry-run', 'POST', body);
  showResult('e_result', data, !ok);
}

async function submitAction() {
  const body = {
    domainName: val('e_domain'), version: val('e_version'), actionName: val('e_name'),
    targetObjectId: val('e_targetId'), input: parseJson(val('e_input')),
    dryRun: bool('e_dryRun'), requestedBy: val('e_by')
  };
  const { ok, data } = await request(API + '/actions/submit', 'POST', body);
  showResult('e_result', data, !ok);
}

document.addEventListener('DOMContentLoaded', function () {
  wfMaxUnlockedIndex = 0;
  updateWorkflowUi();
  listDomains();
});
