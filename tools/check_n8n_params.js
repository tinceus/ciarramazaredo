// Headless n8n parameter check: runs n8n's own validator on every node of the given workflow files.
// Usage: N8N_MODULES=/path/to/n8n/node_modules node tools/check_n8n_params.js workflows/*/*.json
// Expected: only blank Document/Calendar pickers, which the buyer fills after import.
const path = require('path');
const NM = process.env.N8N_MODULES || path.join(__dirname, 'node_modules'); // folder holding n8n-workflow and n8n-nodes-base
const { NodeHelpers } = require(path.join(NM, 'n8n-workflow'));

const pkgs = [['n8n-nodes-base', 'n8n-nodes-base'], ['@n8n/n8n-nodes-langchain', '@n8n/n8n-nodes-langchain']];
const index = {};
for (const [prefix, dir] of pkgs) {
  const root = path.join(NM, dir);
  for (const f of require(path.join(root, 'package.json')).n8n.nodes) {
    const name = path.basename(f, '.node.js');
    index[`${prefix}.${name[0].toLowerCase()}${name.slice(1)}`] = path.join(root, f);
  }
}

function describe(type, version) {
  let t = type, tool = false;
  if (!index[t] && t.endsWith('Tool')) { t = t.slice(0, -4); tool = true; }
  const file = index[t];
  if (!file) return null;
  const mod = require(file);
  const Cls = Object.values(mod).find(v => typeof v === 'function');
  const inst = new Cls();
  const d = inst.nodeVersions ? (inst.nodeVersions[version] || inst.getNodeType(version)).description : inst.description;
  return { d, tool };
}

let total = 0;
for (const file of process.argv.slice(2)) {
  const wf = require(path.resolve(file));
  for (const node of wf.nodes) {
    if (node.type === 'n8n-nodes-base.stickyNote') continue;
    const r = describe(node.type, node.typeVersion);
    if (!r) { console.log(`${file} :: ${node.name}: UNKNOWN TYPE ${node.type}`); total++; continue; }
    const props = r.d.properties;
    const full = NodeHelpers.getNodeParameters(props, node.parameters, true, false, node, r.d) || {};
    const issues = NodeHelpers.getNodeParametersIssues(props, { ...node, parameters: full }, r.d);
    const msgs = [];
    if (issues && issues.parameters) for (const [k, v] of Object.entries(issues.parameters)) msgs.push(`issue ${k}: ${v.join('; ')}`);
    const skip = new Set([...(r.tool ? ['toolDescription', 'descriptionType'] : []), ...(r.d.polling ? ['pollTimes'] : [])]); // n8n injects pollTimes into polling triggers
    const dropped = (obj, keep, pre) => {
      for (const k of Object.keys(obj)) {
        if (skip.has(k)) continue;
        if (!(k in keep)) { msgs.push(`ignored param ${pre}${k}`); continue; }
        const v = obj[k], w = keep[k];
        if (v && typeof v === 'object' && !Array.isArray(v) && !v.__rl && w && typeof w === 'object' && !Array.isArray(w)) dropped(v, w, `${pre}${k}.`);
      }
    };
    dropped(node.parameters, full, '');
    if (msgs.length) { total += msgs.length; console.log(`${path.basename(path.dirname(file))}/${path.basename(file)} :: ${node.name}\n   - ${msgs.join('\n   - ')}`); }
  }
}
console.log(total ? `\n${total} finding(s)` : 'params: PASS');
