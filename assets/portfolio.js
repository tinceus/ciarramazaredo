/* No client documents, free-text answers, or personal data enter analytics. */
(function (root) {
  const workflowIds = ['lead-to-booked-call','weekly-report','content-routing','inbox-triage','ai-receptionist','error-alerts','trend-scoring','transcript-harvester'];
  function routeFit({process, frequency, systems, examples, actions}) {
    if (!['lead-to-booked-call','weekly-report','content-routing','inbox-triage','other'].includes(process) || !['occasional','weekly','daily'].includes(frequency) || !['supported','custom','unknown'].includes(systems) || !['yes','no'].includes(examples) || !['draft','write'].includes(actions)) return null;
    if (examples === 'no') return {route:'prepare', title:'Gather a few examples first', text:'Record the current steps, frequency, and exceptions. Sanitized examples make a paid assessment more useful.', href:'/workflows', label:'Explore examples'};
    if (systems !== 'supported' || actions === 'write' || process === 'other') return {route:'sprint', title:'Discuss a feasibility sprint', text:'The integrations or actions need a closer look. A fit call can establish whether the US$750 assessment is appropriate.', href:null, label:'Email a workflow inquiry'};
    if (frequency === 'occasional') return {route:'starter', title:'Try a free starter first', text:'A reviewed manual process may be enough at this volume. Compare the example with your actual steps before investing.', href:'/workflows#'+process, label:'Explore a starter'};
    return {route:'setup', title:'Ask about a scoped setup', text:'If the existing example fits, request a setup quote. A paid sprint is not required for clearly understood work.', href:null, label:'Request a setup quote'};
  }
  if (typeof module !== 'undefined') module.exports={routeFit};
  if (!root.document) return;
  const doc=root.document, config=root.SITE || {};
  const incoming = new URLSearchParams(root.location.search).get('workflow');
  const workflow = workflowIds.includes(incoming) ? incoming : '';
  function inquiryUrl(context,route) {
    if (config.sprintBookingUrl) {
      try {
        const url = new URL(config.sprintBookingUrl);
        if (url.protocol === 'https:') {
          if (context) url.searchParams.set('workflow',context);
          if (route) url.searchParams.set('intent',route);
          return url.href;
        }
      } catch (_) { /* Invalid configuration uses the public email fallback. */ }
    }
    const subject = 'Workflow inquiry'+(context?' - '+context:'')+(route?' - '+route:'');
    return 'mailto:ciarramazaredo@gmail.com?subject='+encodeURIComponent(subject);
  }
  function track(name,properties={}) {
    // Optional first-party adapter. No external collector is added by this script.
    if (typeof root.portfolioTrack === 'function') root.portfolioTrack(name,properties);
  }
  doc.querySelectorAll('[data-sprint-inquiry]').forEach(a=>{a.href=inquiryUrl(workflow);});
  const form=doc.getElementById('fit-form'),result=doc.getElementById('fit-result');
  if(form && result){
    const select=doc.getElementById('process');
    if([...select.options].some(o=>o.value===workflow)) select.value=workflow;
    form.addEventListener('submit',event=>{
      event.preventDefault();
      if(!form.reportValidity())return;
      const answers=Object.fromEntries(new FormData(form));
      const recommendation=routeFit(answers);
      if(!recommendation)return;
      result.replaceChildren();
      const title=doc.createElement('h3');title.textContent=recommendation.title;
      const description=doc.createElement('p');description.textContent=recommendation.text;
      const link=doc.createElement('a');link.className='btn btn-primary';link.textContent=recommendation.label;
      link.href=recommendation.href || inquiryUrl(answers.process,recommendation.route);
      if(!recommendation.href){link.dataset.sprintInquiry='';link.dataset.workflow=answers.process;}
      result.append(title,description,link);result.hidden=false;result.focus();
      track('fit_check_result',{route:recommendation.route});
    });
  }
  for(const [key,selector] of [['newsletterUrl','[data-newsletter]'],['storefrontUrl','[data-storefront]']]){
    try { const url=new URL(config[key]);if(url.protocol!=='https:')continue;
      doc.querySelectorAll(selector).forEach(a=>{a.href=url.href;a.hidden=false;});
    }catch(_){}
  }
  doc.addEventListener('click',e=>{
    const a=e.target.closest('a');if(!a)return;
    if(a.hasAttribute('data-sprint-inquiry'))track('inquiry_link_clicked',{path:root.location.pathname,workflow:workflowIds.includes(a.dataset.workflow)?a.dataset.workflow:workflow});
    if(a.hasAttribute('download'))track('workflow_download_clicked',{path:root.location.pathname});
  });
  if(root.location.pathname==='/ai-sprint')track('sprint_page_viewed');
})(typeof window !== 'undefined' ? window : globalThis);
