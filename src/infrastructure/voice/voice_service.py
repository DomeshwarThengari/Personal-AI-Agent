import io
import time
import wave
from typing import List, Optional
from src.domain.interfaces.voice_service import AbstractVoiceService
from src.config.settings import settings
from src.utils.logging import get_logger

logger = get_logger("voice_service")

# Lazy import flag
AUDIO_LIBS_AVAILABLE = False
try:
    import sounddevice as sd
    import speech_recognition as sr
    import numpy as np
    from gtts import gTTS

    AUDIO_LIBS_AVAILABLE = True
except (ImportError, OSError) as e:
    logger.warning(
        f"Audio libraries not fully available. Fallback to mock mode. Error: {e}"
    )


class VoiceService(AbstractVoiceService):
    """Concrete adapter for Voice operations.

    Utilizes SpeechRecognition and gTTS for online STT/TTS, and sounddevice
    for mic recording. Falls back to CLI/Mock mode if no hardware is present.
    """

    def __init__(self, force_mock: bool = False) -> None:
        """Initializes voice service.

        Args:
            force_mock: If True, forces mock/simulated mode even if audio devices are present.
        """
        self._force_mock = force_mock
        self._is_playing = False
        self._interrupted = False
        self._spoken_history: List[str] = []

        # Check if hardware audio devices are available
        self._has_hardware = False
        if AUDIO_LIBS_AVAILABLE and not self._force_mock:
            try:
                devices = sd.query_devices()
                if devices:
                    # Look for at least one input and one output channel
                    has_input = any(d.get("max_input_channels", 0) > 0 for d in devices)
                    has_output = any(
                        d.get("max_output_channels", 0) > 0 for d in devices
                    )
                    self._has_hardware = has_input and has_output
            except Exception as e:
                logger.warning(f"Failed to query audio devices: {e}")
                self._has_hardware = False

        if self._has_hardware:
            logger.info("VoiceService initialized in REAL hardware mode.")
        else:
            logger.info("VoiceService initialized in SIMULATED/MOCK mode.")

    @property
    def spoken_history(self) -> List[str]:
        """Returns the history of spoken texts (primarily for testing verification)."""
        return self._spoken_history

    def is_audio_available(self) -> bool:
        return self._has_hardware

    def listen_for_wake_word(self, wake_word: str) -> bool:
        """Listens for the wake word.

        In simulated mode, reads stdin and returns True if input contains the wake word.
        In hardware mode, listens continuously and transcribes.
        """
        self._interrupted = False
        if not self._has_hardware:
            print(
                f"\n[Siri Passive Listening] (Wake Word: '{wake_word}'). Press Enter or type a command to wake me up..."
            )
            try:
                user_input = input(">> ").strip().lower()
                if not user_input or wake_word.lower() in user_input:
                    return True
                # Return True anyway to simulate wake word trigger for convenience
                return True
            except KeyboardInterrupt:
                return False

        # Hardware mode wake word detection
        logger.info(f"Listening for wake word: '{wake_word}'...")
        # Capture a brief 2.5 second audio snippet and check if it contains the word
        try:
            sample_rate = 16000
            duration = 2.5
            recording = sd.rec(
                int(duration * sample_rate),
                samplerate=sample_rate,
                channels=1,
                dtype="int16",
            )
            sd.wait()

            # Convert numpy array to WAV bytes
            wav_io = io.BytesIO()
            with wave.open(wav_io, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(sample_rate)
                wf.writeframes(recording.tobytes())
            wav_io.seek(0)

            r = sr.Recognizer()
            with sr.AudioFile(wav_io) as source:
                audio = r.record(source)
            text = r.recognize_google(audio).strip().lower()
            logger.debug(f"Passive listen transcribed: '{text}'")
            return wake_word.lower() in text
        except Exception as e:
            logger.debug(f"Wake word listening error/timeout: {e}")
            return False

    def record_command(self, duration: Optional[float] = None) -> Optional[str]:
        """Records command from mic. In simulated mode, requests CLI input."""
        rec_duration = (
            duration if duration is not None else settings.VOICE_INPUT_DURATION
        )

        if not self._has_hardware:
            print("\n[Siri Listening] Say your command (Type below):")
            try:
                cmd = input("You (Voice): ").strip()
                return cmd if cmd else None
            except KeyboardInterrupt:
                return None

        # Hardware mode STT
        sample_rate = 16000
        logger.info(f"Recording command for {rec_duration} seconds...")
        print(f"\n* Siri Listening for {rec_duration}s... *")
        try:
            recording = sd.rec(
                int(rec_duration * sample_rate),
                samplerate=sample_rate,
                channels=1,
                dtype="int16",
            )
            sd.wait()
            logger.info("Recording finished. Transcribing...")

            wav_io = io.BytesIO()
            with wave.open(wav_io, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(sample_rate)
                wf.writeframes(recording.tobytes())
            wav_io.seek(0)

            r = sr.Recognizer()
            with sr.AudioFile(wav_io) as source:
                audio = r.record(source)
            text = r.recognize_google(audio)
            logger.info(f"Transcription: {text}")
            return str(text)
        except Exception as e:
            logger.error(f"Speech recognition failed: {e}")
            print(f"* (Could not recognize speech: {e}) *")
            return None

    def speak_text(self, text: str) -> None:
        """Synthesizes text to speech.

        In simulated mode, prints output.
        In hardware mode, downloads Google TTS MP3, logs, and plays a simulated beep/audio.
        """
        self._spoken_history.append(text)
        self._interrupted = False
        print(f"\n[Siri Voice]: {text}")

        if not self._has_hardware:
            # Simulate speech duration based on word count
            word_count = len(text.split())
            sleep_time = min(4.0, max(0.5, word_count * 0.3))
            # Sleep in tiny increments to allow simulated interruption
            for _ in range(int(sleep_time * 10)):
                if self._interrupted:
                    print(" [Siri Output Interrupted] ")
                    break
                time.sleep(0.1)
            return

        # Hardware mode TTS
        logger.info(f"Generating TTS audio for: '{text[:30]}...'")
        try:
            tts = gTTS(text=text, lang="en")
            # In a container environment, we write the MP3 file
            import tempfile
            from pathlib import Path

            temp_dir = Path(tempfile.gettempdir())
            mp3_path = temp_dir / "siri_response.mp3"
            tts.save(str(mp3_path))
            logger.info(f"Speech response saved to {mp3_path.resolve()}")

            # Since native MP3 playback may fail on headless/bare servers,
            # we simulate playback duration while checking for voice barge-in (mic level)
            self._is_playing = True
            word_count = len(text.split())
            playback_duration = min(6.0, max(1.0, word_count * 0.35))

            # Monitor microphone for interruption during speech
            sample_rate = 16000
            chunk_duration = 0.2  # 200ms audio chunks
            chunk_size = int(sample_rate * chunk_duration)
            elapsed = 0.0

            logger.info(
                "Simulating speech playback & monitoring mic for interruption..."
            )
            while (
                elapsed < playback_duration
                and self._is_playing
                and not self._interrupted
            ):
                # Read a brief chunk from the mic to check volume levels (RMS)
                try:
                    mic_chunk = sd.rec(
                        chunk_size,
                        samplerate=sample_rate,
                        channels=1,
                        dtype="float32",
                        blocking=True,
                    )
                    # Compute Root Mean Square (RMS) amplitude
                    rms = float(np.sqrt(np.mean(mic_chunk**2)))
                    if rms > settings.VOICE_INTERRUPT_THRESHOLD:
                        logger.info(
                            f"Voice interruption detected! Mic RMS: {rms:.4f} > threshold: {settings.VOICE_INTERRUPT_THRESHOLD}"
                        )
                        self.stop_playback()
                        print(" [Siri Voice Interrupted by Speech] ")
                        break
                except Exception:
                    # If recording fails, just sleep
                    time.sleep(chunk_duration)

                elapsed += chunk_duration

            self._is_playing = False

        except Exception as e:
            logger.error(f"TTS execution failed: {e}")

    def is_interrupted(self) -> bool:
        return self._interrupted

    def stop_playback(self) -> None:
        logger.info("Stopping audio playback")
        self._interrupted = True
        self._is_playing = False
        if self._has_hardware:
            try:
                sd.stop()
            except Exception:
                pass
