from unittest.mock import patch, MagicMock
from src.infrastructure.voice.voice_service import VoiceService


def test_voice_service_mock_init() -> None:
    # Force mock mode
    service = VoiceService(force_mock=True)
    assert not service.is_audio_available()


def test_voice_service_speak_and_history() -> None:
    service = VoiceService(force_mock=True)
    assert len(service.spoken_history) == 0

    service.speak_text("Hello there.")
    assert len(service.spoken_history) == 1
    assert service.spoken_history[0] == "Hello there."


def test_voice_service_interruption() -> None:
    service = VoiceService(force_mock=True)
    assert not service.is_interrupted()

    service.stop_playback()
    assert service.is_interrupted()


@patch("builtins.input", return_value="hey assistant")
def test_voice_service_wake_word_simulated(mock_input: MagicMock) -> None:
    service = VoiceService(force_mock=True)
    res = service.listen_for_wake_word("hey assistant")
    assert res is True


@patch("builtins.input", return_value="hello assistant please launch chromium")
def test_voice_service_record_command_simulated(mock_input: MagicMock) -> None:
    service = VoiceService(force_mock=True)
    res = service.record_command()
    assert res == "hello assistant please launch chromium"
