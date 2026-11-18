import argparse
import json
import math
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Clip:
    name: str
    start: float
    end: float
    focus: float
    captions: Path | None


def ffmpeg(directory: Path, *args: str) -> None:
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-v", "error", "-nostdin", *args],
        cwd=directory, check=True,
    )


def duration_seconds(video: Path) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(video)],
        capture_output=True, text=True, check=True,
    )
    return float(result.stdout.strip())


def number(value: object, label: str) -> float:
    if type(value) not in (float, int) or not math.isfinite(value):
        raise ValueError(f"{label} deve essere un numero finito")
    return float(value)


def read_clips(manifest: Path, duration: float) -> list[Clip]:
    rows = json.loads(manifest.read_text(encoding="utf-8-sig"))
    if not isinstance(rows, list) or not rows:
        raise ValueError("Il manifest deve contenere almeno una clip")

    clips = []
    names = set()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Ogni clip deve essere un oggetto JSON")
        name = row.get("name")
        if not isinstance(name, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name):
            raise ValueError("Ogni clip richiede un nome in minuscolo, con trattini facoltativi")
        if name in names or re.fullmatch(r"con|prn|aux|nul|(?:com|lpt)[1-9]", name):
            raise ValueError(f"Nome duplicato o riservato: {name}")
        names.add(name)

        start = number(row.get("start"), f"{name}.start")
        end = number(row.get("end"), f"{name}.end")
        focus = number(row.get("focus", 0.5), f"{name}.focus")
        if not 0 <= start < end <= duration or end - start < 1 / 30:
            raise ValueError(f"{name}: intervallo fuori dal video o troppo breve")
        if not 0 <= focus <= 1:
            raise ValueError(f"{name}: focus deve essere compreso fra 0 e 1")

        captions = row.get("captions")
        if captions is not None:
            if not isinstance(captions, str) or not captions:
                raise ValueError(f"{name}: captions richiede il percorso di un file SRT")
            captions = (manifest.parent / captions).resolve()
            if captions.suffix.lower() != ".srt" or not captions.is_file():
                raise ValueError(f"{name}: file SRT mancante o non valido")
        clips.append(Clip(name, start, end, focus, captions))
    return clips


def render_clip(video: Path, clip: Clip, directory: Path) -> None:
    filters = (
        "scale=w='max(1080,ceil(1920*dar/2)*2)':h='max(1920,ceil(1080/dar/2)*2)',"
        "setsar=1,"
        f"crop=1080:1920:x=(in_w-out_w)*{clip.focus}:y=(in_h-out_h)/2,fps=30"
    )
    if clip.captions:
        shutil.copyfile(clip.captions, directory / "captions.srt")
        filters += ",subtitles=captions.srt:force_style='FontSize=18,Outline=2,MarginV=28'"
    output = f"{clip.name}.mp4"
    ffmpeg(
        directory, "-ss", f"{clip.start:.6f}", "-i", str(video),
        "-t", f"{clip.end - clip.start:.6f}", "-map", "0:v:0", "-map", "0:a:0?",
        "-vf", filters, "-c:v", "libx264", "-preset", "fast", "-crf", "20",
        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k",
        "-movflags", "+faststart", output,
    )
    ffmpeg(directory, "-xerror", "-i", output, "-f", "null", "-")


def main() -> None:
    parser = argparse.ArgumentParser(description="Esporta Shorts e copertina NOESIS.")
    for name in ("video", "manifest", "cover", "output"):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()

    try:
        video, manifest, cover, output = (
            path.resolve() for path in (args.video, args.manifest, args.cover, args.output)
        )
        if output.exists():
            raise ValueError("Scegli una cartella di output nuova")
        clips = read_clips(manifest, duration_seconds(video))
        output.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix=".noesis-", dir=output.parent) as temp:
            staging = Path(temp) / "result"
            staging.mkdir()
            for clip in clips:
                render_clip(video, clip, staging)
            (staging / "captions.srt").unlink(missing_ok=True)
            ffmpeg(
                staging, "-i", str(cover), "-vf",
                "scale=w='min(1280,max(2,trunc(720*dar/2)*2))':"
                "h='min(720,max(2,trunc(1280/dar/2)*2))',"
                "setsar=1,pad=1280:720:(ow-iw)/2:(oh-ih)/2",
                "-frames:v", "1", "-q:v", "3", "-update", "1", "cover.jpg",
            )
            ffmpeg(staging, "-xerror", "-i", "cover.jpg", "-f", "null", "-")
            staging.rename(output)
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        parser.exit(1, f"Errore: {exc}\n")
    print(f"Esportate {len(clips)} clip e la copertina in {output}")


if __name__ == "__main__":
    main()
