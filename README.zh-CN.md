# 视频文案分析工具

[English](README.md) | 中文文档

> 🎬 一站式视频内容提取与文案分析工具。下载视频、Whisper 语音转录、三维度 AI 框架分析文案。

## ✨ 功能特性

| 阶段 | 功能 | 说明 |
|------|------|------|
| 1️⃣ | **视频下载** | 使用 yt-dlp 下载 B站/YouTube 视频 |
| 2️⃣ | **Whisper 转录** | 使用 OpenAI Whisper 语音转文字 |
| 3️⃣ | **智能校正** | 基于上下文自动校正转录错误 |
| 4️⃣ | **三维度分析** | TextContent + Viral + Brainstorming |

## 🚀 快速开始

### 环境要求

```bash
# 安装 Python 依赖
pip install yt-dlp pysrt python-dotenv openai-whisper

# FFmpeg 必须安装并添加到 PATH
ffmpeg -version
```

### 使用方法

这是一个 **Claude Skill**，专为 AI 代理设计。将其安装到 `.agent/skills/` 目录：

```bash
git clone https://github.com/YOUR_USERNAME/video-copy-analyzer.git .agent/skills/video-copy-analyzer
```

然后与 Claude 对话使用：

> "分析这个视频：https://www.bilibili.com/video/BV1xxxxx"

## 📊 三维度分析框架

### 1. TextContent Analysis（文本内容分析）
- 叙事结构拆解
- 修辞手法识别
- 关键词提取

### 2. Viral-Abstract-Script（病毒传播框架）
- **Viral-5D 诊断**：Hook / Emotion / 爆点 / CTA / 社交货币
- 风格定位
- 优化建议

### 3. Brainstorming（头脑风暴框架）
- 核心价值拆解
- 2-3 种创意方向探索
- 增量验证点

## 📁 项目结构

```
video-copy-analyzer/
├── SKILL.md                    # 核心技能说明
├── scripts/
│   ├── transcribe_audio.py     # Whisper 转录脚本
│   └── check_environment.py    # 环境检测脚本
└── references/
    └── analysis-frameworks.md  # 分析框架详解
```

## 🔧 配置说明

首次使用时，skill 会引导你设置默认输出目录：

- **选项 A**：使用默认目录 `~/video-analysis/`
- **选项 B**：每次手动指定
- **选项 C**：设置一个固定的自定义目录

## 📄 输出文件

分析完成后，你将获得：

| 文件 | 内容 |
|------|------|
| `{视频ID}.mp4` | 原始视频 |
| `{视频ID}.srt` | 原始字幕 |
| `{视频ID}_文字稿.md` | 校正后文字稿 |
| `{视频ID}_分析报告.md` | 三维度分析报告 |

## 🎯 推荐环境

- **Antigravity** + Gemini 3 Pro
- **Cursor** + Claude 4.5 Opus

## 📝 许可证

MIT License
