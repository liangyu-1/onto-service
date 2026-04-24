const API = '/api/v1';

function qs(id) { return document.getElementById(id); }
function setStatus(msg) { qs('status').textContent = msg || ''; }
function setErrors(msg) { qs('errors').innerHTML = msg ? `<div class="err">${escapeHtml(msg)}</div>` : '<div class="muted">无</div>'; }
function setInspect(obj) {
  if (!obj) { qs('inspect').innerHTML = '<div class="muted">未选择</div>'; return; }
  const entries = Object.entries(obj);
  qs('inspect').innerHTML = entries.map(([k, v]) => `
    <div class="k">${escapeHtml(k)}</div>
    <div class="v">${escapeHtml(typeof v === 'string' ? v : JSON.stringify(v))}</div>
  `).join('');
}

function escapeHtml(s) {
  return String(s ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

async function request(url) {
  const r = await fetch(url);
  const text = await r.text();
  let data;
  try { data = JSON.parse(text); } catch { data = text; }
  if (!r.ok) throw new Error(typeof data === 'string' ? data : (data?.message || JSON.stringify(data)));
  // Support Result{code,message,data} and raw payload
  if (data && typeof data === 'object' && !Array.isArray(data) && typeof data.code === 'number' && 'data' in data) return data.data;
  return data;
}

/**
 * D3Vis: minimal ontology graph viewer
 * - nodes: object types
 * - links: relation types
 */
class D3Vis {
  constructor(svg) {
    this.svg = svg;
    this.width = 800;
    this.height = 600;
    this.nodes = [];
    this.links = [];
    this.transform = d3.zoomIdentity;

    this.root = d3.select(svg);
    this.root.attr('viewBox', `0 0 ${this.width} ${this.height}`);
    this.root.style('cursor', 'grab');

    this.g = this.root.append('g');
    this.linkG = this.g.append('g').attr('stroke', 'rgba(233,238,252,0.35)').attr('stroke-width', 1.4);
    this.nodeG = this.g.append('g');
    this.labelG = this.g.append('g').attr('pointer-events', 'none');

    this.zoom = d3.zoom()
      .scaleExtent([0.2, 3])
      .on('zoom', (ev) => {
        this.transform = ev.transform;
        this.g.attr('transform', this.transform);
      });
    this.root.call(this.zoom);

    this.sim = d3.forceSimulation()
      .force('link', d3.forceLink().id(d => d.id).distance(90).strength(0.8))
      .force('charge', d3.forceManyBody().strength(-320))
      .force('center', d3.forceCenter(this.width / 2, this.height / 2))
      .force('collide', d3.forceCollide().radius(d => (d._r || 18) + 10));

    const resize = () => {
      const rect = this.svg.getBoundingClientRect();
      this.width = Math.max(600, Math.floor(rect.width));
      this.height = Math.max(400, Math.floor(rect.height));
      this.root.attr('viewBox', `0 0 ${this.width} ${this.height}`);
      this.sim.force('center', d3.forceCenter(this.width / 2, this.height / 2));
      this.sim.alpha(0.6).restart();
    };
    window.addEventListener('resize', resize);
    resize();
  }

  setData(nodes, links) {
    this.nodes = nodes || [];
    this.links = links || [];

    // degree for sizing
    const deg = new Map();
    this.links.forEach(l => {
      deg.set(l.source, (deg.get(l.source) || 0) + 1);
      deg.set(l.target, (deg.get(l.target) || 0) + 1);
    });
    this.nodes.forEach(n => {
      const d = deg.get(n.id) || 0;
      n._deg = d;
      n._r = 14 + Math.min(14, d * 2);
    });

    this.render();
    this.sim.nodes(this.nodes).on('tick', () => this.ticked());
    this.sim.force('link').links(this.links);
    this.sim.alpha(1).restart();
  }

  render() {
    // links
    this.linkSel = this.linkG.selectAll('line').data(this.links, d => d.id);
    this.linkSel.exit().remove();
    const linkEnter = this.linkSel.enter().append('line')
      .attr('stroke', 'rgba(233,238,252,0.28)')
      .attr('stroke-width', 1.5)
      .on('click', (_, d) => setInspect({ type: 'RelationType', ...d.meta }));
    this.linkSel = linkEnter.merge(this.linkSel);

    // link labels
    this.linkLabelSel = this.labelG.selectAll('text.linkLabel').data(this.links, d => d.id);
    this.linkLabelSel.exit().remove();
    const llEnter = this.linkLabelSel.enter().append('text')
      .attr('class', 'linkLabel')
      .attr('fill', 'rgba(233,238,252,0.55)')
      .attr('font-size', 10)
      .attr('text-anchor', 'middle')
      .text(d => d.label);
    this.linkLabelSel = llEnter.merge(this.linkLabelSel);

    // nodes
    this.nodeSel = this.nodeG.selectAll('g.node').data(this.nodes, d => d.id);
    this.nodeSel.exit().remove();
    const nodeEnter = this.nodeSel.enter().append('g').attr('class', 'node')
      .call(d3.drag()
        .on('start', (ev, d) => {
          this.root.style('cursor', 'grabbing');
          if (!ev.active) this.sim.alphaTarget(0.3).restart();
          d.fx = d.x; d.fy = d.y;
        })
        .on('drag', (ev, d) => { d.fx = ev.x; d.fy = ev.y; })
        .on('end', (ev, d) => {
          this.root.style('cursor', 'grab');
          if (!ev.active) this.sim.alphaTarget(0);
          d.fx = null; d.fy = null;
        })
      )
      .on('click', (_, d) => setInspect({ type: 'ObjectType', ...d.meta }));

    nodeEnter.append('circle')
      .attr('r', d => d._r || 18)
      .attr('fill', d => d._deg ? 'rgba(45,108,255,0.45)' : 'rgba(255,255,255,0.10)')
      .attr('stroke', 'rgba(233,238,252,0.45)')
      .attr('stroke-width', 1.2);

    nodeEnter.append('text')
      .attr('y', d => (d._r || 18) + 12)
      .attr('fill', '#e9eefc')
      .attr('font-size', 12)
      .attr('text-anchor', 'middle')
      .text(d => d.label);

    this.nodeSel = nodeEnter.merge(this.nodeSel);
  }

  ticked() {
    this.linkSel
      .attr('x1', d => d.source.x)
      .attr('y1', d => d.source.y)
      .attr('x2', d => d.target.x)
      .attr('y2', d => d.target.y);

    this.nodeSel.attr('transform', d => `translate(${d.x},${d.y})`);

    this.linkLabelSel
      .attr('x', d => (d.source.x + d.target.x) / 2)
      .attr('y', d => (d.source.y + d.target.y) / 2);
  }

  fit() {
    if (!this.nodes.length) return;
    const xs = this.nodes.map(n => n.x).filter(Number.isFinite);
    const ys = this.nodes.map(n => n.y).filter(Number.isFinite);
    if (!xs.length || !ys.length) return;
    const minX = Math.min(...xs), maxX = Math.max(...xs);
    const minY = Math.min(...ys), maxY = Math.max(...ys);
    const pad = 60;
    const w = Math.max(1, maxX - minX + pad * 2);
    const h = Math.max(1, maxY - minY + pad * 2);
    const scale = Math.min(2.5, Math.max(0.2, Math.min(this.width / w, this.height / h)));
    const tx = (this.width / 2) - scale * ((minX + maxX) / 2);
    const ty = (this.height / 2) - scale * ((minY + maxY) / 2);
    const t = d3.zoomIdentity.translate(tx, ty).scale(scale);
    this.root.transition().duration(420).call(this.zoom.transform, t);
  }
}

async function loadOntology(domain, version) {
  setErrors('');
  setInspect(null);
  setStatus('加载中…');
  const [types, rels] = await Promise.all([
    request(`${API}/semantic/${encodeURIComponent(domain)}/${encodeURIComponent(version)}/object-types`),
    request(`${API}/semantic/${encodeURIComponent(domain)}/${encodeURIComponent(version)}/relationships`)
  ]);

  const nodes = (types || []).map(t => ({
    id: t.labelName,
    label: t.displayName || t.labelName,
    meta: t
  }));

  const links = (rels || []).map(r => ({
    id: r.labelName,
    source: r.sourceLabel,
    target: r.targetLabel,
    label: r.labelName,
    meta: r
  })).filter(l => l.source && l.target);

  setStatus(`已加载：类型 ${nodes.length}，关系 ${links.length}`);
  return { nodes, links };
}

const vis = new D3Vis(qs('graph'));

qs('loadBtn').addEventListener('click', async () => {
  try {
    const domain = (qs('domain').value || '').trim();
    const version = (qs('version').value || '').trim() || '1.0.0';
    const { nodes, links } = await loadOntology(domain, version);
    vis.setData(nodes, links);
    setTimeout(() => vis.fit(), 160);
  } catch (e) {
    setStatus('');
    setErrors(e?.message || String(e));
  }
});

qs('fitBtn').addEventListener('click', () => vis.fit());

// auto-load
qs('loadBtn').click();

