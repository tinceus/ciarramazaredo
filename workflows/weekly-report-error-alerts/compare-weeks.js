/* Pure calculation. n8n wrapper is added by tools/build_workflows.py. */
function compareWeeks(rows) {
  if (!Array.isArray(rows) || !rows.length) throw new Error('No KPI rows supplied');
  const numeric = (value, field) => {
    if ((typeof value !== 'number' && typeof value !== 'string') || String(value).trim() === '' || !Number.isFinite(Number(value))) {
      throw new Error(`Invalid numeric ${field}`);
    }
    return Number(value);
  };
  const keys = new Set();
  for (const row of rows) {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(row.week_start || '') || !Number.isFinite(Date.parse(row.week_start)) || new Date(row.week_start).toISOString().slice(0, 10) !== row.week_start) throw new Error('Invalid week_start; use YYYY-MM-DD');
    if (typeof row.metric !== 'string' || !row.metric.trim()) throw new Error('Missing metric name');
    const key = JSON.stringify([row.week_start, row.metric]);
    if (keys.has(key)) throw new Error(`Duplicate KPI row: ${row.metric} ${row.week_start}`);
    keys.add(key);
    numeric(row.value, `${row.metric} value`);
    numeric(row.target, `${row.metric} target`);
    if (!['up', 'down'].includes(row.direction)) throw new Error(`Invalid direction: ${row.metric}`);
  }
  const weeks = [...new Set(rows.map(r => r.week_start))].sort();
  const current = weeks.at(-1), previous = weeks.at(-2) || null;
  const lookup = (week, metric) => rows.find(r => r.week_start === week && r.metric === metric);
  const metrics = [...new Set(rows.filter(r => [current, previous].includes(r.week_start)).map(r => r.metric))].map(metric => {
    const a = lookup(current, metric), b = lookup(previous, metric);
    const prior = b ? Number(b.value) : null;
    if (!a) return {metric, value: null, target: null, previous: prior, change: null, status: 'Missing current data'};
    const value = Number(a.value), target = Number(a.target);
    const good = a.direction === 'down' ? value <= target : value >= target;
    return {metric, value, target, previous: prior, change: prior === null ? null : Number((value - prior).toFixed(2)), status: good ? 'On track' : 'Watch'};
  });
  const show = value => value === null ? 'not available' : value;
  return {week: current, previousWeek: previous, metrics,
    table: metrics.map(m => `${m.metric}: ${show(m.value)} (target ${show(m.target)}, previous available week ${show(m.previous)}) ${m.status}`).join('\n')};
}
if (typeof module !== 'undefined') module.exports = {compareWeeks};
