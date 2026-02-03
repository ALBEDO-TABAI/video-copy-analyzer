# Video Copy Analyzer

[中文文档](README.zh-CN.md) | English

<div align="center">

**🤖 Claude Skill** | AI-Powered Video Analysis

[![Claude 4.5 Opus](https://img.shields.io/badge/Tested%20on-Claude%204.5%20Opus-blue)](https://claude.ai)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

</div>

> 🎬 One-stop video content extraction and copywriting analysis tool. Download videos, transcribe with Whisper, and analyze scripts using three AI frameworks.

## ✨ Features

| Stage | Function | Description |
|-------|----------|-------------|
| 1️⃣ | **Video Download** | Download from Bilibili/YouTube using yt-dlp |
| 2️⃣ | **Whisper Transcription** | Speech-to-text using OpenAI Whisper |
| 3️⃣ | **Smart Correction** | Context-based auto-correction of transcription errors |
| 4️⃣ | **Three-Dimensional Analysis** | TextContent + Viral + Brainstorming |

## 🚀 Quick Start

### Prerequisites

```bash
# Install dependencies
pip install yt-dlp pysrt python-dotenv openai-whisper

# FFmpeg must be installed and in PATH
ffmpeg -version
```

### Usage

This is a **Claude Skill** designed for AI agents. Install it in your `.agent/skills/` directory:

```bash
git clone https://github.com/YOUR_USERNAME/video-copy-analyzer.git .agent/skills/video-copy-analyzer
```

Then use it with Claude:

> "Analyze this video: https://www.bilibili.com/video/BV1xxxxx"

## 📊 Three-Dimensional Analysis Framework

### 1. TextContent Analysis
- Narrative structure breakdown
- Rhetorical device identification
- Keyword extraction

### 2. Viral-Abstract-Script Framework
- **Viral-5D Diagnosis**: Hook / Emotion / Peaks / CTA / Social Currency
- Style positioning
- Optimization suggestions

### 3. Brainstorming Framework
- Core value decomposition
- 2-3 creative direction exploration
- Incremental verification points

## 📁 Project Structure

```
video-copy-analyzer/
├── SKILL.md                    # Core skill instructions
├── scripts/
│   ├── transcribe_audio.py     # Whisper transcription script
│   └── check_environment.py    # Environment verification
└── references/
    └── analysis-frameworks.md  # Analysis framework details
```

## 🔧 Configuration

On first use, the skill will prompt you to set a default output directory:

- **Option A**: Use default `~/video-analysis/`
- **Option B**: Specify each time
- **Option C**: Set a fixed custom directory

## 📄 Output Files

After analysis, you'll receive:

| File | Content |
|------|---------|
| `{video_id}.mp4` | Original video |
| `{video_id}.srt` | Raw subtitles |
| `{video_id}_transcript.md` | Corrected transcript |
| `{video_id}_analysis.md` | Three-dimensional analysis report |

## 🎯 Supported Environments

This is a **Claude Skill** that works with AI coding assistants:

| Environment | Model | Status |
|-------------|-------|--------|
| **Antigravity** | Gemini 3 Pro | ✅ Supported |
| **Cursor** | Claude 4.5 Opus | ✅ **Tested & Recommended** |
| **Claude Code** | Claude 4.5 Opus | ✅ Supported |
| **Windsurf** | Any Claude model | ✅ Supported |

> 💡 **Best Performance**: Tested with **Claude 4.5 Opus**, achieving optimal results in transcription correction and three-dimensional analysis.

## 📝 License

MIT License
