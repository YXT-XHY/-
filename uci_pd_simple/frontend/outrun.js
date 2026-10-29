const $ = id => document.getElementById(id);
const reduced=matchMedia('(prefers-reduced-motion: reduce)').matches;
const signalTheme=getComputedStyle(document.documentElement);
const signalStart=signalTheme.getPropertyValue('--signal-start').trim()||'#6d5dfc';
const signalEnd=signalTheme.getPropertyValue('--signal-end').trim()||'#279c98';
const englishReading='On a clear morning, a traveler walks along a quiet road. The wind moves through the trees, and the sunlight warms the fields. Please keep speaking in your usual voice and read these sentences at a comfortable pace.';
const taskInfo={
 vowel:{name:'持续元音',duration:'6–10 秒',instruction:'平稳发出“啊——”，持续约 6 秒。'},
 ddk:{name:'音节重复',duration:'7–10 秒',instruction:'均匀重复“啪、塔、卡”，持续约 7 秒。'},
 reading:{name:'短文朗读',duration:'15–25 秒',instruction:englishReading}
};
let selected='reading',running=false,records=[],toastTimer,composition=0,importedRow=null,fileName=null;
function randomId(){const alphabet='ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';let value='';while(value.length<12)for(const byte of crypto.getRandomValues(new Uint8Array(20)))if(byte<252&&value.length<12)value+=alphabet[byte%36];return /[A-Z]/.test(value)&&/\d/.test(value)?value:randomId();}
$('sessionId').textContent=randomId();
function toast(message){$('toast').textContent=message;$('toast').classList.add('visible');clearTimeout(toastTimer);toastTimer=setTimeout(()=>$('toast').classList.remove('visible'),4500);}
function updateInstruction(){taskInfo.reading.instruction=$('audioLanguage').value==='en'?englishReading:'清晨的阳光穿过窗户。今天的天气晴朗，微风吹动树叶。我用平常的声音和自然的语速，清晰地读完这段文字。';$('instruction').textContent=taskInfo[selected].instruction;$('duration').textContent=taskInfo[selected].duration;}
$('audioLanguage').onchange=updateInstruction;updateInstruction();
document.querySelectorAll('.nav-button').forEach(button=>button.onclick=()=>{document.querySelectorAll('.nav-button').forEach(b=>b.classList.toggle('current',b===button));['lab','records','model','evaluation'].forEach(view=>$(view+'View').hidden=view!==button.dataset.view);if(button.dataset.view==='lab')requestAnimationFrame(resizeWave);});
document.querySelectorAll('.task').forEach(button=>button.onclick=()=>{if(running||window.neuroCapture?.busy)return;selected=button.dataset.task;document.querySelectorAll('.task').forEach(b=>{const active=b===button;b.classList.toggle('selected',active);b.setAttribute('aria-pressed',String(active));b.querySelector('.task-radio').textContent=active?'●':'○';});updateInstruction();});
$('regenerate').onclick=()=>{if(running||window.neuroCapture?.busy)return;$('sessionId').textContent=randomId();toast('已生成新的会话编号');};
$('shuffle').onclick=()=>{composition=(composition+1+crypto.getRandomValues(new Uint8Array(1))[0]%2)%3;$('deck').dataset.composition=String(composition);requestAnimationFrame(resizeWave);};
$('help').onclick=()=>$('helpDialog').showModal();$('closeHelp').onclick=()=>$('helpDialog').close();
function renderRecords(){$('recordsList').replaceChildren();for(const entry of records){const row=document.createElement('div');row.className='record-row';for(const value of [entry.session,entry.label,entry.score.toFixed(3),new Date(entry.time).toLocaleTimeString('zh-CN')]){const span=document.createElement('span');span.textContent=value;row.append(span);}$('recordsList').append(row);}$('recordCount').textContent=String(records.length+(window.neuroCapture?.savedCount||0)).padStart(2,'0');}
$('export').onclick=()=>{const capture=window.neuroCapture;if(!capture?.lastPrediction)return toast('请先完成真实模型分析');const report={application:'NEURODRIVE',session:capture.clip?.session,prediction:capture.lastPrediction,created_at:new Date().toISOString(),notice:'研究模型输出，不构成临床诊断。'};const url=URL.createObjectURL(new Blob([JSON.stringify(report,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='NEURODRIVE-'+report.session+'-analysis.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
const canvas=$('waveCanvas'),context=canvas.getContext('2d');let width=0,height=0,lastPaint=0;
function resizeWave(){const rect=canvas.getBoundingClientRect();if(!rect.width||!rect.height)return;const ratio=Math.min(devicePixelRatio||1,2);width=rect.width;height=rect.height;canvas.width=Math.round(width*ratio);canvas.height=Math.round(height*ratio);context.setTransform(ratio,0,0,ratio,0,0);}
new ResizeObserver(resizeWave).observe(canvas);resizeWave();
function draw(time){requestAnimationFrame(draw);if(document.hidden||$('labView').hidden||time-lastPaint<(reduced?300:33))return;lastPaint=time;context.clearRect(0,0,width,height);const gradient=context.createLinearGradient(0,0,width,0);gradient.addColorStop(0,signalStart);gradient.addColorStop(1,signalEnd);context.fillStyle=gradient;context.strokeStyle=gradient;context.lineWidth=1.5;
const capture=window.neuroCapture;
if(capture?.analyser){const samples=new Float32Array(capture.analyser.fftSize);capture.analyser.getFloatTimeDomainData(samples);context.beginPath();for(let i=0;i<samples.length;i++){const x=i/(samples.length-1)*width,y=height/2-samples[i]*height*.48;if(i===0)context.moveTo(x,y);else context.lineTo(x,y);}context.stroke();return;}
if(capture?.waveform){const data=capture.waveform,bins=Math.max(1,Math.floor(width/3));for(let i=0;i<bins;i++){const at=Math.min(1023,Math.floor(i/bins*1024))*2,low=data[at],high=data[at+1];context.fillRect(i*3,(1-high)*height/2,1.5,Math.max(1,(high-low)*height/2));}return;}
context.globalAlpha=.25;context.beginPath();context.moveTo(0,height/2);context.lineTo(width,height/2);context.stroke();context.globalAlpha=1;}
requestAnimationFrame(draw);
$('scoreArc').style.strokeDasharray='0 100';
$('waveLabel').textContent='等待语音';
