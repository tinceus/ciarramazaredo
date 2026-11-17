/* AI Sprint fit check. Loaded on /ai-sprint only. Answers stay in the browser: nothing is sent or stored.
   Route logic from the Codex draft (routeFit), with its tracking and storefront code removed. */
(function (root) {
  const workflowIds = ['lead-to-booked-call', 'weekly-report', 'content-routing', 'inbox-triage', 'ai-receptionist', 'error-alerts', 'trend-scoring', 'transcript-harvester'];
  const names = {
    'lead-to-booked-call': 'lead to booked call', 'weekly-report': 'weekly report', 'content-routing': 'approved copy into the calendar',
    'inbox-triage': 'inbox triage', 'ai-receptionist': 'AI receptionist', 'error-alerts': 'error alerts',
    'trend-scoring': 'trend scoring', 'transcript-harvester': 'transcript harvester', 'other': 'another process'
  };
  function routeFit({process, frequency, systems, examples, actions}) {
    if (![...workflowIds, 'other'].includes(process) || !['occasional', 'weekly', 'daily'].includes(frequency) ||
        !['supported', 'custom', 'unknown'].includes(systems) || !['yes', 'no'].includes(examples) || !['draft', 'write'].includes(actions)) return null;
    if (examples === 'no') return {route: 'prepare', title: 'Gather a few examples first', text: 'Write down the steps, how often they happen and the exceptions. A few cleaned-up examples make the Sprint far more useful.', href: '/workflows', label: 'Look at the free workflows'};
    if (systems !== 'supported' || actions === 'write' || process === 'other') return {route: 'sprint', title: 'Book a fit call about the Sprint', text: 'The tools or the actions need a closer look. A free 15-minute fit call shows whether the Sprint is the right step.', href: null, label: 'Book a free 15-minute fit call'};
    if (frequency === 'occasional') return {route: 'starter', title: 'Try a free workflow first', text: 'At this volume, a checked manual process may be enough. Compare the free example with your real steps first.', href: '/workflows#' + process, label: 'Open the free workflow'};
    return {route: 'setup', title: 'Ask about setting it up', text: 'If the free example fits your work, I can quote the setup. You do not need the Sprint for work that is already clear.', href: null, label: 'Email me about setting it up'};
  }
  if (typeof module !== 'undefined') module.exports = {routeFit};
  if (!root.document) return;
  const doc = root.document, config = root.SITE || {};
  const incoming = new URLSearchParams(root.location.search).get('workflow');
  const workflow = workflowIds.includes(incoming) ? incoming : '';
  // Each link names its source in the email subject, so inquiries can be counted by source.
  function inquiryUrl(context, route) {
    if (config.sprintBookingUrl) {
      try {
        const url = new URL(config.sprintBookingUrl);
        if (url.protocol === 'https:') {
          if (context) url.searchParams.set('workflow', context);
          if (route) url.searchParams.set('intent', route);
          return url.href;
        }
      } catch (_) { /* an invalid booking link falls back to email */ }
    }
    const from = !context ? '' : context === 'other' ? ': another process' : ': from the ' + (names[context] || context) + ' workflow';
    const subject = 'AI Sprint' + from + (route ? ' (' + route + ')' : '');
    return 'mailto:ciarramazaredo@gmail.com?subject=' + encodeURIComponent(subject);
  }
  doc.querySelectorAll('[data-sprint-inquiry]').forEach(a => { a.href = inquiryUrl(workflow); });
  const form = doc.getElementById('fit-form'), result = doc.getElementById('fit-result');
  if (form && result) {
    form.hidden = false;
    const select = doc.getElementById('process');
    if ([...select.options].some(o => o.value === workflow)) select.value = workflow;
    form.addEventListener('submit', event => {
      event.preventDefault();
      if (!form.reportValidity()) return;
      const answers = Object.fromEntries(new FormData(form));
      const rec = routeFit(answers);
      if (!rec) return;
      result.replaceChildren();
      const title = doc.createElement('h3'); title.textContent = rec.title;
      const text = doc.createElement('p'); text.textContent = rec.text;
      const link = doc.createElement('a'); link.className = 'btn btn-primary'; link.textContent = rec.label;
      link.href = rec.href || inquiryUrl(answers.process, rec.route);
      result.append(title, text, link); result.hidden = false; result.focus();
    });
  }
})(typeof window !== 'undefined' ? window : globalThis);
