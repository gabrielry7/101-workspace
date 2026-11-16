"""Bounded mono PCM extraction and actionable audio intake checks."""

import array
import hashlib
import math
import tempfile
import wave
from pathlib import Path

from .social_production import require
from .social_video_media import base, command, input_flags


def extract(raw):
    with tempfile.TemporaryDirectory(prefix="101-speech-") as td:
        src, wav, flac = (Path(td) / n for n in ("source.mp4", "audio.wav", "audio.flac"))
        src.write_bytes(raw)
        command(
            base()
            + input_flags(src)
            + [
                "-vn",
                "-map",
                "0:a:0",
                "-t",
                "30",
                "-ar",
                "16000",
                "-ac",
                "1",
                "-c:a",
                "pcm_s16le",
                str(wav),
            ],
            20,
        )
        with wave.open(str(wav)) as audio:
            samples = array.array("h", audio.readframes(audio.getnframes()))
        require(bool(samples), "speech_audio_missing_rerecord", 422)
        rms = math.sqrt(sum(v * v for v in samples) / len(samples)) / 32768
        clipped = sum(abs(v) >= 32700 for v in samples) / len(samples)
        require(rms >= 0.001, "speech_too_quiet_rerecord", 422)
        require(clipped < 0.03, "speech_clipped_rerecord", 422)
        command(base() + ["-i", str(wav), "-c:a", "flac", str(flac)], 15)
        data = flac.read_bytes()
        require(len(data) <= 2 * 1024 * 1024, "speech_audio_limit", 422)
        return data, {
            "sha256": hashlib.sha256(data).hexdigest(),
            "bytes": len(data),
            "sample_rate": 16000,
            "channels": 1,
            "rms": rms,
            "clipped_fraction": clipped,
            "intelligibility": "human_review_required",
        }
