(() => {
  const el = id => document.getElementById(id);
  let baseline = null, shownPrediction = null;
  const finite = n => typeof n === 'number' && Number.isFinite(n);
  const node = (tag, text, cls) => { const n = document.createElement(tag); if (text != null) n.textContent = text; if (cls) n.className = cls; return n; };
  function svgNode(tag, attrs, text) { const n = document.createElementNS('http://www.w3.org/2000/svg', tag); for (const [k,v] of Object.entries(attrs)) n.setAttribute(k,String(v)); if(text != null)n.textContent=text; return n; }
  function svg(title) { const s=svgNode('svg',{viewBox:'0 0 420 320',role:'img','aria-label':title}); s.append(svgNode('title',{},title)); return s; }
  function validateMetrics(m) {
    if (!m || !['tp','tn','fp','fn','subjects'].every(k => Number.isInteger(m[k]) && m[k]>=0) || !m.subjects || m.tp+m.tn+m.fp+m.fn!==m.subjects) throw Error('报告中的人数或混淆矩阵无效');
    if (!['auc','accuracy','sensitivity','specificity','balanced_accuracy'].every(k=>finite(m[k])&&m[k]>=0&&m[k]<=1))throw Error('报告中的评估指标无效');
    return m;
  }
  function renderEvaluation(data) {
    const m=validateMetrics(data.metrics), cards=el('evaluationMetrics'); cards.replaceChildren();
    el('evaluationProtocol').textContent='受试者级 OOF · '+(finite(data.threshold)?'固定阈值 '+data.threshold:'阈值请参阅原模型档案');
    [[m.subjects,'受试者'],[m.auc.toFixed(3),'AUROC'],[(m.accuracy*100).toFixed(1)+'%','准确率'],[(m.sensitivity*100).toFixed(1)+'%','灵敏度'],[(m.specificity*100).toFixed(1)+'%','特异度']].forEach(([v,label])=>{const c=node('div',null,'eval-stat');c.append(node('strong',v),node('span',label));cards.append(c);});
    const cm=svg(`混淆矩阵：健康正确${m.tn}人，误报${m.fp}人，漏报${m.fn}人，患者正确${m.tp}人`);
    const text=(x,y,t,size=13,fill='#dfd4ee')=>svgNode('text',{x,y,'text-anchor':'middle',fill,'font-size':size},t);
    cm.append(text(181,30,'预测健康对照'),text(315,30,'预测帕金森组'),text(51,112,'真实健康'),text(51,238,'真实 PD'));
    [[116,50,m.tn,'正确健康',true],[250,50,m.fp,'误报',false],[116,178,m.fn,'漏报',false],[250,178,m.tp,'正确患者',true]].forEach(([x,y,count,label,ok])=>{cm.append(svgNode('rect',{x,y,width:124,height:116,rx:14,fill:ok?'#063e4c':'#4c163a',stroke:ok?'#00d4ff':'#ff5caa'}),text(x+62,y+53,count,36,'#ffffff'),text(x+62,y+83,label));});el('confusionChart').replaceChildren(cm);
    const target=el('rocChart');target.replaceChildren();
    if (data.roc?.length>1) {
      const chart=svg('ROC曲线：横轴假阳性率，纵轴真阳性率');
      for(let i=0;i<=4;i++){const f=i/4,x=60+f*315,y=266-f*220;chart.append(svgNode('path',{d:`M${x} 46V266 M60 ${y}H375`,stroke:'#60476c','stroke-width':.6}),text(x,287,f.toFixed(2),11),text(36,y+4,f.toFixed(2),11));}
      chart.append(svgNode('path',{d:'M60 266L375 46',stroke:'#977f9f','stroke-dasharray':'5 5',fill:'none'}));
      chart.append(svgNode('polyline',{points:data.roc.map(p=>`${60+p.fpr*315},${266-p.tpr*220}`).join(' '),fill:'none',stroke:'#00e5ff','stroke-width':3}));
      chart.append(svgNode('circle',{cx:60+(1-m.specificity)*315,cy:266-m.sensitivity*220,r:5,fill:'#ff5caa'}),text(218,315,'假阳性率（1 − 特异度）'),text(65,25,'真阳性率 / 灵敏度',12));target.append(chart);
    } else target.append(node('p','导入报告只有汇总指标，没有逐人留出分数，因此不绘制或猜测 ROC 曲线。','eval-notice'));
    let notice=data.notice||'模型整体评估，不是本次录音准确率。';
    if(data.auc_bootstrap_95?.length===2)notice+=` AUC 95% 区间：${data.auc_bootstrap_95.map(n=>Number(n).toFixed(3)).join('–')}。`;
    notice+=' PD / HC 病例对照小样本；无独立中文验证，不能用于确诊或排除疾病。';el('evaluationNotice').textContent=notice;
  }
  function renderRecording(p, session) {
    if(!p || !finite(p.model_score) || p.model_score<0 || p.model_score>1 || !['hc_like','pd_like','uncertain'].includes(p.prediction))throw Error('缺少有效的语音分析结果，请导入原始 JSON 报告');
    const target=el('recordingVisual');target.replaceChildren();
    const labels={hc_like:'更接近健康对照组',pd_like:'更接近帕金森病组',uncertain:'无法明确归组'};
    target.append(node('strong',labels[p.prediction],'eval-result'),node('p',`${session?'会话 '+session+' · ':''}${p.task==='reading'?'朗读':p.task} · 声明语种 ${p.language} · 模型分数 ${p.model_score.toFixed(3)}`));
    const track=node('div',null,'eval-score-track'),dot=node('span');dot.style.left=(p.model_score*100)+'%';track.append(dot);target.append(track);
    const axis=node('div',null,'eval-score-axis');axis.append(node('span','0 · 偏健康对照'),node('span','1 · 偏帕金森组'));target.append(axis);
    if(Array.isArray(p.model_scores)&&p.model_scores.length<=20)p.model_scores.forEach((score,i)=>{if(!finite(score)||score<0||score>1)return;const row=node('div',null,'eval-fold'),bar=node('div',null,'eval-fold-track'),fill=node('i');fill.style.width=(score*100)+'%';bar.append(fill);row.append(node('span',`模型 ${i+1}`),bar,node('b',score.toFixed(3)));target.append(row);});
    target.append(node('p',`基础质量：${p.quality?.quality==='pass'?'通过':'需检查'} · ${p.quality?.duration_seconds??'—'} 秒。分数不是患病概率；${p.uncertain?'已触发':'未触发'}不确定条件。`,'eval-notice'));
  }
  async function load() {
    try {const response=await fetch('/api/evaluation');const data=await response.json();if(!response.ok)throw Error(data.error||'读取评估失败');baseline=data;renderEvaluation(data);el('evaluationStatus').textContent='来源：真实受试者留出预测 · '+data.dataset.join(' / ');}
    catch(e){el('evaluationStatus').textContent=e.message+'；可导入已有 JSON 报告查看汇总指标。';}
  }
  document.querySelector('[data-view="evaluation"]').addEventListener('click',()=>{const p=window.neuroCapture?.lastPrediction;if(p&&p!==shownPrediction){shownPrediction=p;renderRecording(p,window.neuroCapture.clip?.session);if(baseline)renderEvaluation(baseline);}});
  el('importReport').onclick=()=>el('reportFile').click();
  el('reportFile').onchange=async event=>{
    const file=event.target.files[0];if(!file)return;
    try{if(file.size>1024*1024)throw Error('JSON 报告不能超过 1 MB');const report=JSON.parse(await file.text()),p=report.prediction;validateMetrics(p?.evaluation?.metrics);
      if(!p||!finite(p.model_score)||!['hc_like','pd_like','uncertain'].includes(p.prediction)||p.model_score<0||p.model_score>1)throw Error('不是有效的 NEURODRIVE 分析报告');
      renderRecording(p,report.session);renderEvaluation({...p.evaluation,notice:'来源：导入报告中的模型评估；不是本次录音准确率。'});el('evaluationStatus').textContent='已导入 '+file.name+' · 汇总评估来自该报告';
    }catch(e){el('evaluationStatus').textContent='导入失败：'+e.message;}finally{event.target.value='';}
  };
  el('printEvaluation').onclick=()=>window.print();
  load();
})();
