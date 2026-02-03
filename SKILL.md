---
name: video-copy-analyzer
description: >
  视频文案分析一站式工具。下载在线视频（B站/YouTube等）、使用Whisper转录语音为文字稿、
  自动校正文稿、并进行三维度综合分析（TextContent/Viral/Brainstorming）。
  使用场景：当用户需要分析短视频文案、提取视频内容、学习爆款文案技巧时。
  关键词：视频分析、文案分析、语音转文字、Whisper、爆款分析、视频下载
---

# 视频文案分析工具

一站式视频内容提取与文案分析，支持 B站、YouTube 等平台。

## 首次使用设置

首次使用时，询问用户：

> "请设置默认工作目录（用于保存下载的视频和分析报告）：
> 
> A. 使用默认目录：`~/video-analysis/`
> B. 每次手动指定目录
> C. 指定一个固定目录：[请输入路径]"

保存用户选择供后续使用。

## 依赖环境检测

运行前检测以下依赖，如缺失则提示安装：

```bash
# 1. yt-dlp
yt-dlp --version

# 2. FFmpeg
ffmpeg -version

# 3. Python 依赖
python -c "import pysrt; from dotenv import load_dotenv; import whisper; print('OK')"
```

**安装命令（如缺失）**：
```bash
pip install yt-dlp pysrt python-dotenv openai-whisper
```

## 工作流程（4 阶段）

### 阶段 1: 下载视频

1. 获取用户视频 URL 和输出目录
2. 使用 yt-dlp 下载视频：
   ```bash
   yt-dlp -f "bestvideo[height<=1080]+bestaudio/best[height<=1080]" \
     --merge-output-format mp4 \
     -o "<output_dir>/%(id)s.%(ext)s" \
     "<video_url>"
   ```
3. 记录视频文件路径

### 阶段 2: Whisper 转录

使用 scripts/transcribe_audio.py 进行语音转录：

```bash
python scripts/transcribe_audio.py <video_path> <output_srt> [model] [language] [device]
```

参数说明：
- model: tiny/base/small/medium/large（默认 medium）
- language: zh/en/auto（默认 auto）
- device: cuda/cpu（默认 cuda，不可用时自动回退）

输出：SRT 格式字幕文件

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

- [transcribe_audio.py](scripts/transcribe_audio.py): Whisper 转录脚本
- [analysis-frameworks.md](references/analysis-frameworks.md): 三个分析框架详解
