"""Embed the evidence manifest into static cards; retains no-JavaScript access."""
import json,re,html
from pathlib import Path
root=Path(__file__).resolve().parents[1]
p=root/'workflows.html';s=p.read_text();records=json.loads((root/'assets/workflow-evidence.json').read_text());it=iter(records)
def update(m):
 card=m[0];r=next(it)
 card=re.sub(r' data-workflow="[^"]*"','',card)
 card=card.replace('<article class="card"',f'<article id="{r["id"]}" class="card" data-workflow="{r["id"]}"') if ' id=' not in card.split('>')[0] else card.replace('class="card"',f'class="card" data-workflow="{r["id"]}"',1)
 card=re.sub(r'<span class="label">.*?</span>',f'<span class="label">{r["status"]}</span>',card,count=1)
 card=re.sub(r'<!-- proof:start -->.*?<!-- proof:end -->','',card,flags=re.S)
 proof='<div class="proof-detail"><p><strong>Checked '+r['last_checked']+':</strong> '+html.escape(r['tested_scope'])+'</p><p><strong>Setup:</strong> '+html.escape(r['prerequisites'])+'</p><p><strong>Limits:</strong> '+html.escape(r['limitations'])+'</p><p>'+html.escape(r['costs'])+'</p><a href="https://github.com/tinceus/ciarramazaredo/tree/main/'+r['source']+'">Versions, sample inputs and setup notes</a></div><a class="btn" href="/ai-sprint?workflow='+r['id']+'#fit-check">Adapt this to my business</a>'
 return card.replace('</article>','<!-- proof:start -->'+proof+'<!-- proof:end --></article>')
s=re.sub(r'<article\b[^>]*class="card".*?</article>',update,s,flags=re.S)
p.write_text(s)
