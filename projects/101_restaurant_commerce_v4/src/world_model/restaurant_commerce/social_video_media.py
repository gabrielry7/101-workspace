"""Bounded local media operations. Only code constructs paths, flags and filters.

No model code, remote fetch, music lookup or speech model. The installed FFmpeg
build is an operator dependency; absent tools are a visible capability blocker.
"""

import hashlib
import io
import json
import math
import os
import shutil
import subprocess
import tempfile
import zipfile
from functools import lru_cache
from pathlib import Path

from fastapi import HTTPException
from PIL import Image, ImageOps

from .social_production import require
from .social_video_contracts import MAX_CLIP_BYTES, MAX_OUTPUT_BYTES, VERSION


def command(args, timeout=25):
    try:
        result = subprocess.run(
            args,
            check=True,
            capture_output=True,
            timeout=timeout,
            env={"PATH": os.defpath, "LC_ALL": "C"},
        )
        require(len(result.stdout) < 2 * 1024 * 1024, "media_probe_output_limit", 422)
        return result.stdout
    except FileNotFoundError:
        raise HTTPException(503, "video_tools_unavailable") from None
    except subprocess.TimeoutExpired:
        raise HTTPException(422, "media_processing_time_limit") from None
    except subprocess.CalledProcessError:
        raise HTTPException(422, "video_decode_failed_rerecord") from None


@lru_cache(maxsize=1)
def tools():
    encoder, probe = shutil.which("ffmpeg"), shutil.which("ffprobe")
    require(encoder and probe, "video_tools_unavailable", 503)
    version = command([encoder, "-version"], 5).decode().splitlines()[0]
    return encoder, probe, version


def base():
    return [
        tools()[0],
        "-nostdin",
        "-hide_banner",
        "-v",
        "error",
        "-y",
        "-threads",
        "1",
        "-filter_threads",
        "1",
        "-filter_complex_threads",
        "1",
        "-max_alloc",
        "134217728",
    ]


def input_flags(path):
    # Demux only actual MOV/MP4 containers; external references remain disabled.
    return [
        "-protocol_whitelist",
        "file,pipe",
        "-format_whitelist",
        "mov",
        "-enable_drefs",
        "0",
        "-use_absolute_path",
        "0",
        "-i",
        str(path),
    ]


def probe(path, *, source=True):
    try:
        return _probe(path, source=source)
    except (ValueError, KeyError, TypeError, OverflowError, ZeroDivisionError):
        raise HTTPException(422, "video_metadata_invalid_rerecord") from None


def _probe(path, *, source=True):
    data = json.loads(
        command(
            [
                tools()[1],
                "-v",
                "error",
                "-max_alloc",
                "134217728",
                "-protocol_whitelist",
                "file,pipe",
                "-format_whitelist",
                "mov",
                "-enable_drefs",
                "0",
                "-use_absolute_path",
                "0",
                "-show_streams",
                "-show_format",
                "-of",
                "json",
                str(path),
            ],
            12,
        )
    )
    streams = data.get("streams", [])
    videos = [s for s in streams if s.get("codec_type") == "video"]
    audios = [s for s in streams if s.get("codec_type") == "audio"]
    require(
        len(videos) == 1 and len(audios) <= 1 and len(streams) <= 3,
        "video_streams_unsupported",
        422,
    )
    v = videos[0]
    require(v.get("codec_name") in {"h264", "hevc", "mpeg4"}, "video_codec_unsupported", 422)
    duration = float(v.get("duration") or data["format"].get("duration", 0))
    width, height = int(v.get("width", 0)), int(v.get("height", 0))
    rotation = (
        int(
            float(
                next(
                    (s["rotation"] for s in v.get("side_data_list", []) if "rotation" in s),
                    v.get("tags", {}).get("rotate", 0),
                )
            )
        )
        % 360
    )
    require(rotation in {0, 90, 180, 270}, "video_rotation_unsupported", 422)
    if rotation in {90, 270}:
        width, height = height, width
    fps_text = v.get("avg_frame_rate", "0/1")
    n, d = fps_text.split("/")
    fps = float(n) / float(d) if float(d) else 0
    require(
        math.isfinite(duration) and 0.5 <= duration <= 30.1 and 0 < fps <= 61,
        "video_duration_or_framerate_limit",
        422,
    )
    require(width * height <= 16_777_216 and min(width, height) > 0, "video_resolution_limit", 422)
    transfer = v.get("color_transfer", "unknown")
    require(transfer not in {"smpte2084", "arib-std-b67"}, "video_hdr_record_in_sdr", 422)
    if source:
        require(height >= width, "video_record_vertically", 422)
        require(width >= 720 and height >= 1280, "video_record_higher_resolution", 422)
    return {
        "duration_ms": round(duration * 1000),
        "width": width,
        "height": height,
        "rotation": rotation,
        "fps": fps,
        "fps_native": fps_text,
        "frame_rate_policy": "normalize_to_30_on_render",
        "codec": v["codec_name"],
        "pixel_format": v.get("pix_fmt"),
        "color_transfer": transfer,
        "color_space": v.get("color_space", "unknown"),
        "has_audio": bool(audios),
        "audio_codec": audios[0].get("codec_name") if audios else None,
        "tool_version": tools()[2],
        "semantic_review": "human_required",
        "transcription": "not_requested_natural_sound_recipe",
    }


def intake(raw):
    require(0 < len(raw) <= MAX_CLIP_BYTES, "video_upload_limit", 413)
    with tempfile.TemporaryDirectory(prefix="101-video-intake-") as td:
        p = Path(td) / "source.mp4"
        p.write_bytes(raw)
        meta = probe(p)
        # Full bounded decode validates the complete clip, not just its first frame.
        command(
            base()
            + input_flags(p)
            + ["-map", "0:v:0", "-map", "0:a:0?", "-t", "30", "-f", "null", "-"],
            25,
        )
        analysis = Path(td) / "analysis.mp4"
        command(
            base()
            + input_flags(p)
            + [
                "-t",
                "5",
                "-map",
                "0:v:0",
                "-map",
                "0:a:0?",
                "-vf",
                "scale=360:640:force_original_aspect_ratio=decrease,pad=360:640:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=15",
                "-c:v",
                "libx264",
                "-threads",
                "1",
                "-preset",
                "ultrafast",
                "-crf",
                "28",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-b:a",
                "64k",
                "-movflags",
                "+faststart",
                "-map_metadata",
                "-1",
                "-fs",
                "3000000",
                str(analysis),
            ],
            20,
        )
        poster = Path(td) / "poster.jpg"
        command(
            base() + input_flags(analysis) + ["-frames:v", "1", "-update", "1", str(poster)], 10
        )
        return meta, analysis.read_bytes(), poster.read_bytes()


def encode(raws, timeline, metadata):
    """Validated integer time ranges/focal numbers only; no user filter strings."""
    with tempfile.TemporaryDirectory(prefix="101-video-render-") as td:
        td = Path(td)
        paths = []
        for i, (raw, clip, meta) in enumerate(zip(raws, timeline.clips, metadata, strict=True)):
            src, out = td / f"source-{i}.mp4", td / f"segment-{i}.mp4"
            src.write_bytes(raw)
            duration = (clip.source_out - clip.source_in) / 1000
            args = base() + ["-ss", str(clip.source_in / 1000)] + input_flags(src)
            natural = meta["has_audio"] and clip.audio_mode == "preserve_natural_sound"
            if not natural:
                args += ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo"]
            # Scale/crop after autorotation. Preserve wall-clock speed; generate no scenes.
            filters = (
                "scale=1080:1920:force_original_aspect_ratio=increase,"
                f"crop=1080:1920:(iw-1080)*{clip.focal_x:.6f}:(ih-1920)*{clip.focal_y:.6f},"
                "setsar=1,fps=30,format=yuv420p"
            )
            args += [
                "-t",
                str(duration),
                "-map",
                "0:v:0",
                "-map",
                "0:a:0" if natural else "1:a:0",
                "-vf",
                filters,
                "-af",
                "aresample=48000:async=1:first_pts=0,apad,alimiter=limit=0.95:level=false",
                "-c:v",
                "libx264",
                "-threads",
                "1",
                "-preset",
                "veryfast",
                "-crf",
                "23",
                "-c:a",
                "aac",
                "-ar",
                "48000",
                "-ac",
                "2",
                "-b:a",
                "128k",
                "-map_metadata",
                "-1",
                "-movflags",
                "+faststart",
                "-fs",
                "12000000",
                str(out),
            ]
            command(args, 35)
            paths.append(out)
        playlist = td / "segments.txt"
        playlist.write_text("".join(f"file '{p.name}'\n" for p in paths))
        final = td / "video.mp4"
        command(
            base()
            + [
                "-protocol_whitelist",
                "file,pipe",
                "-f",
                "concat",
                "-safe",
                "1",
                "-i",
                str(playlist),
                "-c",
                "copy",
                "-movflags",
                "+faststart",
                "-map_metadata",
                "-1",
                "-fs",
                str(MAX_OUTPUT_BYTES),
                str(final),
            ],
            15,
        )
        info = probe(final, source=False)
        expected = sum(c.source_out - c.source_in for c in timeline.clips)
        require(
            abs(info["duration_ms"] - expected) <= 150
            and info["width"] == 1080
            and info["height"] == 1920,
            "video_output_duration_or_dimensions",
            422,
        )
        # Decode the entire output. Narrative, crop and audio still need human review.
        command(base() + input_flags(final) + ["-f", "null", "-"], 25)
        preview, cover = td / "preview.mp4", td / "cover.jpg"
        command(
            base()
            + input_flags(final)
            + [
                "-vf",
                "scale=360:640",
                "-c:v",
                "libx264",
                "-threads",
                "1",
                "-preset",
                "ultrafast",
                "-crf",
                "27",
                "-c:a",
                "aac",
                "-b:a",
                "64k",
                "-movflags",
                "+faststart",
                "-fs",
                "5000000",
                str(preview),
            ],
            20,
        )
        command(base() + input_flags(final) + ["-frames:v", "1", "-update", "1", str(cover)], 10)
        with Image.open(cover) as im:
            poster = io.BytesIO()
            ImageOps.fit(im.convert("RGB"), (1080, 1350)).save(poster, "JPEG", quality=92)
        files = {
            "video.mp4": final.read_bytes(),
            "preview.mp4": preview.read_bytes(),
            "cover.jpg": cover.read_bytes(),
            "post.jpg": poster.getvalue(),
        }
        require(sum(map(len, files.values())) <= MAX_OUTPUT_BYTES, "video_output_size_limit", 422)
        report = {
            "renderer": VERSION,
            "tool_version": tools()[2],
            "technical": "passed",
            "width": 1080,
            "height": 1920,
            "duration_ms": info["duration_ms"],
            "fps": 30,
            "audio": "selected_natural_sound_or_explicit_mute",
            "transcription": "not_requested",
            "checks": ["full_decode", "duration", "dimensions", "source_bounds", "hashes"],
            "craft": "requires_complete_watch_and_listen",
            "performance": "unavailable",
            "files": {
                k: {"sha256": hashlib.sha256(v).hexdigest(), "bytes": len(v)}
                for k, v in files.items()
            },
        }
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_STORED) as z:
            for name, data in files.items():
                z.writestr(name, data)
        return buf.getvalue(), report


def unpack(data):
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        require(
            set(z.namelist()) == {"video.mp4", "preview.mp4", "cover.jpg", "post.jpg"},
            "video_checkpoint_invalid",
        )
        require(
            sum(i.file_size for i in z.infolist()) <= MAX_OUTPUT_BYTES, "video_checkpoint_limit"
        )
        return {name: z.read(name) for name in z.namelist()}
