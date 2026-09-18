"""Bounded local, silent slide encoding; no speech, browser, network or model use."""

import asyncio
import base64
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from .artifacts import parse_html
from .errors import StoriesError, require
from .media import bindings, portable_markup
from .quality import render


def encode(revision, media, output_path, slide_seconds, timeout_seconds):
    path = Path(output_path).expanduser().resolve()
    require(not path.exists(), "Output already exists; choose a new destination.", "output_exists")
    require(path.parent.is_dir(), "Output parent directory must exist.")
    require(path.suffix.lower() == ".mp4", "Choose an .mp4 output path.")
    require(
        type(timeout_seconds) in (int, float) and 1 <= timeout_seconds <= 900,
        "timeout_seconds must be between 1 and 900.",
    )
    require(revision.get("kind") != "document", "Video export requires a presentation.", "unsupported_format")
    soup = parse_html(revision["html"])
    slides = soup.select(".slide")
    require(slides, "Video export requires .slide elements.")
    require(
        not soup.select("video,audio,track"),
        "Clip playback is not supported by silent slide export; use HTML/ZIP for this revision.",
        "unsupported_media",
    )
    portable_markup(revision["html"])
    css = (
        "\n".join(n.get_text() for n in soup.select("style"))
        + "\n"
        + "\n".join(n.get("style", "") for n in soup.find_all(True))
    )
    require(
        not re.search(
            r"(?:^|[;{])\s*(?:-webkit-)?animation(?:-[\w-]+)?\s*:|@(?:-webkit-)?keyframes", css, re.I
        ),
        "CSS animation is unsupported in static video export.",
        "unsupported_media",
    )
    used, _ = bindings(revision["html"], revision.get("assets", []), strict=True)
    assets = [a for a in revision.get("assets", []) if a["id"] in used]
    require(
        all(a["mime_type"].startswith("image/") and a.get("frames", 1) == 1 for a in assets),
        "Silent slide export supports static images only, not animated media.",
        "unsupported_media",
    )
    require(
        isinstance(slide_seconds, list) and len(slide_seconds) == len(slides),
        "Supply one explicit duration in seconds for each slide.",
    )
    frames = []
    for seconds in slide_seconds:
        require(
            type(seconds) in (int, float) and math.isfinite(seconds) and seconds > 0,
            "Slide durations must be finite positive numbers.",
        )
        count = round(seconds * 30)
        require(
            count >= 1 and abs(count / 30 - seconds) < 1e-7,
            "Durations must be whole frames at 30 fps (for example 5 or 5.1 seconds).",
        )
        frames.append(count)
    ffmpeg, ffprobe = shutil.which("ffmpeg"), shutil.which("ffprobe")
    if not ffmpeg or not ffprobe:
        raise StoriesError(
            "video_dependency_missing",
            "Video export requires ffmpeg and ffprobe on PATH.",
            "Install ffmpeg (macOS: brew install ffmpeg), then retry. No model or TTS is needed.",
        )
    deadline = time.monotonic() + timeout_seconds

    def run(args):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise StoriesError("export_timeout", "Video export exceeded its time allowance.")
        try:
            result = subprocess.run(args, capture_output=True, timeout=remaining, check=False)
        except subprocess.TimeoutExpired:
            raise StoriesError("export_timeout", "Video export exceeded its time allowance.") from None
        if result.returncode:
            raise StoriesError(
                "video_export_failed",
                result.stderr.decode(errors="replace")[-2000:],
                "Check ffmpeg codec support and the slide layout. No finished output was written.",
            )
        return result.stdout

    render_soup = parse_html(revision["html"])
    for note in render_soup.select(".notes,[data-speaker-notes]"):
        note.decompose()
    rendered = asyncio.run(render(str(render_soup), min(40, timeout_seconds), include_pdf=True, media=media))
    require(
        not rendered["findings"] and rendered["page_count"] == len(slides),
        "Slide layout must fit one page per slide: " + "; ".join(rendered["findings"]),
        "export_review_failed",
    )
    import pypdfium2 as pdfium

    timeline, start = [], 0
    # Temporary work lives beside the target, permitting an atomic no-overwrite final link.
    with tempfile.TemporaryDirectory(prefix=".stories-video-", dir=path.parent) as folder:
        root = Path(folder)
        pdf = pdfium.PdfDocument(base64.b64decode(rendered["pdf"]))
        try:
            for i, page in enumerate(pdf):
                bitmap = page.render(scale=1280 / page.get_width())
                try:
                    image = bitmap.to_pil().convert("RGB")
                    require(image.size == (1280, 720), "Video slides must render at 16:9.")
                    image.save(root / f"slide-{i}.png")
                finally:
                    bitmap.close()
                    page.close()
                timeline.append(
                    {
                        "slide": i + 1,
                        "start_frame": start,
                        "frames": frames[i],
                        "duration_seconds": frames[i] / 30,
                        "notes": [
                            n.get_text(" ", strip=True)
                            for n in slides[i].select(".notes,[data-speaker-notes]")
                        ],
                        "frame_sha256": hashlib.sha256((root / f"slide-{i}.png").read_bytes()).hexdigest(),
                    }
                )
                start += frames[i]
        finally:
            pdf.close()
        entries = [
            f"file slide-{i}.png\noption framerate 30\nduration {f / 30:.9f}\n" for i, f in enumerate(frames)
        ]
        entries.append(f"file slide-{len(frames) - 1}.png\noption framerate 30\n")
        (root / "frames.txt").write_text("".join(entries))
        encoded = root / "output.mp4"
        run(
            [
                ffmpeg,
                "-nostdin",
                "-v",
                "error",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(root / "frames.txt"),
                "-an",
                "-c:v",
                "libx264",
                "-preset",
                "medium",
                "-tune",
                "stillimage",
                "-crf",
                "18",
                "-pix_fmt",
                "yuv420p",
                "-vf",
                "fps=30",
                "-fps_mode",
                "cfr",
                "-frames:v",
                str(start),
                "-movflags",
                "+faststart",
                str(encoded),
            ]
        )
        probe = json.loads(
            run([ffprobe, "-v", "error", "-show_streams", "-show_format", "-of", "json", str(encoded)])
        )
        streams = probe["streams"]
        require(
            len(streams) == 1 and streams[0]["codec_type"] == "video",
            "Unexpected audio or stream in silent output.",
            "video_verification_failed",
        )
        v = streams[0]
        require(
            v["codec_name"] == "h264"
            and v["width"] == 1280
            and v["height"] == 720
            and int(v["nb_frames"]) == start
            and abs(float(probe["format"]["duration"]) - start / 30) < 0.04,
            "Encoded video does not match its timing plan.",
            "video_verification_failed",
        )
        run([ffmpeg, "-nostdin", "-v", "error", "-xerror", "-i", str(encoded), "-f", "null", "-"])
        result = {
            "status": "succeeded",
            "path": str(path),
            "format": "mp4",
            "mime_type": "video/mp4",
            "revision_id": revision["id"],
            "source_sha256": revision["sha256"],
            "delivery_sha256": revision.get("delivery_sha256", revision["sha256"]),
            "sha256": hashlib.sha256(encoded.read_bytes()).hexdigest(),
            "size_bytes": encoded.stat().st_size,
            "width": 1280,
            "height": 720,
            "fps": 30,
            "duration_seconds": start / 30,
            "audio": "none",
            "pacing": "explicit",
            "transitions": "cut",
            "timeline": timeline,
            "assets": assets,
            "checks": {
                "decode": "passed",
                "timing": "passed",
                "audio_absent": "passed",
                "layout": "passed",
                "visual": "not_performed",
                "semantic": "not_performed",
            },
            "limitations": [
                "Static rendered slides; no animation, clip playback, narration or TTS.",
                "Encoded output does not inherit model review or human acceptance.",
            ],
        }
        try:
            os.link(encoded, path)
        except FileExistsError:
            raise StoriesError("output_exists", "Output already exists; choose a new destination.") from None
        return result
