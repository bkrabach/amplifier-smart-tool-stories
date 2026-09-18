"""Check the actual encoded timeline, not merely the existence of an MP4."""

import json
import shutil
import subprocess

import pytest

from amplifier_smart_tool_stories import Stories, StoriesError

HTML = """<html><head><style>
html,body{margin:0}.slide{width:1280px;height:720px;box-sizing:border-box;page-break-after:always}
.slide:last-child{page-break-after:auto}
</style></head><body><section class="slide" style="background:#ff0000">One</section>
<section class="slide" style="background:#0000ff">Two</section></body></html>"""


def setup(tmp_path, html=HTML):
    api = Stories(tmp_path / "store")
    r = api.create_story("Video test", html, "create")
    return api, r["story_id"], r["revision_id"]


def test_real_video_timeline_and_retained_provenance(tmp_path):
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        pytest.skip("ffmpeg and ffprobe are optional video prerequisites")
    api, sid, rid = setup(tmp_path)
    out = tmp_path / "deck.mp4"
    result = api.export_video(sid, rid, str(out), [0.5, 0.7])
    assert result["duration_seconds"] == 1.2
    assert result["timeline"][1]["start_frame"] == 15
    assert result["audio"] == "none"
    # Decode exactly the two frames straddling the cut, downsampled for color identification.
    for frame, channel in [(14, 0), (15, 2), (35, 2)]:
        pixels = subprocess.check_output(
            [
                "ffmpeg",
                "-v",
                "error",
                "-i",
                str(out),
                "-vf",
                f"select=eq(n\\,{frame}),scale=1:1",
                "-frames:v",
                "1",
                "-f",
                "rawvideo",
                "-pix_fmt",
                "rgb24",
                "-",
            ]
        )
        assert len(pixels) == 3 and pixels[channel] > 220
        assert all(v < 30 for i, v in enumerate(pixels) if i != channel)
    events = api.read_changes(sid)["changes"]
    retained = next(e for e in events if e["kind"] == "video_exported")
    assert retained["timeline"] == result["timeline"]
    assert retained["revision_id"] == rid
    before = out.read_bytes()
    with pytest.raises(StoriesError, match="already exists"):
        api.export_video(sid, rid, str(out), [0.5, 0.7])
    assert out.read_bytes() == before
    assert not list(tmp_path.glob(".stories-video-*"))


@pytest.mark.parametrize("durations", [[1], [True, 1], [0, 1], [float("nan"), 1], [0.01, 1]])
def test_invalid_pacing_fails_without_output(tmp_path, durations):
    api, sid, rid = setup(tmp_path)
    with pytest.raises(StoriesError):
        api.export_video(sid, rid, str(tmp_path / "deck.mp4"), durations)
    assert not (tmp_path / "deck.mp4").exists()


def test_clips_are_not_silently_flattened(tmp_path):
    api, sid, rid = setup(tmp_path, HTML.replace("</section>", "<video></video></section>", 1))
    with pytest.raises(StoriesError, match="Clip playback"):
        api.export_video(sid, rid, str(tmp_path / "deck.mp4"), [1, 1])


def test_missing_encoder_is_actionable(tmp_path, monkeypatch):
    api, sid, rid = setup(tmp_path)
    monkeypatch.setattr("amplifier_smart_tool_stories.video.shutil.which", lambda name: None)
    with pytest.raises(StoriesError) as exc:
        api.export_video(sid, rid, str(tmp_path / "deck.mp4"), [1, 1])
    assert exc.value.code == "video_dependency_missing"
    assert "brew install ffmpeg" in exc.value.remedy


def test_cli_video_help_is_provider_free():
    import sys

    p = subprocess.run(
        [sys.executable, "-m", "amplifier_smart_tool_stories", "export-video", "--help"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "slide_seconds" in p.stdout and "No TTS" in p.stdout
    from amplifier_smart_tool_stories.help import example

    assert isinstance(json.loads(json.dumps(example("export_video")))["slide_seconds"], list)


@pytest.mark.parametrize("failure", ["timeout", "interrupt", "encoder"])
def test_encoder_failure_leaves_no_partial_output(tmp_path, monkeypatch, failure):
    api, sid, rid = setup(tmp_path)
    monkeypatch.setattr("amplifier_smart_tool_stories.video.shutil.which", lambda name: name)

    def fail(args, **kwargs):
        if failure == "timeout":
            raise subprocess.TimeoutExpired(args, 1)
        if failure == "interrupt":
            raise KeyboardInterrupt()
        return subprocess.CompletedProcess(args, 1, b"", b"encoder unavailable")

    monkeypatch.setattr("amplifier_smart_tool_stories.video.subprocess.run", fail)
    with pytest.raises(KeyboardInterrupt if failure == "interrupt" else StoriesError):
        api.export_video(sid, rid, str(tmp_path / "deck.mp4"), [1, 1])
    assert not (tmp_path / "deck.mp4").exists()
    assert not list(tmp_path.glob(".stories-video-*"))
    assert not any(e["kind"] == "video_exported" for e in api.read_changes(sid)["changes"])


def test_animation_is_not_silently_frozen(tmp_path):
    html = HTML.replace(".slide{", ".slide{animation:spin 2s;")
    api, sid, rid = setup(tmp_path, html)
    with pytest.raises(StoriesError, match="CSS animation"):
        api.export_video(sid, rid, str(tmp_path / "deck.mp4"), [1, 1])
