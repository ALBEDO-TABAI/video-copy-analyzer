# FunASR 技术细节与故障排除

## 技术细节

本 skill 使用 FunASR 的 **Paraformer** 系列模型组合：

```python
from funasr import AutoModel

model = AutoModel(
    model="paraformer-zh",        # 中文 ASR（含 SeACo 增强）
    vad_model="fsmn-vad",         # 语音活动检测（自动分段长音频）
    vad_kwargs={"max_single_segment_time": 60000},  # 每段最长 60 秒
    punc_model="ct-punc",         # 标点恢复
    disable_update=True,          # 禁用版本检查
)

result = model.generate(
    input="audio.wav",
    batch_size_s=300,             # 动态 batch
    cache={},                     # 官方推荐参数
)
```

**性能参考**（MacBook Pro M 系列 CPU）：

| 音频时长 | 转录耗时 | RTF | 字幕条数 |
|---------|---------|-----|---------|
| 42 秒 | 2 秒 | 0.049 | ~11 条 |
| 9 分钟 | 22 秒 | 0.036 | ~137 条 |
| 10 分钟 | 22 秒 | 0.035 | ~142 条 |

---

## 首次运行注意事项

FunASR 首次运行时会**自动下载约 2-3GB 模型文件**到 `~/.cache/modelscope/`：

| 模型 | 大小 | 用途 |
|------|------|------|
| paraformer-zh | ~1.05GB | 中文语音识别（ASR） |
| fsmn-vad | ~20MB | 语音活动检测（长音频分段） |
| ct-punc | ~1GB | 标点恢复 |

- 首次下载可能需要 1-5 分钟（取决于网速），期间看起来像是卡住，请耐心等待
- 下载完成后会缓存到本地，后续运行秒级加载

---

## 故障排除

### FunASR 首次运行很慢 / 看起来卡住
首次运行需下载约 2-3GB 模型文件，这是正常现象。在网速 30MB/s 的环境下约需 1-2 分钟。下载完成后后续运行秒级加载。

### FunASR 模型下载失败
如果 ModelScope 下载速度慢或中断，可手动从 [ModelScope](https://www.modelscope.cn/models) 下载以下模型到 `~/.cache/modelscope/hub/models/iic/` 目录：
- `speech_seaco_paraformer_large_asr_nat-zh-cn-16k-common-vocab8404-pytorch`
- `speech_fsmn_vad_zh-cn-16k-common-pytorch`
- `punc_ct-transformer_cn-en-common-vocab471067-large`

### torch 版本不兼容
FunASR 需要 PyTorch 2.0+，建议：
```bash
pip install torch torchaudio --upgrade
```

### 字幕提取脚本直接运行卡住
不要直接运行 `python extract_subtitle_funasr.py video.mp4 output.srt`（它会调用 B站 API 获取字幕并因 cookies 问题卡住）。请按照 SKILL.md 阶段 2 的说明，直接调用 `extract_with_funasr()` 函数。
