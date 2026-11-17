const assert = require('node:assert/strict');
const {test} = require('node:test');
const {compareWeeks} = require('./compare-weeks');
const {normalizeError} = require('./normalize-error');
const row = (week, metric = 'Leads', value = 10, target = 12, direction = 'up') => ({week_start: week, metric, value, target, direction});
test('single week preserves current values without inventing previous data', () => {
  const r = compareWeeks([row('2026-11-09')]);
  assert.equal(r.week, '2026-11-09'); assert.equal(r.metrics[0].previous, null); assert.equal(r.metrics[0].change, null);
});
test('two weeks calculate change and respect lower-is-better metrics', () => {
  const r = compareWeeks([row('2026-11-02','Response',4,2,'down'), row('2026-11-09','Response',1,2,'down')]);
  assert.equal(r.metrics[0].change,-3); assert.equal(r.metrics[0].status,'On track');
});
test('missing current metric is surfaced without a fabricated zero', () => {
  const r = compareWeeks([row('2026-11-02','A'),row('2026-11-09','B')]);
  assert.equal(r.metrics[0].status,'Missing current data'); assert.equal(r.metrics[0].value,null);
});
test('blank, invalid and infinite numbers fail before AI summary', () => {
  for (const value of ['', 'oops', Infinity, null, false]) assert.throws(()=>compareWeeks([row('2026-11-09','A',value)]),/Invalid numeric/);
});
test('empty input, duplicate records and invalid dates fail visibly', () => {
  assert.throws(()=>compareWeeks([]),/No KPI/);
  assert.throws(()=>compareWeeks([row('2026-11-09'),row('2026-11-09')]),/Duplicate/);
  assert.throws(()=>compareWeeks([row('2026-02-30')]),/Invalid week/);
});
test('nonconsecutive weeks are described accurately', () => {
  const r=compareWeeks([row('2026-10-01'),row('2026-11-09')]);
  assert.equal(r.previousWeek,'2026-10-01'); assert.match(r.table,/previous available week/);
});
test('execution and trigger failures normalize without optional fields', () => {
  assert.equal(normalizeError({execution:{error:{message:'Expired'},url:'https://example.com/run'}}).message,'Expired');
  const r=normalizeError({trigger:{error:{message:'Trigger failed',node:{name:'Webhook'}}}});
  assert.equal(r.step,'Webhook'); assert.equal(r.message,'Trigger failed'); assert.match(r.url,/No execution/);
  assert.equal(normalizeError({}).workflow,'Unknown workflow');
});
test('property owner report sample (fictional) gives the expected statuses', () => {
  const fs = require('node:fs'), path = require('node:path');
  const lines = fs.readFileSync(path.join(__dirname, 'sample-data/owner-report.csv'), 'utf8').trim().split('\n');
  const head = lines.shift().split(',');
  const rows = lines.map(l => Object.fromEntries(l.split(',').map((v, i) => [head[i], v])));
  const r = compareWeeks(rows);
  const status = Object.fromEntries(r.metrics.map(m => [m.metric, m.status]));
  assert.deepEqual(status, {'Occupancy (%)': 'On track', 'Rent collected (%)': 'Watch', 'Open work orders': 'Watch', 'Days to fill a vacancy': 'On track'});
  assert.equal(r.metrics.find(m => m.metric === 'Open work orders').change, -7);
});
