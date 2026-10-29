const $ = (id) => document.getElementById(id);
document.querySelectorAll('button').forEach(button => button.classList.add('font-semibold','rounded-full','transition-all','active:scale-[0.98]'));
document.querySelectorAll('.panel, .art-panel').forEach(panel => panel.classList.add('group','bg-white/10','backdrop-blur-sm','rounded-2xl','border','border-white/20'));
document.querySelectorAll('.section-index,.task-icon').forEach(icon => icon.classList.add('group-hover:scale-110'));
const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;
const tasks = {
  vowel: { name: '持续元音', instruction: '深吸一口气，以自然、平稳的音量持续发出“啊——”音，保持约 6 秒。', duration: '06–10' },
  ddk: { name: '音节重复', instruction: '以舒适的音量连续重复“啪、塔、卡”，保持清晰、均匀的节奏，持续约 7 秒。', duration: '07–10' },
  reading: { name: '短文朗读', instruction: '以自然语速朗读：“清晨的阳光穿过窗户，今天的天气晴朗，适合去公园散步。”', duration: '10–15' }
};
let selectedTask = 'vowel', running = false, importedRow = null, fileName = null, score = 0.284, history = [], toastTimer;
function randomId() {
  const alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
  let result = '';
  // Rejection sampling keeps every character equally likely.
  while (result.length < 12) { const bytes = crypto.getRandomValues(new Uint8Array(20)); for (const byte of bytes) { if (byte < 252 && result.length < 12) result += alphabet[byte % 36]; } }
  return result;
}
$('sessionId').textContent = randomId();
let composition = crypto.getRandomValues(new Uint8Array(1))[0] % 3;
function setComposition(value) {
  composition = value;
  document.body.dataset.composition = String(value);
  $('layoutLabel').textContent = `COMPOSITION 0${value + 1}`;
  requestAnimationFrame(() => { if (typeof resizeCanvases === 'function') resizeCanvases(); });
}
document.body.dataset.composition = String(composition);
$('layoutLabel').textContent = `COMPOSITION 0${composition + 1}`;
$('shuffleLayout').onclick = () => {
  const next = (composition + 1 + crypto.getRandomValues(new Uint8Array(1))[0] % 2) % 3;
  setComposition(next); toast(`已切换艺术构图 0${next + 1}`);
};
function toast(message) { $('toast').textContent = message; $('toast').classList.add('visible'); clearTimeout(toastTimer); toastTimer = setTimeout(() => $('toast').classList.remove('visible'), 4200); }
function updateClock() { const clock = $('clock'); if (clock) clock.textContent = new Intl.DateTimeFormat('en-GB', { timeZone: 'Asia/Shanghai', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false }).format(new Date()) + ' CST'; }
updateClock(); setInterval(updateClock, 1000);
$('regenerate').onclick = () => { if (running) return toast('分析中，请稍候再生成会话编号'); $('sessionId').textContent = randomId(); toast('已生成新的随机会话编号'); };
document.querySelectorAll('.task').forEach(button => button.onclick = () => {
  if (running) return;
  selectedTask = button.dataset.task;
  document.querySelectorAll('.task').forEach(b => { const active = b === button; b.classList.toggle('selected', active); b.setAttribute('aria-pressed', String(active)); b.querySelector('.task-check').textContent = active ? '✓' : '○'; });
  $('instruction').textContent = tasks[selectedTask].instruction;
  $('duration').innerHTML = tasks[selectedTask].duration + ' <small>SEC</small>';
});
document.querySelectorAll('.task').forEach(b => b.setAttribute('aria-pressed', String(b.classList.contains('selected'))));
document.querySelectorAll('.rail-button').forEach(button => button.onclick = () => {
  document.querySelectorAll('.rail-button').forEach(b => { b.classList.toggle('active', b === button); b.setAttribute('aria-current', b === button ? 'page' : 'false'); });
  ['screen', 'records', 'model'].forEach(view => $(view + 'View').hidden = view !== button.dataset.view);
  if (button.dataset.view === 'screen') requestAnimationFrame(resizeCanvases);
});
$('help').onclick = () => $('helpDialog').showModal();
$('heroAbout').onclick = () => {
  document.querySelector('[data-view="model"]').click();
  $('laboratory').scrollIntoView({behavior:reducedMotion ? 'instant' : 'smooth'});
};
document.querySelector('.hero-primary').addEventListener('click', () => document.querySelector('[data-view="screen"]').click());
$('closeHelp').onclick = () => $('helpDialog').close();
$('helpDialog').addEventListener('click', e => { if (e.target === $('helpDialog')) $('helpDialog').close(); });
const features = ['MDVP:Fo(Hz)','MDVP:Fhi(Hz)','MDVP:Flo(Hz)','MDVP:Jitter(%)','MDVP:Jitter(Abs)','MDVP:RAP','MDVP:PPQ','Jitter:DDP','MDVP:Shimmer','MDVP:Shimmer(dB)','Shimmer:APQ3','Shimmer:APQ5','MDVP:APQ','Shimmer:DDA','NHR','HNR','RPDE','DFA','spread1','spread2','D2','PPE'];
function parseCsv(text) {
  const rows = []; let row = [], value = '', quoted = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (c === '"') { if (quoted && text[i+1] === '"') { value += '"'; i++; } else quoted = !quoted; }
    else if (c === ',' && !quoted) { row.push(value); value = ''; }
    else if ((c === '\n' || c === '\r') && !quoted) { if (c === '\r' && text[i+1] === '\n') i++; row.push(value); if (row.some(v => v.trim())) rows.push(row); row = []; value = ''; }
    else value += c;
  }
  if (quoted) throw new Error('CSV 引号未闭合');
  row.push(value); if (row.some(v => v.trim())) rows.push(row);
  return rows;
}
$('csvFile').onchange = async (e) => {
  const file = e.target.files[0]; if (!file) return;
  if (running) { e.target.value = ''; return toast('请在模拟分析完成后导入文件'); }
  try {
    if (file.size > 5 * 1024 * 1024) throw new Error('请选择小于 5 MB 的 CSV 文件');
    const rows = parseCsv((await file.text()).replace(/^\uFEFF/, ''));
    if (rows.length < 2) throw new Error('文件需要包含表头和至少一条数据');
    const header = rows[0].map(v => v.trim());
    if (new Set(header).size !== header.length) throw new Error('表头含有重复列');
    const missing = features.filter(f => !header.includes(f));
    if (missing.length) throw new Error('缺少特征列：' + missing.slice(0, 3).join('、') + (missing.length > 3 ? ` 等 ${missing.length} 列` : ''));
    for (let r = 1; r < rows.length; r++) {
      if (rows[r].length !== header.length) throw new Error(`第 ${r + 1} 行列数与表头不一致`);
      for (const f of features) { const value = rows[r][header.indexOf(f)].trim(); if (!value || !Number.isFinite(Number(value))) throw new Error(`第 ${r + 1} 行 ${f} 不是有效数值`); }
    }
    importedRow = Object.fromEntries(header.map((name, i) => [name, rows[1][i]])); fileName = file.name;
    $('fileLabel').textContent = file.name; $('inputMode').textContent = `${rows.length - 1} 条特征 · 已校验`;
    $('f0Value').innerHTML = Number(importedRow['MDVP:Fo(Hz)']).toFixed(1) + ' <small>Hz</small>';
    $('jitterValue').innerHTML = (Number(importedRow['MDVP:Jitter(%)']) * 100).toFixed(2) + ' <small>%</small>';
    $('shimmerValue').innerHTML = (Number(importedRow['MDVP:Shimmer']) * 100).toFixed(2) + ' <small>%</small>';
    $('hnrValue').innerHTML = Number(importedRow.HNR).toFixed(1) + ' <small>dB</small>';
    toast(`已校验 ${rows.length - 1} 条录音，显示首条特征；分数仍为模拟输出`);
  } catch (error) { toast(error.message); } finally { e.target.value = ''; }
};
$('analyze').onclick = () => {
  if (running) return; running = true; $('analyze').disabled = true;
  $('signalState').innerHTML = '<i></i> ANALYZING'; const start = performance.now();
  $('signalNote').textContent = '模拟特征处理与分析流程，请稍候…';
  const timer = setInterval(() => {
    const elapsed = Math.min((performance.now() - start) / 1000, 6);
    $('waveTime').textContent = `00:0${Math.floor(elapsed)} / 00:06`;
    $('analyze').querySelector('span').textContent = `模拟分析中 ${Math.round(elapsed / 6 * 100)}%`;
    if (elapsed >= 6) {
      clearInterval(timer); running = false; $('analyze').disabled = false;
      $('analyze').querySelector('span').textContent = '再次模拟分析';
      $('signalState').innerHTML = '<i></i> ANALYSIS COMPLETE';
      score = [0.284, 0.418, 0.672][history.length % 3];
      $('score').textContent = score.toFixed(3); $('scoreArc').style.strokeDasharray = `${score * 100} 100`;
      const low = score < .35, high = score >= .65;
      $('resultBand').innerHTML = `<span></span><strong>${low ? '低' : high ? '高' : '中'}分数区间</strong><small>${low ? 'LOW' : high ? 'HIGH' : 'MID'} BAND</small>`;
      $('resultBand').style.color = high ? '#eab393' : low ? '#9bd0bb' : '#d4c792';
      $('signalNote').textContent = '模拟分析完成 · 输出为演示数据，未调用 Python 模型';
      const entry = { session: $('sessionId').textContent, task: tasks[selectedTask].name, demo_score: score, file: fileName, time: new Date().toISOString() };
      history.unshift(entry); renderHistory(); toast('模拟分析完成，可导出演示报告');
    }
  }, 100);
};
function renderHistory() {
  $('recordsList').replaceChildren();
  history.forEach(entry => {
    const row = document.createElement('div'); row.className = 'record-row';
    [entry.session, entry.task, `DEMO ${entry.demo_score.toFixed(3)}`, new Date(entry.time).toLocaleTimeString('zh-CN', { timeZone: 'Asia/Shanghai' })].forEach(value => { const span = document.createElement('span'); span.textContent = value; row.append(span); });
    $('recordsList').append(row);
  });
}
$('export').onclick = () => {
  const report = { application: 'NEUROVA', session: $('sessionId').textContent, type: 'frontend-demo', generated_at: new Date().toISOString(), task: tasks[selectedTask].name, demo_score: score, source_file: fileName, first_row_features: importedRow, notice: '前端演示报告；尚未连接 Python 推理。分数为模拟数据，不代表患病概率。', history };
  const url = URL.createObjectURL(new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' }));
  const a = document.createElement('a'); a.href = url; a.download = `NEUROVA-${report.session}-demo.json`; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000); toast('演示报告已导出');
};

const neural = $('neuralCanvas'), wave = $('waveCanvas');
const ctx = neural.getContext('2d'), wctx = wave.getContext('2d');
let nw = 0, nh = 0, ww = 0, wh = 0, lastPaint = 0;
function resizeCanvases() {
  const ratio = Math.min(devicePixelRatio || 1, 2);
  for (const [canvas, context] of [[neural,ctx],[wave,wctx]]) {
    const rect = canvas.getBoundingClientRect(); if (!rect.width || !rect.height) continue;
    canvas.width = Math.round(rect.width * ratio); canvas.height = Math.round(rect.height * ratio); context.setTransform(ratio,0,0,ratio,0,0);
    if (canvas === neural) { nw = rect.width; nh = rect.height; } else { ww = rect.width; wh = rect.height; }
  }
}
window.addEventListener('resize', resizeCanvases); resizeCanvases();
const points = Array.from({length:550},(_,i) => { const y = 1 - (i / 549) * 2, radius = Math.sqrt(1 - y*y), phi = i * Math.PI * (3 - Math.sqrt(5)); return {x:Math.cos(phi)*radius,y,z:Math.sin(phi)*radius}; });
function draw(time) {
  requestAnimationFrame(draw);
  if (document.hidden || $('screenView').hidden || time - lastPaint < (reducedMotion ? 250 : 33)) return;
  lastPaint = time; const t = reducedMotion ? 1.5 : time / 1000; const r = Math.min(nw * .30, nh * .34), cx = nw/2, cy = nh*.47;
  ctx.clearRect(0,0,nw,nh);
  const glow = ctx.createRadialGradient(cx,cy,5,cx,cy,r*1.5); glow.addColorStop(0,'#71d3c217');glow.addColorStop(.6,'#4dbbb40d');glow.addColorStop(1,'#7de3dc00');ctx.fillStyle=glow;ctx.fillRect(0,0,nw,nh);
  ctx.save();ctx.translate(cx,cy);ctx.strokeStyle='#5b919c44';ctx.lineWidth=.7;
  ctx.beginPath();ctx.ellipse(0,0,r*1.32,r*.40,-.38,0,Math.PI*2);ctx.stroke();
  ctx.beginPath();ctx.ellipse(0,0,r*.62,r*1.16,.48,0,Math.PI*2);ctx.stroke();
  ctx.setLineDash([2,7]);ctx.beginPath();ctx.arc(0,0,r*1.26,0,Math.PI*2);ctx.stroke();ctx.setLineDash([]);
  const rotation = t*.13, cos = Math.cos(rotation), sin = Math.sin(rotation);
  const projected = points.map((p,i) => {
    const x=p.x*cos-p.z*sin,z=p.x*sin+p.z*cos;
    const vibration = 1 + .045*Math.sin(p.y*13+t*(running?5:1.1)) + .023*Math.cos(x*14+t);
    const scale=1+z*.15;return {x:x*r*vibration*scale,y:p.y*r*vibration*scale,z,index:i};
  });
  for (let i=0;i<projected.length;i++) {
    const a=projected[i];
    for (const j of [i+1,i+21,i+34]) {
      if(j>=projected.length)continue;const b=projected[j],d=Math.hypot(a.x-b.x,a.y-b.y);
      if(d<r*.29&&Math.abs(a.z-b.z)<.4){ctx.strokeStyle=`rgba(115,218,204,${(.025+Math.max(0,a.z)*.11)*(1-d/(r*.4))})`;ctx.beginPath();ctx.moveTo(a.x,a.y);ctx.lineTo(b.x,b.y);ctx.stroke();}
    }
  }
  projected.sort((a,b)=>a.z-b.z).forEach(p=>{const alpha=.18+(p.z+1)*.32;ctx.fillStyle=`rgba(151,239,222,${alpha})`;ctx.beginPath();ctx.arc(p.x,p.y,.65+(p.z+1)*.55,0,Math.PI*2);ctx.fill();});
  // A luminous neural tract through the sphere, drawn from signal-like curves.
  for(let strand=0;strand<5;strand++){ctx.beginPath();for(let k=0;k<=110;k++){const yy=(k/110-.5)*r*1.65;const envelope=Math.sin(k/110*Math.PI);const xx=(Math.sin(k*.12+t*.6+strand*.8)*r*.27+Math.sin(k*.27+strand)*r*.09)*envelope;const px=xx+(strand-2)*5;if(k===0)ctx.moveTo(px,yy);else ctx.lineTo(px,yy);}ctx.strokeStyle=`rgba(147,239,218,${strand===2?.48:.12})`;ctx.lineWidth=strand===2?1.1:.6;ctx.stroke();}
  ctx.restore();
  wctx.clearRect(0,0,ww,wh);wctx.strokeStyle='#30505b55';wctx.lineWidth=.5;wctx.beginPath();wctx.moveTo(0,wh/2);wctx.lineTo(ww,wh/2);wctx.stroke();
  const count=Math.floor(ww/4);for(let i=0;i<count;i++){const x=i*4+2,envelope=Math.pow(Math.sin(i/count*Math.PI),.55);const mod=(Math.sin(i*1.47)*.35+.65)*(.55+.45*Math.sin(i*.13+(running?t*3:t*.25)));const height=3+envelope*mod*wh*.8;wctx.fillStyle=i<count*.62?'#82d9c9':'#426f78';wctx.fillRect(x,(wh-height)/2,1.8,height);}
  $('frameCount').textContent='Φ '+((t*.037)%1).toFixed(3);
}
requestAnimationFrame(draw);
