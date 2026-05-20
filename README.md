# WhisperX Japanese English Captions

Reusable bilingual caption pipeline for Japanese and English subtitles.

## What It Does

- Transcribes and aligns audio with WhisperX.
- Creates Japanese + English subtitle lines in an `.ass` file.
- Optionally burns the captions into a new MP4 using FFmpeg.

## Folder Layout

- `caption_pipeline.py` - main script.
- `config.example.yaml` - starter config.
- `config.yaml` - your local working config, ignored by Git.
- `.venv` - local Python environment, ignored by Git.

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
