from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pysubs2
import yaml
from deep_translator import GoogleTranslator
from rich.console import Console
from rich.progress import track

console = Console(force_terminal=False, legacy_windows=False)


@dataclass
class Settings:
    input_video: Path
    output_dir: Path
    whisper: dict[str, Any]
    captions: dict[str, Any]
    style: dict[str, Any]
    render: dict[str, Any]


def load_settings(config_path: Path) -> Settings:
    with config_path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)

    return Settings(
        input_video=Path(raw["input_video"]),
        output_dir=Path(raw["output_dir"]),
        whisper=raw.get("whisper", {}),
        captions=raw.get("captions", {}),
        style=raw.get("style", {}),
        render=raw.get("render", {}),
    )


def safe_path(path: Path) -> str:
    return str(path).encode("ascii", errors="backslashreplace").decode("ascii")


def transcribe_and_align(settings: Settings) -> dict[str, Any]:
    import whisperx

    device = settings.whisper.get("device", "cpu")
    batch_size = int(settings.whisper.get("batch_size", 8))
    compute_type = settings.whisper.get("compute_type", "int8")
    model_name = settings.whisper.get("model", "large-v3")
    language = settings.whisper.get("language") or None

    console.print(f"[bold]Loading WhisperX model:[/bold] {model_name}")
    model = whisperx.load_model(model_name, device, compute_type=compute_type, language=language)

    console.print("[bold]Loading audio[/bold]")
    audio = whisperx.load_audio(str(settings.input_video))

    console.print("[bold]Transcribing[/bold]")
    result = model.transcribe(audio, batch_size=batch_size, language=language)
    detected_language = result.get("language") or language or "ja"

    console.print(f"[bold]Aligning transcript[/bold] ({detected_language})")
    align_model, metadata = whisperx.load_align_model(language_code=detected_language, device=device)
    return whisperx.align(
        result["segments"],
        align_model,
        metadata,
        audio,
        device,
        return_char_alignments=False,
    ) | {"language": detected_language}


def translate_segments(segments: list[dict[str, Any]], source: str, target: str) -> list[str]:
    translator = GoogleTranslator(source=source, target=target)
    translations: list[str] = []
    for segment in track(segments, description=f"Translating {source} to {target}"):
        text = clean_text(segment.get("text", ""))
        translations.append(translator.translate(text) if text else "")
    return translations


def clean_text(text: str) -> str:
    return " ".join(text.replace("\n", " ").split()).strip()


def clamp_timing(start: float, end: float, min_duration: float, max_duration: float) -> tuple[int, int]:
    duration = max(end - start, min_duration)
    duration = min(duration, max_duration)
    return int(start * 1000), int((start + duration) * 1000)


def build_ass(settings: Settings, result: dict[str, Any], ass_path: Path) -> None:
    source_language = result.get("language", "ja")
    segments = [segment for segment in result.get("segments", []) if clean_text(segment.get("text", ""))]
    japanese_on_top = bool(settings.captions.get("japanese_on_top", True))

    if source_language.startswith("ja"):
        source_lines = [clean_text(segment["text"]) for segment in segments]
        translated_lines = translate_segments(segments, "ja", "en")
        top_lines = source_lines if japanese_on_top else translated_lines
        bottom_lines = translated_lines if japanese_on_top else source_lines
    elif source_language.startswith("en"):
        source_lines = [clean_text(segment["text"]) for segment in segments]
        translated_lines = translate_segments(segments, "en", "ja")
        top_lines = translated_lines if japanese_on_top else source_lines
        bottom_lines = source_lines if japanese_on_top else translated_lines
    else:
        source_lines = [clean_text(segment["text"]) for segment in segments]
        translated_lines = translate_segments(segments, source_language, "en")
        top_lines = source_lines
        bottom_lines = translated_lines

    subs = pysubs2.SSAFile()
    style = settings.style
    subs.styles["Bilingual"] = pysubs2.SSAStyle(
        fontname=style.get("font_name", "Yu Gothic UI"),
        fontsize=float(style.get("font_size", 42)),
        primarycolor=pysubs2.Color(255, 255, 255, 0),
        outlinecolor=pysubs2.Color(22, 22, 22, 0),
        backcolor=pysubs2.Color(0, 0, 0, 120),
        bold=False,
        alignment=2,
        marginv=int(style.get("margin_v", 78)),
        outline=float(style.get("outline", 2.4)),
        shadow=float(style.get("shadow", 0.6)),
    )

    min_duration = float(settings.captions.get("min_duration", 1.0))
    max_duration = float(settings.captions.get("max_duration", 7.0))

    for segment, top, bottom in zip(segments, top_lines, bottom_lines):
        start, end = clamp_timing(float(segment["start"]), float(segment["end"]), min_duration, max_duration)
        subs.events.append(
            pysubs2.SSAEvent(
                start=start,
                end=end,
                text=f"{top}\\N{{\\fs{int(style.get('english_font_size', 34))}}}{bottom}",
                style="Bilingual",
            )
        )

    subs.save(str(ass_path))


def ffmpeg_filter_path(path: Path) -> str:
    normalized = path.resolve().as_posix().replace(":", r"\:")
    return normalized.replace("'", r"\'")


def render_video(input_video: Path, ass_path: Path, output_video: Path) -> None:
    command = [
        "ffmpeg",
        "-y",
        "-i",
        str(input_video),
        "-vf",
        f"ass='{ffmpeg_filter_path(ass_path)}'",
        "-c:a",
        "copy",
        str(output_video),
    ]
    console.print("[bold]Rendering burned-in caption video[/bold]")
    subprocess.run(command, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate bilingual Japanese/English captions.")
    parser.add_argument("--config", default="config.yaml", type=Path)
    parser.add_argument("--skip-render", action="store_true")
    args = parser.parse_args()

    settings = load_settings(args.config)
    settings.output_dir.mkdir(parents=True, exist_ok=True)

    stem = settings.input_video.stem
    transcript_path = settings.output_dir / f"{stem}.whisperx.json"
    ass_path = settings.output_dir / f"{stem}.bilingual.ass"
    suffix = settings.render.get("output_name_suffix", "_bilingual_captions")
    output_video = settings.output_dir / f"{stem}{suffix}.mp4"

    if transcript_path.exists():
        console.print(f"[green]Using transcript:[/green] {safe_path(transcript_path)}")
        result = json.loads(transcript_path.read_text(encoding="utf-8"))
    else:
        result = transcribe_and_align(settings)
        transcript_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        console.print(f"[green]Saved transcript:[/green] {safe_path(transcript_path)}")

    build_ass(settings, result, ass_path)
    console.print(f"[green]Saved subtitles:[/green] {safe_path(ass_path)}")

    if settings.render.get("burn_in", True) and not args.skip_render:
        render_video(settings.input_video, ass_path, output_video)
        console.print(f"[green]Saved rendered video:[/green] {safe_path(output_video)}")


if __name__ == "__main__":
    main()
