# WhisperX Japanese English Subtitles

Reusable bilingual subtitle pipeline for Japanese and English videos.

## What It Does

- Transcribes and aligns audio with WhisperX.
- Creates Japanese + English subtitle lines in an `.ass` file.
- Optionally burns the subtitles into a new MP4 using FFmpeg.

## Folder Layout

- `caption_pipeline.py` - main script.
- `config.example.yaml` - starter config.
- `config.yaml` - your local working config, ignored by Git.
- `.venv` - local Python environment, ignored by Git.

## Setup

Use Python 3.10 through 3.13. Python 3.12 is recommended.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip setuptools wheel
.\.venv\Scripts\python.exe -m pip install -r .\requirements.txt
```

For NVIDIA GPU acceleration on Windows, install the CUDA PyTorch wheels after the regular requirements:

```powershell
.\.venv\Scripts\python.exe -m pip install --force-reinstall torch==2.8.0 torchvision==0.23.0 torchaudio==2.8.0 --index-url https://download.pytorch.org/whl/cu128
```

## Run It

From PowerShell:

```powershell
copy .\config.example.yaml .\config.yaml
.\.venv\Scripts\python.exe .\caption_pipeline.py --config .\config.yaml
```

The first run can take a while because WhisperX downloads model files.

## Notes

- `whisper.language` should usually be `ja` for Japanese spoken audio.
- If the spoken audio is English, set `whisper.language` to `en`; the script will put Japanese on top and English below.
- Translation uses `deep-translator` by default, which sends text to Google Translate through its public endpoint.
- FFmpeg must be installed and available on `PATH`.
- CUDA-enabled PyTorch is recommended for faster transcription.
