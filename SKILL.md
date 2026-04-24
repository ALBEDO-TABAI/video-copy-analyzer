---
name: video-copy-analyzer
description: "视频文案分析一站式工具。下载在线视频（B站/YouTube/抖音等）、使用FunASR进行高速中文语音转录、自动校正文稿、并进行三维度综合分析（TextContent/Viral/Brainstorming）。使用场景：当用户需要分析短视频文案、提取视频内容、学习爆款文案技巧时。关键词：视频分析、文案分析、语音转文字、FunASR、爆款分析、视频下载"
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

FunASR 首次运行时会**自动下载约 2-3GB 模型文件**（需 1-5 分钟），后续运行秒级加载。详见 [FunASR 技术细节与故障排除](references/funasr-details.md)。

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

---

## 工作流程（5 阶段）

> **重要：你必须严格按照以下 5 个阶段顺序执行，每个阶段完成后再进入下一个阶段。不要跳过任何阶段。**

### 阶段 1: 下载视频

**目标**：将用户提供的视频 URL 下载为本地 MP4 文件。

**执行步骤**：
1. 获取用户提供的视频 URL 和输出目录
2. 如果输出目录不存在，创建它：`mkdir -p <输出目录>`
3. **判断视频平台并选择下载方式**：

#### 抖音视频（URL 包含 `douyin.com` 或 `v.douyin.com`）

使用专用下载脚本：
```bash
python scripts/download_douyin.py "<抖音链接>" "<输出目录>/<文件名>.mp4"
```

支持的链接格式：`v.douyin.com/xxx`、`www.douyin.com/video/xxx`、`douyin.com/jingxuan?modal_id=xxx`

#### 其他平台（B站、YouTube 等）

使用 yt-dlp：
```bash
yt-dlp -f "bestvideo[height<=1080]+bestaudio/best[height<=1080]" \
  --merge-output-format mp4 \
  -o "<输出目录>/%(id)s.%(ext)s" \
  "<视频URL>"
```

4. **确认下载成功**：检查 MP4 文件是否存在且大小 > 0

---

### 阶段 2: 字幕提取

**目标**：从视频中提取 SRT 格式字幕文件。

**执行步骤**：

**⚠️ 重要：不要调用 `extract_subtitle_funasr.py` 的 `main()` 函数或直接运行整个脚本（它包含 B站 API 调用会因 cookies 问题卡住）。直接调用 `extract_with_funasr` 函数。**

使用以下 Python 代码直接调用 FunASR 提取字幕：

```python
import sys, os
sys.path.insert(0, '<skill_scripts_目录的绝对路径>')
from extract_subtitle_funasr import extract_with_funasr
success = extract_with_funasr('<视频文件绝对路径>', '<输出SRT文件绝对路径>')
```

**执行方式**：将上述代码写入临时 Python 脚本文件（如 `/tmp/run_funasr.py`），然后运行：
```bash
python3 -u /tmp/run_funasr.py 2>&1 | tee /tmp/funasr_output.log
```

**注意事项**：
- 必须使用**绝对路径**，不要使用相对路径
- 首次运行会下载模型（详见 [FunASR 详情](references/funasr-details.md)），后续秒级加载
- 转录速度极快：10 分钟音频约 22 秒完成
- 命令运行后需要等待 30-120 秒（取决于视频长度）

**确认成功**：检查 SRT 文件是否存在且大小 > 0

**字幕提取的内部逻辑（三层优先级，脚本自动处理）**：

| 优先级 | 方法 | 适用场景 | 准确度 | 速度 |
|--------|------|---------|--------|------|
| L1 | 内嵌字幕提取 | 视频自带字幕流 | ⭐⭐⭐⭐⭐ | ⚡ 极快 |
| L2 | RapidOCR 烧录字幕识别 | 字幕烧录在画面中 | ⭐⭐⭐⭐ | 🚀 快 |
| L3 | FunASR 语音转录 | 无字幕，纯语音 | ⭐⭐⭐⭐ | ⚡ 极快 |

---

### 阶段 3: 文稿校正

**目标**：将 SRT 字幕合并为连续文本，基于语义进行校正，输出 `<视频ID>_文字稿.md`。

**执行步骤**：
1. 读取 SRT 字幕文件
2. 提取所有文本行（跳过序号和时间戳行）
3. 合并为连续文本
4. 基于上下文语义进行智能校正：
   - 修正 ASR 产生的同音字错误（如"旗下"→"棋下"）
   - 修正专业术语和人名
   - 确保标点符号正确
5. 保存为 Markdown 文件

**输出文件**：`<输出目录>/<视频ID>_文字稿.md`

**输出格式**：
```markdown
# <视频ID> 原始文字稿

<校正后的完整文本>
```

---

### 阶段 4: 三维度综合分析

**目标**：对文字稿内容进行深度分析，应用三个分析框架，输出 `<视频ID>_分析报告.md`。

**执行步骤**：
1. 读取阶段 3 生成的文字稿内容
2. 依次应用以下三个分析框架
3. 将分析结果保存为 Markdown 文件

**三个分析框架**：

#### 4.1 TextContent Analysis 视角
你必须分析以下维度：
- **叙事结构分析**：开场、发展、高潮、转折、结尾的结构
- **叙事声音分析**：基调、节奏、独特金句
- **修辞手法识别**：比喻、反转、呼应、隐喻等
- **词库提取**：关键词列表

#### 4.2 Viral-Abstract-Script 视角
你必须分析以下维度：
- **Viral-5D 框架诊断**：对 Hook、Emotion、爆点、CTA、社交货币 分别给出⭐评分和分析
- **风格定位**：该视频的内容风格标签
- **爆款潜力评估**：完播率、互动率、转发率预期
- **优化建议**：1-3 条具体可执行的改进建议

#### 4.3 Brainstorming 视角
你必须分析以下维度：
- **核心价值拆解**：该文案的核心传播价值是什么
- **创意方向探索**：2-3 种衍生创意方向
- **增量验证点**：可测试的优化实验

**输出文件**：`<输出目录>/<视频ID>_分析报告.md`

**输出格式**：
```markdown
# 视频文案综合分析报告（三维度）

## 一、TextContent Analysis 视角
[叙事结构、修辞手法、词库]

## 二、Viral-Abstract-Script 视角
[Viral-5D诊断、风格定位、优化建议]

## 三、Brainstorming 视角
[价值拆解、创意方向、验证点]
```

---

### 阶段 5: 结构化文字稿

**目标**：基于阶段 3 的文字稿，按照视频内容的叙事逻辑重新分段整理，输出格式清晰、层次分明的 `<视频ID>_结构化文字稿.md`。

**执行步骤**：
1. 读取阶段 3 生成的文字稿，以及阶段 4 分析报告中的叙事结构分析
2. 按照视频内容的自然叙事段落进行切分
3. 为每个段落添加简洁的小标题（`## 一、xxx`、`## 二、xxx` 格式）
4. 在段落内部按语义进行合理分行（每段不宜过长，3-5 句为宜）
5. 修正 ASR 错误的同时保留口语化风格
6. 对关键金句或重点内容使用**加粗**标注
7. 保存为 Markdown 文件

**输出文件**：`<输出目录>/<视频ID>_结构化文字稿.md`

**输出格式**：
```markdown
# <视频标题或ID> 结构化文字稿

## 一、<第一段小标题>

<分行后的段落文本，3-5 句一段>

<继续...>

## 二、<第二段小标题>

<分行后的段落文本>

...
```

**注意事项**：
- 小标题应简洁有力，概括该段核心内容
- 保留视频原始的口语表达风格，不要过度书面化
- 关键金句或亮点用**加粗**突出
- 每个段落之间用空行分隔，提高可读性

---

## 完成后输出

完成所有 5 个阶段后，向用户播报：

```
✅ 视频文案分析完成！

📁 输出目录: <用户指定的目录>

📄 生成文件:
  - <视频ID>.mp4              (原始视频)
  - <视频ID>.srt              (原始字幕)
  - <视频ID>_文字稿.md         (校正后纯文本文字稿)
  - <视频ID>_分析报告.md       (三维度分析报告)
  - <视频ID>_结构化文字稿.md   (按叙事逻辑分段的结构化文字稿)

🔗 快速打开:
  [文字稿](<文字稿路径>)
  [分析报告](<分析报告路径>)
  [结构化文字稿](<结构化文字稿路径>)
```

---

## 参考文件

| 文件 | 说明 | 状态 |
|------|------|------|
| [download_douyin.py](scripts/download_douyin.py) | 抖音视频下载脚本 | ✅ 可用 |
| [extract_subtitle_funasr.py](scripts/extract_subtitle_funasr.py) | 智能字幕提取（FunASR + RapidOCR） | ✅ 可用 |
| [check_environment.py](scripts/check_environment.py) | 环境依赖检测 | ✅ 可用 |
| [analysis-frameworks.md](references/analysis-frameworks.md) | 三个分析框架详解 | ✅ 参考 |
| [funasr-details.md](references/funasr-details.md) | FunASR 技术细节与故障排除 | ✅ 参考 |

<!-- 以下脚本暂未启用，需要浏览器 cookies 支持，目前因 macOS 钥匙串加密问题暂不可用 -->
<!-- | [fetch_bilibili_subtitle.py](scripts/fetch_bilibili_subtitle.py) | B站API字幕获取（需cookies） | ⏸️ 暂停 | -->
<!-- | [extract_subtitle.py](scripts/extract_subtitle.py) | Whisper 字幕提取（已被 FunASR 替代） | ⏸️ 暂停 | -->
<!-- | [transcribe_audio.py](scripts/transcribe_audio.py) | Whisper 音频转录（已被 FunASR 替代） | ⏸️ 暂停 | -->

---

## FunASR 技术细节与故障排除

模型配置、性能参考、常见问题排查请参考 [funasr-details.md](references/funasr-details.md)。
