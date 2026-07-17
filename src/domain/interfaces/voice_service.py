from abc import ABC, abstractmethod
from typing import Optional


class AbstractVoiceService(ABC):
    """Port interface defining voice automation and speech synthesis services.

    Decouples application logic from specific speech recognition, microphone,
    and text-to-speech libraries.
    """

    @abstractmethod
    def is_audio_available(self) -> bool:
        """Returns True if local audio input/output devices are available on the host OS."""
        pass

    @abstractmethod
    def listen_for_wake_word(self, wake_word: str) -> bool:
        """Continuously monitors microphone until the wake word is detected."""
        pass

    @abstractmethod
    def record_command(self, duration: Optional[float] = None) -> Optional[str]:
        """Records microphone input for a specified duration and returns transcribed text command."""
        pass

    @abstractmethod
    def speak_text(self, text: str) -> None:
        """Converts text to speech (TTS) and plays it back to the user."""
        pass

    @abstractmethod
    def is_interrupted(self) -> bool:
        """Returns True if the user interrupted the current speech playback."""
        pass

    @abstractmethod
    def stop_playback(self) -> None:
        """Immediately stops any ongoing audio playback/speech synthesis."""
        pass
