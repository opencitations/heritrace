# User Testing Analysis Software

Privacy-focused toolkit for analyzing user testing sessions, starting with video transcription.

## Features

- **Privacy-First**: Uses Voxtral Mini for completely offline transcription
- **Batch Processing**: Process multiple videos automatically
- **Multiple Formats**: Supports MP4, AVI, MOV, MKV, WebM
- **Structured Output**: JSON format with timestamps and metadata

## Installation

```bash
# Install dependencies with uv
uv sync

# Or install ffmpeg separately if needed
sudo apt install ffmpeg  # Ubuntu/Debian
brew install ffmpeg      # macOS
```

## Usage

### Single Video
```bash
python transcriber.py video.mp4
```

### Batch Processing
```bash
python transcriber.py /path/to/videos/
```

Output saved as `transcriptions.json` in the video directory.

## Privacy Notes

- All processing happens locally
- No data sent to external services
- Audio files automatically cleaned up after transcription
- Voxtral Mini model runs entirely offline

## Output Format

```json
{
  "video_file": "/path/to/video.mp4",
  "timestamp": "2025-07-30T10:30:00",
  "model": "mistralai/voxtral-mini",
  "transcription": "Participant speaks about the interface..."
}
```