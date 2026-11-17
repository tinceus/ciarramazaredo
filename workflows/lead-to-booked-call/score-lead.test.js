// Run: node workflows/lead-to-booked-call/score-lead.test.js
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const { scoreLead } = require('./score-lead');

const rows = fs.readFileSync(path.join(__dirname, 'sample-data/leads.csv'), 'utf8').trim().split('\n');
const head = rows.shift().split(',');
const leads = rows.map(r => Object.fromEntries(r.split(',').map((v, i) => [head[i], v])));
const byName = Object.fromEntries(leads.map(l => [l.name, scoreLead(l)]));

assert.strictEqual(byName['Dana Reyes'].tier, 'hot');
assert.strictEqual(byName['Kim Novak'].tier, 'hot');
assert.strictEqual(byName['Lee Ortiz'].tier, 'hot');
assert.strictEqual(byName['Sam Patel'].tier, 'nurture');
assert.strictEqual(byName['Ali Hassan'].tier, 'nurture');
assert.ok(byName['Dana Reyes'].reasons.length >= 3, 'every score explains itself');
assert.deepStrictEqual(scoreLead({}), { score: 0, tier: 'nurture', reasons: [] });


// Property example (fictional rental inquiries): same rules, expected tiers pinned.
const prows = fs.readFileSync(path.join(__dirname, 'sample-data/property-inquiries.csv'), 'utf8').trim().split('\n');
const phead = prows.shift().split(',');
const prop = Object.fromEntries(prows.map(r => Object.fromEntries(r.split(',').map((v, i) => [phead[i], v]))).map(l => [l.name, scoreLead(l)]));
assert.strictEqual(prop['Maya Torres'].tier, 'hot');
assert.strictEqual(prop['Leo Grant'].tier, 'hot');
assert.strictEqual(prop['Jon Bell'].tier, 'warm');
assert.strictEqual(prop['Priya Shah'].tier, 'nurture');
assert.strictEqual(prop['Ana Cruz'].tier, 'nurture');
for (const [n, r] of Object.entries(byName)) console.log(n.padEnd(12), String(r.score).padStart(3), r.tier);
console.log('score-lead: PASS');
