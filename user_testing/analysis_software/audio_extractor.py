#!/usr/bin/env python3
"""
Audio extraction tool for video files
"""

import argparse
import sys
from pathlib import Path

import ffmpeg
from tqdm import tqdm


class AudioExtractor:
    def extract_audio(self, video_path, output_path=None, sample_rate=16000, channels=1, bitrate='64k'):
        """
        Extract audio from video file

        Args:
            video_path: Path to video file
            output_path: Path for output audio file (default: same name as video with .mp3 extension)
            sample_rate: Audio sample rate in Hz (default: 16000)
            channels: Number of audio channels (default: 1 for mono)
            bitrate: Audio bitrate for MP3 encoding (default: '64k')

        Returns:
            Path to extracted audio file or None if extraction failed
        """
        video_path = Path(video_path)

        if not video_path.exists():
            print(f"Error: Video file not found: {video_path}")
            return None

        if output_path is None:
            output_path = video_path.with_suffix('.mp3')
        else:
            output_path = Path(output_path)

        print(f"Extracting audio from: {video_path.name}")
        print(f"Output: {output_path}")

        try:
            (
                ffmpeg
                .input(str(video_path))
                .audio
                .output(
                    str(output_path),
                    acodec='libmp3lame',
                    ac=channels,
                    ar=sample_rate,
                    audio_bitrate=bitrate
                )
                .overwrite_output()
                .run(quiet=True)
            )
            print(f"Audio extracted successfully: {output_path}")
            return output_path
        except ffmpeg.Error as e:
            print(f"Error extracting audio: {e}")
            return None

    def batch_extract(self, video_directory, output_directory=None, sample_rate=16000, channels=1, bitrate='64k'):
        """
        Extract audio from all videos in a directory

        Args:
            video_directory: Directory containing video files
            output_directory: Directory for output audio files (default: same as input)
            sample_rate: Audio sample rate in Hz (default: 16000)
            channels: Number of audio channels (default: 1 for mono)
            bitrate: Audio bitrate for MP3 encoding (default: '64k')
        """
        video_dir = Path(video_directory)

        if not video_dir.exists() or not video_dir.is_dir():
            print(f"Error: Directory not found: {video_dir}")
            return

        if output_directory is None:
            output_dir = video_dir
        else:
            output_dir = Path(output_directory)
            output_dir.mkdir(parents=True, exist_ok=True)

        video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.webm'}

        video_files = [
            f for f in video_dir.iterdir()
            if f.suffix.lower() in video_extensions
        ]

        if not video_files:
            print(f"No video files found in {video_dir}")
            return

        successful = 0
        failed = 0

        for video_file in tqdm(video_files, desc="Extracting audio"):
            output_path = output_dir / f"{video_file.stem}.mp3"

            try:
                result = self.extract_audio(
                    video_file,
                    output_path,
                    sample_rate=sample_rate,
                    channels=channels,
                    bitrate=bitrate
                )
                if result:
                    successful += 1
                else:
                    failed += 1
            except Exception as e:
                print(f"Error processing {video_file.name}: {e}")
                failed += 1

        print(f"\nExtraction completed: {successful} successful, {failed} failed")


def main():
    parser = argparse.ArgumentParser(
        description='Extract audio from video files'
    )
    parser.add_argument(
        'path',
        help='Video file or directory containing videos'
    )
    parser.add_argument(
        '--output',
        help='Output audio file or directory (default: same location as input with .mp3 extension)'
    )
    parser.add_argument(
        '--sample-rate',
        type=int,
        default=16000,
        help='Audio sample rate in Hz (default: 16000)'
    )
    parser.add_argument(
        '--channels',
        type=int,
        default=1,
        choices=[1, 2],
        help='Number of audio channels: 1 for mono, 2 for stereo (default: 1)'
    )
    parser.add_argument(
        '--bitrate',
        default='64k',
        help='MP3 bitrate (default: 64k). Examples: 64k, 128k, 192k'
    )

    args = parser.parse_args()

    path = Path(args.path)
    extractor = AudioExtractor()

    if path.is_file():
        extractor.extract_audio(
            path,
            output_path=args.output,
            sample_rate=args.sample_rate,
            channels=args.channels,
            bitrate=args.bitrate
        )
    elif path.is_dir():
        extractor.batch_extract(
            path,
            output_directory=args.output,
            sample_rate=args.sample_rate,
            channels=args.channels,
            bitrate=args.bitrate
        )
    else:
        print(f"Error: Path not found: {path}")
        sys.exit(1)


if __name__ == "__main__":
    main()
