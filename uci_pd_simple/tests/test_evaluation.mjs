import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
class Element {
  constructor(tag='div'){this.tag=tag;this.children=[];this.attrs={};this.style={};this.textContent='';}
  append(...nodes){this.children.push(...nodes);}
  replaceChildren(...nodes){this.children=nodes;}
  setAttribute(k,v){this.attrs[k]=v;}
  addEventListener(_,fn){this.listener=fn;}
  click(){this.onclick?.();}
}
const ids=new Map();
const get=id=>{if(!ids.has(id))ids.set(id,new Element());return ids.get(id);};
const nav=new Element();
const model=JSON.parse(fs.readFileSync(new URL('../artifacts/audio_transformer_v1/model_card.json',import.meta.url)));
const raw=JSON.parse(fs.readFileSync(new URL('../artifacts/audio_transformer_v1/integration_hc.json',import.meta.url)));
const prediction=typeof raw.prediction==='object' ? raw.prediction : raw;
assert.equal(typeof prediction.model_score,'number');
const data={metrics:model.evaluation.metrics,threshold:.5,dataset:model.dataset,roc:[{fpr:0,tpr:0},{fpr:1,tpr:1}],notice:'OOF test fixture'};
const sandbox={document:{getElementById:get,createElement:t=>new Element(t),createElementNS:(_,t)=>new Element(t),querySelector:()=>nav},window:{print(){},neuroCapture:{lastPrediction:prediction,clip:{session:'TESTSESSION1'}}},fetch:async()=>({ok:true,json:async()=>data}),console};
vm.runInNewContext(fs.readFileSync(new URL('../frontend/evaluation.js',import.meta.url),'utf8'),sandbox);
await new Promise(resolve=>setImmediate(resolve));
const texts=n=>[n.textContent,...n.children.flatMap(texts)].join(' ');
assert.match(texts(get('evaluationMetrics')),/37/);
assert.match(texts(get('confusionChart')),/漏报6人/);
assert.equal(get('rocChart').children[0].tag,'svg');
nav.listener();assert.match(texts(get('recordingVisual')),/更接近健康对照组/);
get('reportFile').files=[{name:'report.json',size:100,text:async()=>JSON.stringify({session:'TESTSESSION1',prediction})}];
await get('reportFile').onchange({target:get('reportFile')});
assert.match(texts(get('rocChart')),/不绘制或猜测/);
assert.match(texts(get('evaluationStatus')),/已导入/);
get('reportFile').files=[{name:'bad.json',size:100,text:async()=>'{bad'}];
await get('reportFile').onchange({target:get('reportFile')});
assert.match(texts(get('evaluationStatus')),/导入失败/);
console.log('Evaluation rendering, JSON import, missing ROC and invalid report checks passed.');
