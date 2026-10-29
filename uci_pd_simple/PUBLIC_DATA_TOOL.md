# 公开数据检索与下载工具

仅使用Python标准库，无需安装深度学习依赖。进入`uci_pd_simple`后运行以下命令；如果系统没有Python，可将`python`替换成`.\.venv-dl\Scripts\python.exe`。

## 1. 查看已核查的数据获取途径

```powershell
python -m data_tools catalog
```

本地目录包含台大30人、中文轻度PD 278人、普通话100人、台大360人及清华1035人等线索，明确标记申请制或共享状态未确认。目录不是已下载的训练集；完整证据见[中文数据核查](CHINESE_DATA_SOURCES.md)。

## 2. 检索公开仓库

```powershell
python -m data_tools search --limit 20 --pages 3
python -m data_tools search --query 'Parkinson AND Mandarin' --limit 20 --pages 3
```

当前在线检索范围为Zenodo公开只读API，不是全网爬虫。每页最多50条，最多10页；每次新请求至少间隔1秒。结果再次按元数据中的PD、中文语种和语音关键词过滤，但摘要提及中文不代表音频一定是中文，命中也不代表含有医生诊断。

默认查询要求标题含Parkinson，并组合中文语种与语音关键词，以减少无关大仓库；可用`--query`修改或放宽。元数据单次响应上限32 MiB，超限时提示缩小查询或页大小。

完整结果保存为`data/public_discovery/search_results.json`，包括查询式、请求URL、时间、已检查记录数、文件清单、许可和待核查项。`total`是服务器的原始命中总数，不是符合中文PD条件的数据集数量；未找到候选也不证明不存在相关数据。重复检索会更新该结果文件，需保留历史时指定不同输出目录：

```powershell
python -m data_tools --output data/search_run_02 search --query 'Parkinson AND Chinese'
```

## 3. 查看记录详情

```powershell
python -m data_tools inspect 2867216
```

示例为已有的**英文**MDVR-KCL记录。此命令读取官方访问状态、许可、文件名、大小和校验和，并保存原始元数据`<记录ID>/record.json`；不会下载音频。

## 4. 下载或批量下载指定文件

```powershell
python -m data_tools download 19606497 --file description.pdf --file sentences.csv --max-mb 1
```

这是公开研究说明和文本材料的实际联调示例，不是中文PD录音。真实音频下载时，将记录ID和文件名替换为`inspect`列出的正式值。可重复传入`--file`批量选择文件；`--max-mb`是每个文件的大小上限，默认500 MiB。

- 仅自动下载官方元数据标为open、许可为CC BY 4.0或CC0 1.0的记录；其他许可保持拒绝，需另行审核后扩展支持。
- 下载前重新读取官方元数据；不会使用过期搜索结果直接授权下载。
- 中断后再次执行同一命令会根据`.part`与对应元数据恢复。服务器忽略Range时从头下载；错误的Content-Range会被拒绝。
- 校验文件大小和官方MD5／SHA-256后才发布正式文件；另计算SHA-256，保存来源、DOI、作者与许可回执`*.receipt.json`。
- 既有文件校验通过则复用；校验失败不覆盖。源文件校验失败的临时分片会清除，以便重新下载。
- 仅接受Zenodo HTTPS官方文件地址及同域重定向。401／403或429会停止并说明原因；临时连接错误和部分5xx最多重试两次。
- 不登录、不提交数据申请、不自动解压或运行下载文件，不自动生成PD/HC标签或启动训练。

所有下载回执都保留`eligible_for_training: false`。该字段表示尚未完成本项目的临床、身份、任务及语种核查，不表示公开许可禁止研究。取得中文临床数据后，仍须按[接入方案](CHINESE_DATA_SOURCES.md)建立经过核验的受试者清单。

## 验证

`tests/test_public_data.py`覆盖元数据许可拒绝、相关性过滤、危险文件名／外域重定向、校验失败、断点续传、Range忽略重启、大小限制与既有文件保护。网络联调结果另存于`data/public_discovery/`；下载目录默认不进入Git。

2026-10-28验证：全工程51项测试通过；公开API检索、记录详情及两文件批量下载联调通过。默认窄查询本次返回0条；宽查询曾返回只在说明中提及相关术语的英文ASR模型，已用资源类型与标题条件排除。尚未据此获得中文PD临床录音。详细记录见[PUBLIC_DATA_VALIDATION.md](PUBLIC_DATA_VALIDATION.md)。
