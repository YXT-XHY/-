# 本机声音采集

更新：已接入真实 CNN + Transformer 英文朗读研究分类。请使用 `.venv-dl/Scripts/python.exe recording_server.py --port 8768`，访问 http://127.0.0.1:8768/ ，完整说明见 [DEEP_LEARNING.md](DEEP_LEARNING.md)。后文“尚未接入模型”描述为早期采集版本的边界，已由当前深度学习版本替代。

## 启动与使用

在 `uci_pd_simple` 目录执行：

```powershell
python recording_server.py
```

本机默认打开地址为 http://127.0.0.1:8767/ 。当前机器可使用：

```powershell
& 'C:\Users\XuYang\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' recording_server.py
```

1. 选择持续元音、音节重复或短文朗读任务。
2. 确认已获受试者同意。点击“开始录音”，允许浏览器访问麦克风，录音后点击“停止录音”。最长 30 秒自动停止。
3. 或点击“导入音频”，选择 WAV / MP3 / M4A / OGG 等浏览器支持的格式。最大 24 MB、最长 120 秒；不支持的编解码器会提示转换格式。
4. 回放、查看基础质量提示。点击“保存本机”写入 recordings 目录，或下载 WAV 自行保存。
5. 在“分析记录”查看已保存的录音；刷新页面后，本机档案仍可读取。

外接麦克风、USB 声卡等设备通过系统或浏览器默认输入设备选择。页面仅在用户点击开始后请求权限。手机通过普通局域网 HTTP 地址访问通常无法录音，需要 HTTPS；当前服务只绑定本机 127.0.0.1。

## 数据流

麦克风 → getUserMedia → AudioWorklet（混合为单声道 PCM）→ WAV 编码 → 回放/技术质量检查 → 用户点击保存 → 本机 API → recordings/{随机 ID}/audio.wav + metadata.json。

音频文件 → 浏览器 decodeAudioData → 单声道 PCM → 相同 WAV/保存流程。

不使用自动增益、回声消除、降噪作为录音请求选项；实际硬件和浏览器可能仍有自己的处理。PCM 为 AudioContext 实际采样率，不强制声称原始设备采样率。文件导入可能由浏览器重采样，元数据记录的是保存的 WAV 采样率。录音过程无扬声器回授。

## 元数据与质量检查

保存会话编号、任务、采集来源、UTC 时间、采样率、帧数、时长、16 位单声道格式、SHA-256、同意确认标记、RMS dBFS、峰值和削波比例。使用随机 ID，不收集姓名或身份证。

少于 3 秒、RMS 低于约 -40 dBFS、削波比例超过 0.5% 会提示复核。这些是工程启发式阈值，不是临床标准，不能说明是否存在帕金森病。质量提示不会阻止用户保存，服务会再次验证格式。

## 与 UCI 模型的边界

录音不会直接得到疾病分数：UCI 模型需要固定定义的 22 维特征，当前尚未完成对应特征提取与一致性验证。采集后模型区域显示“待提取特征”，禁止运行示例分析或导出示例模型报告，避免混淆。

可清除当前音频后恢复模拟分析；或导入已有 UCI CSV 继续原来的特征展示。清除只丢弃浏览器当前片段，不会删除本机档案。任务和会话在开始录音/导入时固定，保存沿用该快照。

## 本机接口

- GET /api/health：服务状态（inference=false）。
- GET /api/recordings：已保存元数据列表。
- POST /api/recordings?session=...&task=vowel&source=microphone&consent=yes：二进制 audio/wav，返回 201 与元数据。
- GET /api/recordings/{id}/audio：回放 WAV。

服务无额外依赖，绑定本机地址，限制 Host / Origin、24 MB 上传、单声道 16 位 PCM、8–96 kHz、0.25–120 秒。目录列表关闭。它是单机研究工具，没有账户权限、多人隔离或互联网部署能力。保存目录包含可识别声音，应按实际研究的数据管理约定保管。

## 验证

```powershell
python -m unittest discover -s tests -v
node tests/test_capture.mjs
```

后端验证使用合成正弦波；覆盖保存回放、格式、静音、削波、时长、无同意、来源限制和路径保护。前端测试覆盖 WAV 编码、AudioWorklet 分块、停止时尾帧刷新和混音。实际麦克风音质与浏览器权限仍需操作者在设备上确认。
