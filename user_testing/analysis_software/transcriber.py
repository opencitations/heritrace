#!/usr/bin/env python3
"""
Video transcription tool using Voxtral Mini for privacy-focused transcription
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import ffmpeg
import torch
from tqdm import tqdm
from transformers import AutoProcessor, VoxtralForConditionalGeneration


class VideoTranscriber:
    def __init__(self, model_name="mistralai/Voxtral-Mini-3B-2507"):
        """Initialize the transcriber with Voxtral Mini model"""
        self.model_name = model_name
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.processor = None
        self.model = None
        
    def load_model(self):
        """Load the Voxtral model and processor"""
        print(f"Loading {self.model_name} on {self.device}...")
        self.processor = AutoProcessor.from_pretrained(self.model_name)
        self.model = VoxtralForConditionalGeneration.from_pretrained(
            self.model_name,
            torch_dtype=torch.bfloat16 if self.device == "cuda" else torch.float32
        ).to(self.device)
        print("Model loaded successfully!")
    
    def extract_audio(self, video_path, output_path=None):
        """Extract audio from video file"""
        if output_path is None:
            output_path = Path(video_path).with_suffix('.wav')
        
        print(f"Extracting audio from video...")
        try:
            (
                ffmpeg
                .input(video_path)
                .audio
                .output(str(output_path), acodec='pcm_s16le', ac=1, ar=16000)
                .overwrite_output()
                .run(quiet=True)
            )
            print(f"Audio extracted successfully: {output_path}")
            return output_path
        except ffmpeg.Error as e:
            print(f"Error extracting audio: {e}")
            return None
    
    def transcribe_audio(self, audio_path, language="auto"):
        """Transcribe audio file using Voxtral"""
        if not self.model or not self.processor:
            self.load_model()
                
        inputs = self.processor.apply_transcription_request(
            language=language,
            audio=str(audio_path),
            model_id=self.model_name
        )
        inputs = inputs.to(self.device, dtype=torch.bfloat16 if self.device == "cuda" else torch.float32)
        
        print("Running model inference...")
        with torch.no_grad():
            outputs = self.model.generate(**inputs, max_new_tokens=500)
        
        print("Decoding transcription...")
        # Decode only the new tokens (skip input)
        transcription = self.processor.batch_decode(
            outputs[:, inputs.input_ids.shape[1]:], 
            skip_special_tokens=True
        )[0]
        print("Transcription completed!")
        return transcription
    
    def transcribe_video(self, video_path, keep_audio=False, language="auto"):
        """Complete video transcription pipeline"""
        video_path = Path(video_path)
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")
        
        print(f"Processing: {video_path.name}")
        
        audio_path = self.extract_audio(video_path)
        if not audio_path:
            return None
        
        try:
            transcription = self.transcribe_audio(audio_path, language)
            
            result = {
                "video_file": str(video_path),
                "timestamp": datetime.now().isoformat(),
                "model": self.model_name,
                "transcription": transcription
            }
            
            return result
            
        finally:
            if not keep_audio and audio_path.exists():
                audio_path.unlink()
    
    def batch_transcribe(self, video_directory, output_file="transcriptions.json", language="auto"):
        """Transcribe all videos in a directory"""
        video_dir = Path(video_directory)
        video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.webm'}
        
        video_files = [
            f for f in video_dir.iterdir() 
            if f.suffix.lower() in video_extensions
        ]
        
        if not video_files:
            print(f"No video files found in {video_dir}")
            return
        
        results = []
        
        for video_file in tqdm(video_files, desc="Transcribing videos"):
            try:
                result = self.transcribe_video(video_file, language=language)
                if result:
                    results.append(result)
                    print(f"✓ {video_file.name}")
                else:
                    print(f"✗ Failed: {video_file.name}")
            except Exception as e:
                print(f"✗ Error processing {video_file.name}: {e}")
        
        output_path = video_dir / output_file
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"\nTranscriptions saved to: {output_path}")
        print(f"Successfully processed {len(results)}/{len(video_files)} videos")


def main():
    parser = argparse.ArgumentParser(
        description='Video transcription tool using Voxtral Mini for privacy-focused transcription'
    )
    parser.add_argument(
        'path',
        help='Video file or directory containing videos to transcribe'
    )
    parser.add_argument(
        '--output',
        default='transcriptions.json',
        help='Output filename for batch transcription (default: transcriptions.json)'
    )
    parser.add_argument(
        '--keep-audio',
        action='store_true',
        help='Keep extracted audio files after transcription'
    )
    parser.add_argument(
        '--language',
        default='auto',
        help='Language for transcription (e.g., "it" for Italian, "en" for English, "auto" for auto-detection)'
    )
    
    args = parser.parse_args()
    
    path = Path(args.path)
    transcriber = VideoTranscriber()
    
    if path.is_file():
        result = transcriber.transcribe_video(path, keep_audio=args.keep_audio, language=args.language)
        if result:
            print(f"\nTranscription:\n{result['transcription']}")
    elif path.is_dir():
        transcriber.batch_transcribe(path, output_file=args.output, language=args.language)
    else:
        print(f"Path not found: {path}")
        sys.exit(1)


if __name__ == "__main__":
    main()