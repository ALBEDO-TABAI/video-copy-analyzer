#!/usr/bin/env python3
"""
抖音视频下载脚本
支持从抖音分享链接提取并下载视频（无水印版本）

使用方法:
    python download_douyin.py <抖音链接> <输出路径>

示例:
    python download_douyin.py "https://v.douyin.com/xxxxx" ./video.mp4
    python download_douyin.py "https://www.douyin.com/video/xxxxx" ./video.mp4
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from html import unescape
from pathlib import Path
from typing import Iterable, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import unquote
from urllib.request import HTTPCookieProcessor, Request, build_opener


UA_MOBILE = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1"
)
UA_DESKTOP = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)
PLAY_HEADERS = {
    "User-Agent": UA_DESKTOP,
    "Referer": "https://www.douyin.com/",
    "Accept": "*/*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}


def is_douyin_url(url: str) -> bool:
    """检查是否为抖音链接"""
    douyin_patterns = [
        r"v\.douyin\.com",
        r"www\.douyin\.com",
        r"m\.douyin\.com",
        r"iesdouyin\.com",
        r"douyin\.com/video/",
        r"douyin\.com/jingxuan",
        r"douyin\.com/note/",
        r"douyin\.com/share/",
    ]
    return any(re.search(pattern, url) for pattern in douyin_patterns)


def extract_video_id(url: str) -> Optional[str]:
    """从抖音链接中提取视频ID"""
    patterns = [
        r"/video/(\d+)",
        r"/share/video/(\d+)",
        r"/note/(\d+)",
        r"modal_id=(\d+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def _opener():
    return build_opener(HTTPCookieProcessor())


def _request(opener, url: str, headers: Optional[dict] = None, timeout: int = 20):
    req = Request(url, headers=headers or {})
    return opener.open(req, timeout=timeout)


def _read_text(opener, url: str, headers: dict, timeout: int = 20) -> tuple[str, str]:
    with _request(opener, url, headers=headers, timeout=timeout) as resp:
        raw = resp.read()
        final = resp.geturl()
    charset = "utf-8"
    try:
        text = raw.decode(charset)
    except UnicodeDecodeError:
        text = raw.decode("utf-8", errors="replace")
    return final, text


def resolve_url(url: str) -> tuple[str, Optional[str]]:
    """Follow short links and return (final_url, aweme_id)."""
    aweme_id = extract_video_id(url)
    if aweme_id:
        return url, aweme_id

    opener = _opener()
    headers = {
        "User-Agent": UA_MOBILE,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9",
    }
    try:
        final, _html = _read_text(opener, url, headers=headers, timeout=15)
    except Exception as exc:
        print(f"✗ 解析短链接失败: {exc}")
        return url, None
    return final, extract_video_id(final)


def _json_candidates_from_html(html: str) -> list[dict]:
    patterns = [
        r'<script id="RENDER_DATA" type="application/json">([^<]+)</script>',
        r'<script[^>]+\bid="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>([^<]+)</script>',
        r"window\._ROUTER_DATA\s*=\s*(\{.+?\});?\s*</script>",
        r"window\._SSR_DATA\s*=\s*(\{.+?\});?\s*</script>",
        r"window\._SSR_HYDRATED_DATA\s*=\s*(\{.+?\});?\s*</script>",
    ]
    out: list[dict] = []
    for pattern in patterns:
        for raw in re.findall(pattern, html, re.DOTALL):
            data_str = unescape(raw.strip())
            if "%" in data_str:
                data_str = unquote(data_str)
            try:
                parsed = json.loads(data_str)
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict):
                out.append(parsed)
    return out


def _walk_play_urls(obj, acc: list[str], uri_acc: list[str], depth: int = 0) -> None:
    if depth > 12 or obj is None:
        return
    if isinstance(obj, dict):
        if "url_list" in obj and isinstance(obj["url_list"], list):
            for item in obj["url_list"]:
                if isinstance(item, str) and item.startswith("http"):
                    acc.append(item)
        uri = obj.get("uri")
        if isinstance(uri, str) and re.fullmatch(r"v[0-9a-z]{10,}", uri):
            uri_acc.append(uri)
        for key, value in obj.items():
            if key in {"play_addr", "play_addr_h264", "play_addr_265", "download_addr", "playAddr"}:
                _walk_play_urls(value, acc, uri_acc, depth + 1)
            elif isinstance(value, (dict, list)) and key in {
                "video",
                "aweme_detail",
                "videoInfoRes",
                "item_list",
                "loaderData",
                "__DEFAULT_SCOPE__",
                "app",
            }:
                _walk_play_urls(value, acc, uri_acc, depth + 1)
            elif isinstance(value, (dict, list)) and depth < 6:
                _walk_play_urls(value, acc, uri_acc, depth + 1)
    elif isinstance(obj, list):
        for item in obj[:40]:
            _walk_play_urls(item, acc, uri_acc, depth + 1)


def play_urls_from_uri(uri: str) -> list[str]:
    return [
        f"https://www.douyin.com/aweme/v1/play/?video_id={uri}&ratio=1080p&line=0",
        f"https://aweme.snssdk.com/aweme/v1/play/?video_id={uri}&ratio=720p&line=0",
    ]


def collect_media_urls(data: dict) -> list[str]:
    urls: list[str] = []
    uris: list[str] = []
    _walk_play_urls(data, urls, uris)
    cleaned: list[str] = []
    for url in urls:
        url = url.replace("playwm", "play").replace("\\u002F", "/")
        if "watermark=1" in url:
            continue
        cleaned.append(url)
    for uri in uris:
        cleaned.extend(play_urls_from_uri(uri))
    # preserve order, drop dups
    seen = set()
    out = []
    for url in cleaned:
        if url not in seen:
            seen.add(url)
            out.append(url)
    return out


def extract_from_html(html: str) -> list[str]:
    urls: list[str] = []
    for blob in _json_candidates_from_html(html):
        urls.extend(collect_media_urls(blob))
    if urls:
        return urls
    for match in re.findall(r'"uri"\s*:\s*"(v[0-9a-z]{10,})"', html):
        urls.extend(play_urls_from_uri(match))
    return list(dict.fromkeys(urls))


def try_html_strategies(url: str, aweme_id: Optional[str]) -> list[str]:
    opener = _opener()
    headers = {
        "User-Agent": UA_MOBILE,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9",
    }
    pages = []
    if aweme_id:
        pages.extend(
            [
                f"https://www.iesdouyin.com/share/video/{aweme_id}",
                f"https://m.douyin.com/share/video/{aweme_id}",
            ]
        )
    elif "iesdouyin.com" in url or "v.douyin.com" in url:
        pages.append(url)
    seen_pages = set()
    for page in pages:
        if page in seen_pages:
            continue
        seen_pages.add(page)
        try:
            _final, html = _read_text(opener, page, headers=headers, timeout=15)
        except Exception:
            continue
        if "byted_acrawler" in html or "__ac_signature" in html:
            continue
        urls = extract_from_html(html)
        if urls:
            return urls
    return []


def script_dir() -> Path:
    return Path(__file__).resolve().parent


def try_browser_extract(url: str) -> list[str]:
    helper = script_dir() / "douyin_browser.mjs"
    node = shutil.which("node")
    if not helper.exists() or not node:
        return []
    print("   使用本地浏览器通过风控并提取播放地址...")
    try:
        proc = subprocess.run(
            [node, str(helper), url],
            capture_output=True,
            text=True,
            timeout=90,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        print(f"   浏览器提取失败: {exc}")
        return []
    if proc.stderr:
        for line in proc.stderr.strip().splitlines()[-6:]:
            print(f"   {line}")
    if proc.returncode != 0:
        return []
    line = (proc.stdout or "").strip().splitlines()
    if not line:
        return []
    try:
        data = json.loads(line[-1])
    except json.JSONDecodeError:
        return []
    urls = list(data.get("play_urls") or [])
    uri = data.get("uri")
    if uri:
        urls.extend(play_urls_from_uri(uri))
    desc = data.get("desc")
    if desc:
        print(f"   标题: {desc}")
    return list(dict.fromkeys(urls))


def try_ytdlp(url: str, output_path: str) -> bool:
    ytdlp = shutil.which("yt-dlp")
    if not ytdlp:
        return False
    print("   尝试 yt-dlp ...")
    cmd = [
        ytdlp,
        "-f",
        "bv*+ba/b",
        "--merge-output-format",
        "mp4",
        "--no-warnings",
        "-o",
        output_path,
        url,
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    except (OSError, subprocess.TimeoutExpired) as exc:
        print(f"   yt-dlp 失败: {exc}")
        return False
    if proc.returncode == 0 and os.path.isfile(output_path) and os.path.getsize(output_path) > 1024:
        return True
    err = (proc.stderr or proc.stdout or "").strip().splitlines()
    if err:
        print(f"   yt-dlp: {err[-1]}")
    return False


def looks_like_video(path: str) -> bool:
    try:
        with open(path, "rb") as fh:
            head = fh.read(32)
    except OSError:
        return False
    return b"ftyp" in head or head.startswith(b"\x00\x00\x00")


def download_video(video_url: str, output_path: str) -> bool:
    """下载视频"""
    os.makedirs(os.path.dirname(os.path.abspath(output_path)) or ".", exist_ok=True)
    tmp_path = f"{output_path}.part"
    try:
        with _request(_opener(), video_url, headers=PLAY_HEADERS, timeout=90) as resp:
            status = getattr(resp, "status", 200)
            ctype = resp.headers.get("Content-Type", "")
            if status not in (200, 206):
                print(f"✗ 下载失败，状态码: {status}")
                return False
            if "text/html" in ctype or "application/json" in ctype:
                print(f"✗ 下载失败，返回的不是视频 ({ctype})")
                return False
            total_size = int(resp.headers.get("Content-Length") or 0)
            downloaded = 0
            last_pct = -1
            with open(tmp_path, "wb") as fh:
                while True:
                    chunk = resp.read(1024 * 64)
                    if not chunk:
                        break
                    fh.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        percent = int(downloaded * 100 / total_size)
                        if percent != last_pct and percent % 5 == 0:
                            last_pct = percent
                            print(
                                f"\r进度: {percent}% ({downloaded:,}/{total_size:,} bytes)",
                                end="",
                                flush=True,
                            )
        print()
        if not looks_like_video(tmp_path) or os.path.getsize(tmp_path) < 1024:
            print("✗ 下载内容不是有效视频")
            return False
        os.replace(tmp_path, output_path)
        return True
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        print(f"✗ 下载视频时出错: {exc}")
        return False
    finally:
        if os.path.exists(tmp_path) and not os.path.exists(output_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass


def download_first_working(urls: Iterable[str], output_path: str) -> bool:
    for index, video_url in enumerate(urls, 1):
        print(f"   候选地址 {index}: {video_url[:96]}...")
        if download_video(video_url, output_path):
            return True
    return False


def download_douyin_video(url: str, output_path: str) -> bool:
    """
    下载抖音视频的主函数

    Args:
        url: 抖音视频链接（支持短链接和长链接）
        output_path: 输出文件路径

    Returns:
        bool: 下载是否成功
    """
    print("🎬 开始下载抖音视频")
    print(f"   链接: {url}")
    print(f"   输出: {output_path}")
    print()

    print("步骤 1/4: 解析链接...")
    final_url, aweme_id = resolve_url(url)
    if aweme_id:
        print(f"✓ 视频 ID: {aweme_id}")
        watch_url = f"https://www.douyin.com/video/{aweme_id}"
    else:
        print("⚠ 未能直接解析视频 ID，将使用原始链接继续")
        watch_url = final_url

    print("\n步骤 2/4: 提取无水印播放地址...")
    video_urls = try_html_strategies(watch_url, aweme_id)
    source = "页面解析" if video_urls else ""
    if not video_urls:
        video_urls = try_browser_extract(watch_url)
        source = "浏览器" if video_urls else ""
    if video_urls:
        print(f"✓ 通过{source}获取到 {len(video_urls)} 个候选地址")

    if video_urls:
        print("\n步骤 3/4: 下载视频...")
        if download_first_working(video_urls, output_path):
            file_size = os.path.getsize(output_path)
            print(f"✓ 下载完成: {file_size:,} bytes")
            return True
        print("⚠ 候选地址下载失败，尝试 yt-dlp")

    print("\n步骤 3/4: 回退到 yt-dlp...")
    if try_ytdlp(watch_url, output_path):
        file_size = os.path.getsize(output_path)
        print(f"✓ yt-dlp 下载完成: {file_size:,} bytes")
        return True

    print("\n✗ 无法获取视频下载地址")
    print("  当前抖音网页接口需要真实浏览器会话才能通过风控。")
    print("  请确认已安装 Node.js，以及 Chrome / Edge / Chromium。")
    print("  也可设置环境变量 DOUYIN_BROWSER 指向浏览器可执行文件。")
    return False


def main():
    if len(sys.argv) < 3:
        print("用法: python download_douyin.py <抖音链接> <输出路径>")
        print("示例: python download_douyin.py 'https://v.douyin.com/xxxxx' ./video.mp4")
        sys.exit(1)

    url = sys.argv[1]
    output_path = sys.argv[2]

    if not is_douyin_url(url):
        print(f"✗ 不是有效的抖音链接: {url}")
        sys.exit(1)

    success = download_douyin_video(url, output_path)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
