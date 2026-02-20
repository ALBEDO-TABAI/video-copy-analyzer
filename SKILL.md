---
name: video-copy-analyzer
description: >
  视频文案分析一站式工具。下载在线视频（B站/YouTube/抖音等）、使用FunASR进行高速中文语音转录、
  自动校正文稿、并进行三维度综合分析（TextContent/Viral/Brainstorming）。
  使用场景：当用户需要分析短视频文案、提取视频内容、学习爆款文案技巧时。
  关键词：视频分析、文案分析、语音转文字、FunASR、爆款分析、视频下载
---

# 视频文案分析工具

一站式视频内容提取与文案分析，支持 B站、YouTube、抖音 等平台。

## 安装部署

### 系统要求

- Python 3.9+
- FFmpeg（用于音视频处理）
- 约 3GB 磁盘空间（FunASR 模型缓存）

### 一键安装

```bash
# 1. 基础工具
brew install ffmpeg  # macOS
pip install yt-dlp requests pysrt python-dotenv

# 2. FunASR（核心 ASR 引擎，中文语音转录）
pip install funasr modelscope torch torchaudio

# 3. RapidOCR（烧录字幕识别，可选）
pip install rapidocr-onnxruntime
```

### ⚠️ FunASR 首次运行注意事项

FunASR 首次运行时会**自动下载约 2-3GB 模型文件**到 `~/.cache/modelscope/`：

| 模型 | 大小 | 用途 |
|------|------|------|
| paraformer-zh | ~1.05GB | 中文语音识别（ASR） |
| fsmn-vad | ~20MB | 语音活动检测（长音频分段） |
| ct-punc | ~1GB | 标点恢复 |

- **首次下载可能需要 1-5 分钟**（取决于网速），期间看起来像是卡住，请耐心等待
- 下载完成后会缓存到本地，后续运行秒级加载
- 如果下载失败，可手动从 ModelScope 下载模型放到 `~/.cache/modelscope/hub/models/iic/` 目录

### 环境验证

```bash
# 验证所有依赖
python scripts/check_environment.py

# 或手动检查关键组件
yt-dlp --version
ffmpeg -version
python -c "from funasr import AutoModel; print('FunASR OK')"
python -c "from rapidocr_onnxruntime import RapidOCR; print('RapidOCR OK')"
```

## 首次使用设置

首次使用时，询问用户：

> "请设置默认工作目录（用于保存下载的视频和分析报告）：
> 
> A. 使用默认目录：`~/video-analysis/`
> B. 每次手动指定目录
> C. 指定一个固定目录：[请输入路径]"

保存用户选择供后续使用。

## 工作流程（4 阶段）

### 阶段 1: 下载视频

1. 获取用户视频 URL 和输出目录
2. **判断视频平台**：
   - **抖音链接**（douyin.com 或 v.douyin.com）：使用专用脚本下载
   - **其他平台**（B站、YouTube等）：使用 yt-dlp 下载

#### 抖音视频下载

对于抖音链接，使用 `scripts/download_douyin.py`：

```bash
python scripts/download_douyin.py "<抖音链接>" "<输出路径>"
```

**支持的抖音链接格式**：
- 短链接：`https://v.douyin.com/xxxxx`
- 长链接：`https://www.douyin.com/video/xxxxx`
- 精选页：`https://www.douyin.com/jingxuan?modal_id=xxxxx`
- 分享链接：`https://m.douyin.com/share/video/xxxxx`

#### 其他平台下载（yt-dlp）

对于 B站、YouTube 等平台：

```bash
yt-dlp -f "bestvideo[height<=1080]+bestaudio/best[height<=1080]" \
  --merge-output-format mp4 \
  -o "<output_dir>/%(id)s.%(ext)s" \
  "<video_url>"
```

3. 记录视频文件路径

### 阶段 2: 智能字幕提取

使用 `scripts/extract_subtitle_funasr.py` 进行智能字幕提取，自动选择最佳方案：

```bash
python scripts/extract_subtitle_funasr.py <视频路径> <输出SRT路径>
```

**智能提取流程（三层优先级）**：

```
视频输入
    ↓
[1️⃣ 内嵌字幕检测] ──→ 检测到字幕流 ──→ 直接提取（准确度最高）
    ↓ 未检测到
[2️⃣ 烧录字幕检测] ──→ RapidOCR 采样帧识别 ──→ 检测到文字 ──→ 全视频 OCR 提取
    ↓ 未检测到
[3️⃣ FunASR 语音转录] ──→ 高速中文转录（10倍 Whisper 速度）
    ↓
输出 SRT 字幕
```

**三层提取策略详解**：

| 层级 | 方法 | 适用场景 | 准确度 | 速度 |
|------|------|---------|--------|------|
| **L1** | 内嵌字幕提取 | 视频自带字幕流 | ⭐⭐⭐⭐⭐ | ⚡ 极快 |
| **L2** | RapidOCR 烧录字幕识别 | 字幕烧录在画面中 | ⭐⭐⭐⭐ | 🚀 快 |
| **L3** | FunASR 语音转录 | 无字幕，纯语音 | ⭐⭐⭐⭐ | ⚡ 极快 |

### FunASR 技术细节

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
| 30 秒 | 1.9 秒 | 0.063 | ~8 条 |
| 10 分钟 | 22 秒 | 0.036 | ~150 条 |

- **RTF（实时率）**：0.035 表示 1 秒音频只需 0.035 秒处理
- **时间戳**：返回字级时间戳，脚本按标点自动切分为自然句
- **标点**：ct-punc 模型自动恢复中文标点（句号、问号、逗号等）
- **对比 Whisper Large**：同样 10 分钟音频 Whisper 需要 7 分钟，FunASR 仅 22 秒

### 阶段 3: 文稿校正

1. 读取 SRT 字幕文件
2. 合并字幕为连续文本
3. 基于上下文语义进行智能校正：
   - 修正同音字错误
   - 修正专业术语
   - 补充标点符号
4. 输出校正后的文字稿（Markdown 格式）

**校正输出格式**：
```markdown
# 视频语音转录文字稿

**视频来源**: [URL]
**转录时间**: [日期]

---

## 完整文字稿

[校正后的正文内容]

---

## 原始 SRT 字幕

[带时间戳的原始转录]
```

### 阶段 4: 三维度综合分析

应用三个分析框架进行深度分析：

#### 4.1 TextContent Analysis 视角
- 叙事结构分析
- 叙事声音分析
- 修辞手法识别
- 词库提取

#### 4.2 Viral-Abstract-Script 视角
- Viral-5D 框架诊断（Hook/Emotion/爆点/CTA/社交货币）
- 风格定位
- 爆款潜力评估
- 优化建议

#### 4.3 Brainstorming 视角
- 核心价值拆解
- 2-3 种创意方向探索
- 增量验证点

**分析输出格式**：
```markdown
# 视频文案综合分析报告（三维度）

## 一、TextContent Analysis 视角
[叙事结构、修辞手法、词库]

## 二、Viral-Abstract-Script 视角
[Viral-5D诊断、风格定位、优化建议]

## 三、Brainstorming 视角
[价值拆解、创意方向、验证点]

## 四、综合评估与建议
[评分、改进建议、改写示例]
```

## 完成后输出

完成所有阶段后，向用户播报：

```
✅ 视频文案分析完成！

📁 输出目录: <用户指定的目录>

📄 生成文件:
  - <视频ID>.mp4         (原始视频)
  - <视频ID>.srt         (原始字幕)
  - <视频ID>_文字稿.md    (校正后文字稿)
  - <视频ID>_分析报告.md  (三维度分析报告)

🔗 快速打开:
  [文字稿](<文字稿路径>)
  [分析报告](<分析报告路径>)
```

## 参考文件

- [download_douyin.py](scripts/download_douyin.py): 抖音视频下载脚本
- [extract_subtitle_funasr.py](scripts/extract_subtitle_funasr.py): 智能字幕提取脚本（FunASR + RapidOCR）
- [fetch_bilibili_subtitle.py](scripts/fetch_bilibili_subtitle.py): B站字幕获取脚本（需登录cookies，可选）
- [analysis-frameworks.md](references/analysis-frameworks.md): 三个分析框架详解

## 故障排除

### FunASR 首次运行很慢 / 看起来卡住
首次运行需下载约 2-3GB 模型文件，这是正常现象。在网速 30MB/s 的环境下约需 1-2 分钟。下载完成后后续运行秒级加载。

### FunASR 模型下载失败
如果 ModelScope 下载速度慢或中断，可设置镜像：
```bash
export MODELSCOPE_CACHE=~/.cache/modelscope
```
或手动从 [ModelScope](https://www.modelscope.cn/models) 下载以下模型到 `~/.cache/modelscope/hub/models/iic/` 目录：
- `speech_seaco_paraformer_large_asr_nat-zh-cn-16k-common-vocab8404-pytorch`
- `speech_fsmn_vad_zh-cn-16k-common-pytorch`
- `punc_ct-transformer_cn-en-common-vocab471067-large`

### torch 版本不兼容
FunASR 需要 PyTorch 2.0+，建议：
```bash
pip install torch torchaudio --upgrade
```
