"""Deterministic, source-timed subtitle layout and portable text exports."""
# ruff: noqa: E501 -- ASS format/style lines are a literal renderer contract.

from .social_design import font, font_record, glyphs
from .social_production import require


def layout(words, clip, size=48, *, granularity="words"):
    require(
        words and words[0]["start"] >= clip.source_in and words[-1]["end"] <= clip.source_out,
        "speech_trim_would_remove_words",
        422,
    )
    cues, group = [], []
    require(size in {40, 48, 56}, "subtitle_size_invalid", 422)
    face = font(size)
    allowed = glyphs()

    def lines(items):
        result, line = [], ""
        literal_items = (
            items
            if granularity == "words"
            else [{"text": token} for item in items for token in item["text"].split()]
        )
        for w in literal_items:
            text = w["text"]
            require(
                all(ord(c) in allowed and c not in "{}\\<>" for c in text),
                "subtitle_unsupported_character",
                422,
            )
            candidate = (line + " " + text).strip()
            if face.getlength(candidate) > 864:
                if line:
                    result.append(line)
                line = text
                require(face.getlength(line) <= 864, "subtitle_text_overflow", 422)
            else:
                line = candidate
        if line:
            result.append(line)
        return result

    def emit():
        require(len(cues) < 80, "subtitle_cue_limit", 422)
        content = lines(group)
        require(len(content) <= 2, "subtitle_text_overflow", 422)
        start = group[0]["start"] - clip.source_in + clip.timeline_start
        end = group[-1]["end"] - clip.source_in + clip.timeline_start
        require(end - start >= 80, "subtitle_timing_too_short", 422)
        cues.append(
            {
                "start": start,
                "end": end,
                "text": "\n".join(content),
                "word_indices": [w["index"] for w in group],
            }
        )

    for word in words:
        if granularity == "segments":
            group = [word]
            emit()
            group = []
            continue
        candidate = group + [word]
        if group and (
            len(lines(candidate)) > 2
            or word["end"] - group[0]["start"] > 3000
            or word["start"] - group[-1]["end"] > 550
        ):
            emit()
            group = []
        group.append(word)
    if group:
        emit()
    return {
        "schema_version": "1",
        "cues": cues,
        "font": font_record(),
        "style": {
            "size": size,
            "safe_left": 108,
            "safe_right": 108,
            "safe_bottom": 320,
            "max_lines": 2,
        },
        "meaning_review": "human_required",
        "timing": "owner_supplied_segment_mapping"
        if granularity == "segments"
        else "source_word_mapping",
    }


def timestamp(ms, *, vtt=False):
    h, rem = divmod(ms, 3600000)
    m, rem = divmod(rem, 60000)
    s, fract = divmod(rem, 1000)
    return f"{h:02}:{m:02}:{s:02}{'.' if vtt else ','}{fract:03}"


def text_exports(plan):
    cues = plan["cues"]
    srt = (
        "\n\n".join(
            f"{i}\n{timestamp(c['start'])} --> {timestamp(c['end'])}\n{c['text']}"
            for i, c in enumerate(cues, 1)
        )
        + "\n"
    )
    vtt = (
        "WEBVTT\n\n"
        + "\n\n".join(
            f"{timestamp(c['start'], vtt=True)} --> {timestamp(c['end'], vtt=True)}\n{c['text']}"
            for c in cues
        )
        + "\n"
    )
    return {"subtitles.srt": srt, "subtitles.vtt": vtt}


def ass(plan):
    def clock(ms):
        # ASS uses centiseconds. Round rather than changing the editable word times.
        return timestamp(round(ms / 10) * 10, vtt=True)[1:-1]

    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Inter,48,&H00FFFFFF,&H00FFFFFF,&H00141414,&H00141414,0,0,0,0,100,100,0,0,3,9,0,2,108,108,320,1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    header = header.replace(
        "Style: Default,Inter,48,", f"Style: Default,Inter,{plan['style']['size']},"
    )
    rows = []
    for cue in plan["cues"]:
        text = cue["text"].replace("\n", "\\N")
        rows.append(
            f"Dialogue: 0,{clock(cue['start'])},{clock(cue['end'])},Default,,0,0,0,,{text}\n"
        )
    return header + "".join(rows)
