"""Delivery from retained narration: embedded MP4 or separate post-production assets."""

import hashlib
import io
import json
import math
import os
import shutil
import subprocess
import tempfile
import time
import wave
import zipfile
from pathlib import Path

from .errors import StoriesError, require
from .speech import audio_record
from .video import encode


def export(
    api, revision, media, narration, output_path, slide_seconds, pause_seconds, delivery, timeout_seconds
):
    require(delivery in {"embedded", "separate"}, "Choose embedded MP4 or separate ZIP delivery.")
    require(
        narration["state"] == "succeeded", "Narration must complete before export.", "narration_incomplete"
    )
    require(
        narration["revision_id"] == revision["id"] and narration["source_sha256"] == revision["sha256"],
        "Narration belongs to a different revision; explicitly generate/reuse narration for this revision.",
        "stale_narration",
    )
    require(
        type(pause_seconds) in (int, float) and math.isfinite(pause_seconds) and 0 <= pause_seconds <= 60,
        "pause_seconds must be between 0 and 60.",
    )
    require(
        type(timeout_seconds) in (int, float) and 1 <= timeout_seconds <= 900,
        "timeout_seconds must be 1–900.",
    )
    path = Path(output_path).expanduser().resolve()
    require(not path.exists(), "Output already exists; choose a new destination.", "output_exists")
    require(path.parent.is_dir(), "Output parent directory must exist.")
    require(
        path.suffix.lower() == (".mp4" if delivery == "embedded" else ".zip"),
        "Output extension must match delivery (.mp4 or .zip).",
    )
    deadline = time.monotonic() + timeout_seconds
    ffmpeg, ffprobe = shutil.which("ffmpeg"), shutil.which("ffprobe")
    require(
        ffmpeg and ffprobe,
        "Install ffmpeg and ffprobe for narrated video export.",
        "video_dependency_missing",
    )

    def run(args):
        remaining = deadline - time.monotonic()
        require(remaining > 0, "Narrated export timed out.", "export_timeout")
        try:
            p = subprocess.run(args, capture_output=True, timeout=remaining)
        except subprocess.TimeoutExpired:
            raise StoriesError("export_timeout", "Narrated export timed out.") from None
        require(p.returncode == 0, "Narrated video encoding/verification failed.", "video_export_failed")
        return p.stdout

    with api.store.transaction() as db:
        pairs = [audio_record(db, c["audio_id"]) for c in narration["clips"]]
    require(all(pairs), "Narration audio is missing.", "missing_asset")
    minimum = [math.ceil((m["samples"] + round(pause_seconds * 24000)) / 800) for m, _ in pairs]
    frames = minimum
    if slide_seconds is not None:
        require(
            isinstance(slide_seconds, list) and len(slide_seconds) == len(pairs),
            "Supply one duration per slide.",
        )
        frames = []
        for duration, needed in zip(slide_seconds, minimum):
            require(
                type(duration) in (int, float) and math.isfinite(duration) and duration > 0,
                "Durations must be positive numbers.",
            )
            f = round(duration * 30)
            require(abs(f / 30 - duration) < 1e-7, "Durations must align to 30 fps.")
            require(
                f >= needed,
                "Fixed slide duration would truncate narration or its requested pause.",
                "timing_conflict",
            )
            frames.append(f)
    key = hashlib.sha256(
        json.dumps(
            [revision.get("delivery_sha256", revision["sha256"]), narration["id"], frames, pause_seconds],
            sort_keys=True,
        ).encode()
    ).hexdigest()
    with api.store.transaction() as db:
        cached = db.execute("SELECT data,video,audio FROM narration_renders WHERE id=?", (key,)).fetchone()
    with tempfile.TemporaryDirectory(prefix=".stories-narrated-", dir=path.parent) as folder:
        root = Path(folder)
        silent, track = root / "video.mp4", root / "narration.wav"
        if cached:
            plan = json.loads(cached[0])
            silent.write_bytes(cached[1])
            track.write_bytes(cached[2])
            require(
                hashlib.sha256(cached[1]).hexdigest() == plan["video_sha256"]
                and hashlib.sha256(cached[2]).hexdigest() == plan["audio_sha256"],
                "Retained delivery is corrupt.",
                "invalid_media",
            )
        else:
            duration = [f / 30 for f in frames]
            result = encode(revision, media, str(silent), duration, min(900, deadline - time.monotonic()))
            with wave.open(str(track), "wb") as out:
                out.setparams((1, 2, 24000, 0, "NONE", "not compressed"))
                for f, (meta, data) in zip(frames, pairs):
                    with wave.open(io.BytesIO(data), "rb") as audio:
                        pcm = audio.readframes(audio.getnframes())
                    out.writeframesraw(pcm)
                    remaining = f * 800 - meta["samples"]
                    while remaining:
                        count = min(remaining, 24000)
                        out.writeframesraw(b"\0" * (count * 2))
                        remaining -= count
            plan = {
                k: v
                for k, v in result.items()
                if k not in {"path", "status", "sha256", "size_bytes", "audio", "limitations"}
            }
            plan.update(
                narration_id=narration["id"],
                settings=narration["settings"],
                notes=narration["notes"],
                notes_origin=narration["notes_origin"],
                script_id=narration.get("script_id"),
                script_sha256=narration.get("script_sha256"),
                pause_seconds=pause_seconds,
                pacing="measured_audio" if slide_seconds is None else "explicit",
                ai_generated_voice=True,
                video_sha256=hashlib.sha256(silent.read_bytes()).hexdigest(),
                audio_sha256=hashlib.sha256(track.read_bytes()).hexdigest(),
            )
            for entry, (meta, _) in zip(plan["timeline"], pairs):
                entry.update(
                    audio_id=meta["id"],
                    audio_sha256=meta["sha256"],
                    speech_samples=meta["samples"],
                    speech_seconds=meta["duration_seconds"],
                    audio_start_sample=entry["start_frame"] * 800,
                    padding_samples=entry["frames"] * 800 - meta["samples"],
                )
            with api.store.transaction() as db:
                db.execute(
                    "INSERT OR IGNORE INTO narration_renders VALUES (?,?,?,?)",
                    (key, json.dumps(plan), silent.read_bytes(), track.read_bytes()),
                )
        target = root / ("delivery.mp4" if delivery == "embedded" else "delivery.zip")
        if delivery == "embedded":
            run(
                [
                    ffmpeg,
                    "-nostdin",
                    "-v",
                    "error",
                    "-i",
                    str(silent),
                    "-i",
                    str(track),
                    "-map",
                    "0:v:0",
                    "-map",
                    "1:a:0",
                    "-c:v",
                    "copy",
                    "-c:a",
                    "aac",
                    "-b:a",
                    "192k",
                    "-metadata",
                    "comment=AI-generated narration",
                    "-movflags",
                    "+faststart",
                    str(target),
                ]
            )
            probe = json.loads(
                run([ffprobe, "-v", "error", "-show_streams", "-show_format", "-of", "json", str(target)])
            )
            videos = [s for s in probe["streams"] if s["codec_type"] == "video"]
            audios = [s for s in probe["streams"] if s["codec_type"] == "audio"]
            require(
                len(videos) == len(audios) == 1
                and int(videos[0]["nb_frames"]) == sum(frames)
                and abs(float(audios[0]["duration"]) - sum(frames) / 30) < 0.05,
                "Encoded audio/video does not match the retained timeline.",
                "video_verification_failed",
            )
            run([ffmpeg, "-nostdin", "-v", "error", "-xerror", "-i", str(target), "-f", "null", "-"])
        else:
            with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_STORED) as z:
                for name, data in [
                    ("video.mp4", silent.read_bytes()),
                    ("narration.wav", track.read_bytes()),
                    ("manifest.json", json.dumps(plan, indent=2).encode()),
                    (
                        "README.txt",
                        b"AI-generated narration. Video is silent. Align narration.wav at time zero. Slide WAVs are unpadded originals; manifest.json gives their exact sample/frame positions. Both delivery modes use the same retained audio and timeline.\n",
                    ),
                ]:
                    z.writestr(zipfile.ZipInfo(name), data)
                for i, (_, data) in enumerate(pairs):
                    z.writestr(zipfile.ZipInfo(f"slides/slide-{i + 1:03}.wav"), data)
            with zipfile.ZipFile(target) as z:
                require(z.testzip() is None, "Package integrity check failed.", "video_verification_failed")
        require(time.monotonic() < deadline, "Narrated export timed out.", "export_timeout")
        result = {
            "status": "succeeded",
            "path": str(path),
            "format": "mp4" if delivery == "embedded" else "zip",
            "mime_type": "video/mp4" if delivery == "embedded" else "application/zip",
            "delivery": delivery,
            "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
            "size_bytes": target.stat().st_size,
            "plan_id": key,
            "plan": plan,
            "duration_seconds": sum(frames) / 30,
            "audio": "embedded" if delivery == "embedded" else "separate",
            "checks": {
                "audio_timing": "passed",
                "decode": "passed" if delivery == "embedded" else "retained_silent_video",
                "package": "passed" if delivery == "separate" else "not_applicable",
                "visual": "not_performed",
                "semantic": "not_performed",
            },
            "limitations": [
                "AI-generated narration. Listen before delivery; generation does not verify spoken fidelity.",
                "Static slides only; embedded clips and animation remain unsupported.",
            ],
        }
        try:
            os.link(target, path)
        except FileExistsError:
            raise StoriesError("output_exists", "Output already exists; choose a new destination.") from None
    return result
