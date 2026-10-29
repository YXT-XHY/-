/* Raw voice capture is deliberately separated from the UCI feature-table model. */
(() => {
  const el = id => document.getElementById(id);
  const state = {busy:false, recording:false, clip:null, analyser:null, samples:null, waveform:null, savedCount:0, modelInfo:null, lastPrediction:null};
  window.neuroCapture = state;
  let audioContext, stream, sourceNode, worklet, muteNode, chunks=[], sampleCount=0;
  let recordTimer, startedAt=0, stoppedAck, previewUrl, saving=false;
  const maxSeconds=30;
  const tasks={vowel:'持续元音',ddk:'音节重复',reading:'短文朗读'};

  function lock(locked) {
    state.busy=locked;
    document.querySelectorAll('.task').forEach(button=>button.disabled=locked||Boolean(state.clip));
    el('regenerate').disabled=locked;
    el('importAudio').disabled=locked;
    el('audioLanguage').disabled=locked||Boolean(state.clip);
    el('clearAudio').disabled=locked;
    el('recordConsent').disabled=locked;
    el('saveAudio').disabled=locked||Boolean(state.clip?.savedId);
    el('recordAudio').disabled=locked&&!state.recording;
    el('analyze').disabled=locked||!state.clip||!state.modelInfo?.ready;
    el('analyze').firstElementChild.textContent=locked?'处理中…':!state.clip?'请先采集语音':!state.modelInfo?.ready?'模型尚未就绪':'Transformer 分析';
  }
  function status(text) { el('captureStatus').textContent=text; }
  function consent() {
    if (!el('recordConsent').checked) throw new Error('请先确认受试者同意');
  }
  function wavBlob(samples, sampleRate) {
    const buffer=new ArrayBuffer(44+samples.length*2), view=new DataView(buffer);
    const string=(offset,text)=>{for(let i=0;i<text.length;i++)view.setUint8(offset+i,text.charCodeAt(i));};
    string(0,'RIFF');view.setUint32(4,36+samples.length*2,true);string(8,'WAVE');string(12,'fmt ');
    view.setUint32(16,16,true);view.setUint16(20,1,true);view.setUint16(22,1,true);
    view.setUint32(24,sampleRate,true);view.setUint32(28,sampleRate*2,true);
    view.setUint16(32,2,true);view.setUint16(34,16,true);string(36,'data');view.setUint32(40,samples.length*2,true);
    for(let i=0;i<samples.length;i++) {
      const s=Math.max(-1,Math.min(1,samples[i]));
      view.setInt16(44+i*2,s<0?Math.round(s*32768):Math.round(s*32767),true);
    }
    return new Blob([buffer],{type:'audio/wav'});
  }
  function quality(samples,rate) {
    let sum=0,clipped=0;
    for(const s of samples){sum+=s*s;if(Math.abs(s)>=.998)clipped++;}
    const rms=Math.sqrt(sum/samples.length),duration=samples.length/rate,warnings=[];
    if(duration<3)warnings.push('时长不足 3 秒');
    if(rms<.01)warnings.push('音量偏低');
    if(clipped/samples.length>.005)warnings.push('存在削波');
    return {duration,rmsDb:20*Math.log10(Math.max(rms,1e-12)),warnings};
  }
  function renderClip(samples,rate,origin,task,session,language) {
    if(samples.length/rate<.25)throw new Error('录音太短，请至少录制 0.25 秒');
    const info=quality(samples,rate);
    const blob=wavBlob(samples,rate);
    if(previewUrl)URL.revokeObjectURL(previewUrl);
    previewUrl=URL.createObjectURL(blob);
    state.clip={blob,sampleRate:rate,task,session,source:origin,quality:info,language};
    state.lastPrediction=null;
    state.samples=samples;
    const bins=1024,step=Math.max(1,Math.ceil(samples.length/bins));
    state.waveform=new Float32Array(bins*2);
    for(let bin=0;bin<bins;bin++){
      let low=0,high=0;
      for(let i=bin*step;i<Math.min(samples.length,(bin+1)*step);i++){low=Math.min(low,samples[i]);high=Math.max(high,samples[i]);}
      state.waveform[bin*2]=low;state.waveform[bin*2+1]=high;
    }
    el('audioPlayback').src=previewUrl;
    el('downloadAudio').href=previewUrl;
    el('downloadAudio').download=`${session}-${task}.wav`;
    el('audioPreview').hidden=false;
    el('audioQuality').textContent=`${info.duration.toFixed(1)} 秒 · ${(rate/1000).toFixed(1)} kHz · ${info.rmsDb.toFixed(1)} dBFS`+
      (info.warnings.length?' · '+info.warnings.join(' / '):' · 基础检查通过');
    el('audioQuality').dataset.warning=String(Boolean(info.warnings.length));
    el('saveAudio').disabled=false;el('saveAudio').textContent='保存本机';
    el('waveLabel').textContent='采集声波';
    el('waveTime').textContent=info.duration.toFixed(1)+' 秒';
    const axis=el('waveAxis');axis.replaceChildren();
    for(let i=0;i<4;i++){const span=document.createElement('span');span.textContent=(info.duration*i/3).toFixed(1)+'s';axis.append(span);}
    el('signalState').textContent='已采集';
    el('score').textContent='—';el('scoreArc').style.strokeDasharray='0 100';
    el('scoreBand').textContent='等待 Transformer 分析';el('scoreBand').classList.add('pending');
    el('scoreBand').nextElementSibling.textContent='研究分类 · 不能替代临床诊断';
    el('predictionWarnings').textContent='';
    el('export').disabled=true;
    for(const id of ['f0Value','jitterValue','shimmerValue','hnrValue'])el(id).textContent='—';
    el('f0Value').textContent=info.duration.toFixed(1)+' 秒';
    status('回放确认后，可保存到本机');lock(false);
  }
  function clearClip() {
    if(state.busy||saving)return;
    el('audioPlayback').pause();el('audioPlayback').removeAttribute('src');el('audioPlayback').load();
    if(previewUrl)URL.revokeObjectURL(previewUrl);previewUrl=null;
    state.clip=null;state.samples=null;state.waveform=null;el('audioPreview').hidden=true;
    state.lastPrediction=null;el('export').disabled=true;
    el('analyze').disabled=true;el('analyze').firstElementChild.textContent='请先采集语音';
    el('waveLabel').textContent='等待语音';el('waveTime').textContent='00:00 / 00:06';
    el('waveAxis').replaceChildren(...[0,2,4,6].map(n=>{const span=document.createElement('span');span.textContent=n+'s';return span;}));
    el('signalState').textContent='就绪';el('scoreBand').classList.remove('pending');
    el('score').textContent='—';el('scoreArc').style.strokeDasharray='0 100';
    el('scoreBand').textContent='等待语音输入';el('scoreBand').nextElementSibling.textContent='研究分类 · 不能替代临床诊断';
    el('predictionWarnings').textContent='';
    for(const id of ['f0Value','jitterValue','shimmerValue','hnrValue'])el(id).textContent='—';
    status('最长录音 30 秒 · 支持外接麦克风');
    lock(false);
  }
  state.clear=clearClip;
  async function release() {
    clearInterval(recordTimer);
    if(worklet){worklet.port.onmessage=null;worklet.disconnect();}worklet=null;
    sourceNode?.disconnect();sourceNode=null;muteNode?.disconnect();muteNode=null;
    stream?.getTracks().forEach(track=>track.stop());stream=null;state.analyser=null;
    if(audioContext&&audioContext.state!=='closed')await audioContext.close();audioContext=null;
  }
  async function stop() {
    if(!state.recording)return;
    state.recording=false;el('recordAudio').disabled=true;el('recordAudio').textContent='处理中…';
    clearInterval(recordTimer);
    const rate=audioContext.sampleRate,task=state.captureTask,session=state.captureSession;
    try {
      await new Promise((resolve,reject)=>{
        const timer=setTimeout(()=>reject(new Error('音频处理超时，请重新录制')),2500);
        stoppedAck=()=>{clearTimeout(timer);resolve();};worklet.port.postMessage('stop');
      });
      const samples=new Float32Array(sampleCount);let at=0;
      for(const chunk of chunks){samples.set(chunk,at);at+=chunk.length;}
      await release();renderClip(samples,rate,'microphone',task,session,state.captureLanguage);
    }catch(error){await release();status(error.message);toast(error.message);}
    finally{chunks=[];sampleCount=0;stoppedAck=null;el('recordAudio').textContent='● 开始录音';el('recordAudio').classList.remove('is-recording');el('recordAudio').setAttribute('aria-pressed','false');lock(false);}
  }
  async function start() {
    if(running)return toast('请等待模型分析完成');
    try {
      consent();
      if(!window.isSecureContext||!navigator.mediaDevices?.getUserMedia)throw new Error('请通过本机 localhost 或 HTTPS 打开录音页面');
      if(!window.AudioWorkletNode)throw new Error('浏览器不支持录音处理，请使用新版 Chrome / Edge，或导入音频');
      lock(true);status('等待麦克风授权…');el('recordAudio').textContent='等待授权…';
      // Permissions are requested only after the user clicks Start.
      stream=await navigator.mediaDevices.getUserMedia({audio:{channelCount:1,echoCancellation:false,noiseSuppression:false,autoGainControl:false},video:false});
      audioContext=new AudioContext();await audioContext.resume();
      await audioContext.audioWorklet.addModule('pcm-worklet.js');
      chunks=[];sampleCount=0;sourceNode=audioContext.createMediaStreamSource(stream);
      worklet=new AudioWorkletNode(audioContext,'pcm-collector');
      state.analyser=audioContext.createAnalyser();state.analyser.fftSize=2048;
      worklet.port.onmessage=event=>{
        if(event.data.type==='pcm'){
          const room=Math.max(0,Math.floor(audioContext.sampleRate*maxSeconds)-sampleCount);
          const chunk=event.data.chunk.subarray(0,room);
          if(chunk.length){chunks.push(chunk);sampleCount+=chunk.length;}
          if(sampleCount>=audioContext.sampleRate*maxSeconds&&state.recording)stop();
        }else if(event.data.type==='stopped')stoppedAck?.();
      };
      sourceNode.connect(worklet);sourceNode.connect(state.analyser);
      muteNode=audioContext.createGain();muteNode.gain.value=0;
      worklet.connect(muteNode).connect(audioContext.destination);
      state.captureTask=selected;state.captureSession=el('sessionId').textContent;state.captureLanguage=el('audioLanguage').value;
      state.recording=true;startedAt=performance.now();
      state.lastPrediction=null;el('export').disabled=true;el('score').textContent='—';
      el('scoreArc').style.strokeDasharray='0 100';el('scoreBand').textContent='正在采集新语音';
      el('recordAudio').disabled=false;el('recordAudio').textContent='■ 停止录音';el('recordAudio').setAttribute('aria-pressed','true');
      el('recordAudio').classList.add('is-recording');el('signalState').textContent='录音中';el('waveLabel').textContent='实时麦克风';
      stream.getAudioTracks()[0].addEventListener('ended',()=>{if(state.recording)stop();});
      recordTimer=setInterval(()=>{
        const seconds=(performance.now()-startedAt)/1000;
        status(`录音 ${seconds.toFixed(1)} / ${maxSeconds} 秒`);el('waveTime').textContent=seconds.toFixed(1)+' 秒';
        if(seconds>=maxSeconds)stop();
      },100);
    }catch(error){
      state.recording=false;await release();lock(false);el('recordAudio').textContent='● 开始录音';
      const message={NotAllowedError:'未获麦克风授权，可重试或导入音频',NotFoundError:'未找到麦克风，请连接设备或导入音频',NotReadableError:'麦克风被占用或不可用，请检查系统设置'}[error.name]||error.message;
      status(message);toast(message);
    }
  }
  el('recordAudio').onclick=()=>{if(state.recording)stop();else if(!state.busy)start();};
  el('importAudio').onclick=()=>{try{if(running)throw new Error('请等待模型分析完成');consent();el('audioFile').click();}catch(error){toast(error.message);}};
  el('audioFile').onchange=async event=>{
    const file=event.target.files[0];if(!file)return;
    let context;
    try{
      consent();if(state.busy)throw new Error('请先结束当前录音');if(file.size>24*1024*1024)throw new Error('音频文件不能超过 24 MB');
      lock(true);status('正在解码音频…');context=new AudioContext({sampleRate:16000});
      const decoded=await context.decodeAudioData(await file.arrayBuffer());
      if(decoded.duration>120)throw new Error('导入音频最长 120 秒');
      if(decoded.sampleRate<8000||decoded.sampleRate>96000)throw new Error('采样率须在 8–96 kHz 之间');
      const mono=new Float32Array(decoded.length);
      for(let c=0;c<decoded.numberOfChannels;c++){const data=decoded.getChannelData(c);for(let i=0;i<data.length;i++)mono[i]+=data[i]/decoded.numberOfChannels;}
      renderClip(mono,decoded.sampleRate,'file',selected,el('sessionId').textContent,el('audioLanguage').value);
    }catch(error){const message=error.name==='EncodingError'?'无法解码此音频，请尝试 WAV 或 MP3':error.message;status(message);toast(message);}
    finally{if(context&&context.state!=='closed')await context.close();lock(false);event.target.value='';}
  };
  el('clearAudio').onclick=clearClip;
  el('saveAudio').onclick=async()=>{
    if(!state.clip||saving)return;
    try{
      consent();saving=true;lock(true);el('saveAudio').disabled=true;el('saveAudio').textContent='保存中…';
      const clip=state.clip,params=new URLSearchParams({session:clip.session,task:clip.task,source:clip.source,consent:'yes'});
      const response=await fetch('/api/recordings?'+params,{method:'POST',headers:{'Content-Type':'audio/wav'},body:clip.blob});
      const type=response.headers.get('Content-Type')||'';
      if(!type.includes('application/json'))throw new Error('请使用 recording_server.py 启动采集服务');
      const data=await response.json();if(!response.ok)throw new Error(data.error||'保存失败');
      clip.savedId=data.recording.id;el('saveAudio').textContent='已保存';
      status('已保存到本机 recordings 目录');toast('录音已保存');loadSaved();
    }catch(error){el('saveAudio').disabled=false;el('saveAudio').textContent='重试保存';toast(error.message);}
    finally{saving=false;lock(false);}
  };
  async function loadSaved(){
    const target=el('savedRecordings');
    try{
      const response=await fetch('/api/recordings');
      if(!response.ok||!response.headers.get('Content-Type')?.includes('application/json'))throw new Error('请用 recording_server.py 启动本机采集服务');
      const data=await response.json();target.replaceChildren();
      state.savedCount=data.recordings.length;
      el('recordCount').textContent=String(state.savedCount+records.length).padStart(2,'0');
      if(!data.recordings.length){target.textContent='暂无已保存录音';return;}
      data.recordings.forEach(record=>{
        const row=document.createElement('article');row.className='saved-recording';
        const info=document.createElement('div'),title=document.createElement('strong'),details=document.createElement('span');
        title.textContent=record.session+' · '+(tasks[record.task]||record.task);
        details.textContent=`${record.duration_seconds.toFixed(1)} 秒 · ${record.sample_rate/1000} kHz · ${record.source==='microphone'?'麦克风':'文件'} · `+new Date(record.created_at).toLocaleString('zh-CN',{timeZone:'Asia/Shanghai'});
        const warning=document.createElement('small');warning.textContent=record.warnings.length?record.warnings.join(' / '):'基础质量检查通过';
        info.append(title,details,warning);
        const player=document.createElement('audio');player.controls=true;player.preload='none';player.src=record.audio_url;player.setAttribute('aria-label','回放 '+record.session);
        row.append(info,player);target.append(row);
      });
    }catch(error){target.textContent=error.message;}
  }
  el('refreshRecordings').onclick=loadSaved;
  document.querySelector('[data-view="records"]').addEventListener('click',loadSaved);
  window.addEventListener('pagehide',()=>{stream?.getTracks().forEach(track=>track.stop());audioContext?.close();});
  async function loadModel(){
    try{
      const response=await fetch('/api/model');if(!response.ok)throw new Error('模型接口不可用，请使用新版录音服务');
      const info=await response.json();state.modelInfo=info;
      el('modelStatus').textContent=info.ready?'CNN + Transformer · 英文朗读研究分类':info.reason||'模型尚未就绪';
      if(info.progress?.status==='training')el('modelStatus').textContent+=` · 第 ${info.progress.fold} 折 / ${info.progress.epoch} 轮`;
      const details=el('modelDetails');details.replaceChildren();
      if(info.ready){
        const specs=document.createElement('div');specs.className='model-specs';
        [[info.subjects,'训练语料受试者'],[info.evaluation.metrics.auc.toFixed(3),'受试者级 OOF AUC'],[info.evaluation.metrics.sensitivity.toFixed(3),'敏感度（0.5 阈值）'],[info.evaluation.metrics.specificity.toFixed(3),'特异度（0.5 阈值）']].forEach(([value,label])=>{const item=document.createElement('div'),strong=document.createElement('strong'),span=document.createElement('span');strong.textContent=value;span.textContent=label;item.append(strong,span);specs.append(item);});
        const description=document.createElement('p');description.textContent='来源：'+info.dataset.join(' / ')+'；任务：英文朗读。外层按人交叉验证，内层验证集早停。分数未经人群患病率校准，不能解释为患病概率。';
        const limits=document.createElement('p');limits.textContent='病例对照小样本研究；无独立中文验证。OOF 结果描述各留出折模型，不是对部署集成模型的独立外部验证。';
        details.append(specs,description,limits);
      }else{const p=document.createElement('p');p.textContent=info.reason||'缺少训练模型';details.append(p);}
      if(!state.busy)lock(false);
    }catch(error){state.modelInfo={ready:false};el('modelStatus').textContent=error.message;}
  }
  el('analyze').onclick=async()=>{
    if(state.busy||!state.clip||!state.modelInfo?.ready)return;
    try{
      consent();lock(true);running=true;state.lastPrediction=null;el('export').disabled=true;
      el('signalState').textContent='推理中';el('score').textContent='—';el('scoreArc').style.strokeDasharray='0 100';
      el('scoreBand').textContent='Transformer 正在分析';el('predictionWarnings').textContent='';
      const clip=state.clip,params=new URLSearchParams({task:clip.task,language:clip.language,consent:'yes'});
      const response=await fetch('/api/predict?'+params,{method:'POST',headers:{'Content-Type':'audio/wav'},body:clip.blob});
      const data=await response.json();if(!response.ok)throw new Error(data.error||'分析失败');
      const result=data.prediction;state.lastPrediction=result;
      result.label={hc_like:'更接近健康对照组',pd_like:'更接近帕金森病组',uncertain:'无法明确归组'}[result.prediction]||'无法明确归组';
      el('score').textContent=result.model_score.toFixed(3);el('scoreArc').style.strokeDasharray=result.model_score*100+' 100';
      el('scoreBand').textContent=result.label;el('scoreBand').classList.toggle('pending',result.uncertain);
      el('predictionWarnings').textContent=result.warnings.join(' ');
      el('f0Value').textContent=result.quality.duration_seconds.toFixed(1)+' 秒';
      el('jitterValue').textContent=result.sample_rate/1000+' kHz';
      el('shimmerValue').textContent=result.segments+' 段';
      el('hnrValue').textContent=result.model_spread.toFixed(3);
      el('signalState').textContent='分析完成';el('export').disabled=false;
      records.unshift({session:clip.session,score:result.model_score,label:result.label,time:new Date().toISOString()});renderRecords();
      toast('Transformer 分析完成');
    }catch(error){el('signalState').textContent='需复核';el('scoreBand').textContent='未生成分类结果';el('predictionWarnings').textContent=error.message;toast(error.message);}
    finally{running=false;lock(false);}
  };
  loadSaved();loadModel();setInterval(()=>{if(!state.busy)loadModel();},15000);
})();
