# 公开数据工具验证记录

日期：2026-10-28（Asia/Shanghai）。

| 验证 | 结果 |
| --- | --- |
| 全工程Python回归 | 51项通过，无跳过；含11项公开获取工具测试及真实模型/API集成测试 |
| 官方记录详情 | Zenodo 19606497读取成功，open、CC BY 4.0，文件名／大小／校验和可用 |
| 实际批量下载 | `description.pdf`（38377字节）及`sentences.csv`（3495字节）下载成功，均匹配官方MD5，另生成SHA-256和来源回执 |
| 默认检索 | 默认查询成功完成，返回0条，查询与时间保存于`data/public_discovery/search_results.json` |
| 查询正对照 | `title:Parkinson`与`metadata.title:Parkinson`均返回478条原始命中，证明标题字段有效；该数值不是中文数据集数量 |
| 宽查询误匹配 | `Parkinson AND Mandarin`曾命中英文ESPnet预训练模型4499539，其说明包含相关关键词；资源类型／标题过滤已排除此类误匹配 |
| 网络异常 | 遇到过SSL连接EOF，已实现有限连接重试；遇到过过大元数据，已加入32 MiB边界与缩小查询提示 |

实际下载文件只是公开研究说明PDF与文本材料，用于验证传输链路，不是新取得的中文临床录音。下载器不会自动解压、生成诊断标签或启动训练。断点续传、Range异常、损坏与已有文件保护由受控传输测试验证；真实网络下载不等于所有服务器的断点行为都已验证。

重现测试时，本机沙箱需将临时目录指定到项目父目录下的`.tmp`，并允许本机回环HTTP集成测试：

```powershell
$env:TEMP = (Resolve-Path '..\.tmp').Path
$env:TMP = $env:TEMP
& '.\.venv-dl\Scripts\python.exe' -m unittest discover -s tests -q
```

下载联调使用[官方开放记录](https://zenodo.org/records/19606497)；接口依据[Zenodo开发文档](https://developers.zenodo.org/)。已知中文数据申请入口另见[CHINESE_DATA_SOURCES.md](CHINESE_DATA_SOURCES.md)。
