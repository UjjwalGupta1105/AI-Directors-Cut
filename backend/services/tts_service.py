import os
import logging
import struct
import wave

logger = logging.getLogger(__name__)


def _gemini_tts(text: str, output_path: str) -> bool:
    """Try Gemini TTS. Returns True on success."""
    try:
        from google import genai
        from google.genai import types
        from dotenv import load_dotenv
        from pathlib import Path

        env_path = Path(__file__).parent.parent.parent / ".env"
        load_dotenv(dotenv_path=env_path, override=True)

        api_key = os.getenv("GEMINI_API_KEY", "").strip().strip('"').strip("'")
        tts_model = os.getenv("GEMINI_TTS_MODEL", "gemini-2.5-flash-preview-tts")

        client = genai.Client(api_key=api_key, http_options=types.HttpOptions(timeout=12000))

        response = client.models.generate_content(
            model=tts_model,
            contents=text,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Kore")
                    )
                )
            )
        )

        audio_data = response.candidates[0].content.parts[0].inline_data.data

        # Write as WAV
        wav_path = output_path.replace(".mp3", ".wav")
        with wave.open(wav_path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(24000)
            wf.writeframes(audio_data)

        # Rename to expected path
        if wav_path != output_path:
            os.rename(wav_path, output_path)
        elif not output_path.endswith(".wav"):
            os.rename(wav_path, output_path)

        logger.info(f"Gemini TTS generated: {output_path}")
        return True

    except Exception as e:
        logger.warning(f"Gemini TTS failed: {e}")
        return False


def _pyttsx3_tts(text: str, output_path: str) -> bool:
    """Local pyttsx3 fallback TTS."""
    try:
        import pyttsx3
        engine = pyttsx3.init()
        engine.setProperty("rate", 165)
        engine.setProperty("volume", 0.9)

        wav_path = output_path if output_path.endswith(".wav") else output_path.rsplit(".", 1)[0] + ".wav"
        engine.save_to_file(text, wav_path)
        engine.runAndWait()

        if not os.path.exists(wav_path) or os.path.getsize(wav_path) < 100:
            raise RuntimeError("pyttsx3 produced empty or missing file")

        if wav_path != output_path:
            os.rename(wav_path, output_path)

        logger.info(f"pyttsx3 TTS generated: {output_path}")
        return True

    except Exception as e:
        logger.error(f"pyttsx3 TTS failed: {e}")
        return False


def generate_narration(text: str, output_path: str) -> str:
    """Generate TTS audio. Returns path to the generated file (.wav)."""
    # Always save as .wav for FFmpeg compatibility
    wav_path = output_path.rsplit(".", 1)[0] + ".wav"

    if _gemini_tts(text, wav_path):
        return wav_path

    logger.info("Falling back to pyttsx3 for TTS")
    if _pyttsx3_tts(text, wav_path):
        return wav_path

    # Last resort: generate a short silence so FFmpeg doesn't crash
    logger.error("Both TTS methods failed — generating silent placeholder")
    _write_silence(wav_path, duration_seconds=3)
    return wav_path


def _write_silence(path: str, duration_seconds: int = 3):
    sample_rate = 24000
    num_samples = sample_rate * duration_seconds
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(b"\x00\x00" * num_samples)
