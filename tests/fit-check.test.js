const {test}=require('node:test');
const assert=require('node:assert/strict');
const {routeFit}=require('../assets/portfolio');
const baseline={process:'weekly-report',frequency:'daily',systems:'supported',examples:'yes',actions:'draft'};
test('known setup does not force paid discovery',()=>assert.equal(routeFit(baseline).route,'setup'));
test('occasional draft work can start free',()=>assert.equal(routeFit({...baseline,frequency:'occasional'}).route,'starter'));
test('consequential writes or unknown integrations need discussion',()=>{
  assert.equal(routeFit({...baseline,actions:'write'}).route,'sprint');
  assert.equal(routeFit({...baseline,systems:'unknown'}).route,'sprint');
});
test('missing evidence prompts preparation rather than a premature sale',()=>assert.equal(routeFit({...baseline,examples:'no'}).route,'prepare'));
test('invalid input is not treated as a qualified lead',()=>assert.equal(routeFit({...baseline,process:'<script>'}),null));
