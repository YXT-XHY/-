# NEURODRIVE / 新拟物前端

当前页面提供真实语音采集与 CNN + Transformer 研究分类，采用用户提供的 Neumorphism 设计包：浅灰背景、紫色强调、左上光源和内凹／外凸双重阴影。

从工程上级目录启动：

```powershell
& '.\.venv-dl\Scripts\python.exe' recording_server.py --port 8768
```

打开 http://127.0.0.1:8768/ 。普通静态 HTTP 服务只能预览，不能进行模型推理或保存。

- index.html / neumorphism.css：当前新拟物界面与响应式布局。
- evaluation.css / evaluation.js：评估指标、混淆矩阵、ROC、JSON报告导入及打印／保存PDF。
- outrun.js：任务、导航、波形、真实结果报告导出；无固定分数逻辑。
- capture.js / pcm-worklet.js：录音与文件解码、本机 API、质量检查、模型状态、分类展示。
- outrun.css与旧插画保留为历史设计素材，当前页面不加载；采集区使用代码绘制的麦克风图形。

主结果突出显示“更接近健康对照组”“更接近帕金森病组”或“无法明确归组”，模型分数默认折叠。评估可视化使用真实受试者级OOF预测；导入报告没有逐人预测分数时不绘制ROC。更新后需要重启后端以启用`/api/evaluation`接口。

确认同意后录音或导入，回放，再点击 Transformer 分析。仅英文朗读有训练验证；普通话返回不确定，其他任务拒绝分类。结果不能作为临床诊断。只有点击保存才持久存储原始声音，模型推理在本机进行。

已采集音频的任务和语种在采集时固定，需清除当前片段后才能切换，避免把旧音频按新标签分析。

完整训练、验证指标、启动与复现实验见上级 DEEP_LEARNING.md。
