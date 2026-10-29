# NEURODRIVE / Outrun 前端

当前页面提供真实语音采集与 CNN + Transformer 研究分类，保留 Outrun 的霓虹、日落、棕榈剪影和动态网格风格。

从工程上级目录启动：

```powershell
& '.\.venv-dl\Scripts\python.exe' recording_server.py --port 8768
```

打开 http://127.0.0.1:8768/ 。普通静态 HTTP 服务只能预览，不能进行模型推理或保存。

- index.html / outrun.css：界面与响应式布局。
- outrun.js：任务、导航、波形、真实结果报告导出；无固定分数逻辑。
- capture.js / pcm-worklet.js：录音与文件解码、本机 API、质量检查、模型状态、分类展示。
- assets/outrun-neural.png：原创 Outrun 插画；提示词见 assets/OUTRUN_ART.md。

确认同意后录音或导入，回放，再点击 Transformer 分析。仅英文朗读有训练验证；普通话返回不确定，其他任务拒绝分类。结果不能作为临床诊断。只有点击保存才持久存储原始声音，模型推理在本机进行。

已采集音频的任务和语种在采集时固定，需清除当前片段后才能切换，避免把旧音频按新标签分析。

完整训练、验证指标、启动与复现实验见上级 DEEP_LEARNING.md。
