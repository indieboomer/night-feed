import os
import json
from elevenlabs.client import ElevenLabs
from elevenlabs import save


class TTSClient:
    """ElevenLabs TTS client for Polish audio generation."""

    def __init__(self):
        api_key = os.getenv('ELEVENLABS_API_KEY')
        if not api_key:
            raise ValueError("ELEVENLABS_API_KEY environment variable not set")

        self.client = ElevenLabs(api_key=api_key)
        self.load_voice_settings()

    def load_voice_settings(self):
        """Load voice configuration from config file."""
        config_path = '/config/voice_settings.json'

        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    config = json.load(f)

                self.voice_id = config.get('voice_id', os.getenv('ELEVENLABS_VOICE_ID', 'pMsXgVXv3BLzUgSXRplE'))
                self.model_id = config.get('model_id', 'eleven_multilingual_v2')
                self.voice_settings = config.get('voice_settings', {})

                print(f"Voice config loaded: {self.voice_id} (model: {self.model_id})")
            except Exception as e:
                print(f"WARNING: Failed to load voice config: {e}, using defaults")
                self.use_defaults()
        else:
            print("WARNING: Voice config not found, using defaults")
            self.use_defaults()

    def use_defaults(self):
        """Use default voice settings."""
        self.voice_id = os.getenv('ELEVENLABS_VOICE_ID', 'pMsXgVXv3BLzUgSXRplE')
        self.model_id = 'eleven_multilingual_v2'
        self.voice_settings = {
            'stability': 0.7,
            'similarity_boost': 0.8,
            'style': 0.3,
            'use_speaker_boost': True
        }

    def generate_audio(self, text, output_path):
        """Generate audio from text using ElevenLabs API."""
        print(f"Generating audio with voice: {self.voice_id}")
        print(f"  Text length: {len(text)} characters")
        print(f"  Model: {self.model_id}")

        try:
            # Generate audio
            audio = self.client.generate(
                text=text,
                voice=self.voice_id,
                model=self.model_id,
                voice_settings=self.voice_settings
            )

            # Save to file
            save(audio, output_path)

            # Get file size
            file_size = os.path.getsize(output_path)
            file_size_mb = file_size / (1024 * 1024)

            print(f"✓ Audio generated: {output_path}")
            print(f"  File size: {file_size_mb:.2f} MB")

            # Estimate cost (approximate)
            # ElevenLabs charges ~$0.30 per 1000 characters
            char_count = len(text)
            estimated_cost = (char_count / 1000) * 0.30

            metadata = {
                'voice_id': self.voice_id,
                'model': self.model_id,
                'characters': char_count,
                'file_size_bytes': file_size,
                'estimated_cost_usd': round(estimated_cost, 4)
            }

            print(f"  Estimated cost: ${estimated_cost:.4f}")

            return metadata

        except Exception as e:
            print(f"ERROR: TTS generation failed: {e}")
            raise

    def get_audio_duration(self, audio_path):
        """Get audio duration using mutagen."""
        try:
            from mutagen.mp3 import MP3
            audio = MP3(audio_path)
            duration_seconds = int(audio.info.length)

            minutes = duration_seconds // 60
            seconds = duration_seconds % 60

            print(f"  Audio duration: {minutes}:{seconds:02d}")

            return duration_seconds

        except Exception as e:
            print(f"WARNING: Could not determine audio duration: {e}")
            return None
