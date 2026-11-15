// Lead scoring used inside the "Score lead" Code node. Plain rules, no AI, so every score can be explained.
function scoreLead(lead) {
  let score = 0;
  const reasons = [];
  const add = (points, why) => { score += points; reasons.push(`+${points} ${why}`); };
  const msg = (lead.message || '').toLowerCase();

  if (lead.phone) add(15, 'left a phone number');
  if (lead.company) add(10, 'named a company');
  if (lead.budget === '5000+') add(30, 'budget 5000+');
  else if (lead.budget === '1000-5000') add(20, 'budget 1000-5000');
  if (['google_ads', 'referral', 'website'].includes(lead.source)) add(10, `high-intent source (${lead.source})`);
  if (/(this week|ready|start|need|asap|book)/.test(msg)) add(20, 'message shows urgency');
  if (/(just curious|send me|guide|newsletter)/.test(msg)) add(-15, 'message shows research, not buying');

  score = Math.max(0, Math.min(100, score));
  const tier = score >= 60 ? 'hot' : score >= 30 ? 'warm' : 'nurture';
  return { score, tier, reasons };
}

if (typeof module !== 'undefined') module.exports = { scoreLead };
