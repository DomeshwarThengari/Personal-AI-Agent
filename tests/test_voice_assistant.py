from unittest.mock import MagicMock, call
from src.application.voice.voice_assistant import VoiceAssistant
from src.domain.interfaces.voice_service import AbstractVoiceService
from src.application.agent_workflow import AgentWorkflowRunner
from src.infrastructure.database.sqlite_repo import SQLiteChatRepository
from src.domain.entities import AgentResponse, Message


def test_voice_assistant_dialogue_flow() -> None:
    # 1. Setup mocks
    mock_voice = MagicMock(spec=AbstractVoiceService)
    mock_workflow = MagicMock(spec=AgentWorkflowRunner)
    mock_repo = MagicMock(spec=SQLiteChatRepository)

    # Configure wake word and command sequence
    # 1st loop: wake word triggered.
    # Inside active session:
    #   - 1st record command: "hello"
    #   - 2nd record command: None (silence)
    #   - 3rd record command: None (silence again -> timeout sleep)
    mock_voice.listen_for_wake_word.side_effect = [
        True,
        False,
    ]  # stop wake loop after first run
    mock_voice.record_command.side_effect = ["hello", None, None]
    mock_voice.is_interrupted.return_value = False
    mock_voice.is_audio_available.return_value = False

    # Mock workflow response
    agent_response = AgentResponse(
        message=Message(role="assistant", content="Hi human!"),
        actions=[],
    )
    mock_workflow.run.return_value = agent_response
    mock_repo.get_session_messages.return_value = []

    # 2. Instantiate and run VoiceAssistant
    assistant = VoiceAssistant(
        voice_service=mock_voice,
        workflow_runner=mock_workflow,
        chat_repo=mock_repo,
        session_id="test_session",
    )

    call_count = 0

    def listen_side_effect(wake_word: str) -> bool:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return True
        assistant.stop()
        return False

    mock_voice.listen_for_wake_word.side_effect = listen_side_effect

    assistant.start()

    # 3. Assertions
    # Verify siri greeted the user
    mock_voice.speak_text.assert_has_calls(
        [
            call("Mh-hmm? How can I help you?"),
            call("Hi human!"),
            call("I didn't catch that. Could you repeat?"),
            call("Going to sleep. Let me know if you need anything!"),
        ]
    )

    # Verify agent workflow was run with command
    mock_workflow.run.assert_called_once_with(
        session_id="test_session",
        history=[],
        user_input="hello",
        system_instruction=(
            "You are a helpful, brief voice assistant like Siri. "
            "Keep your responses very concise, professional, and friendly. "
            "Avoid markdown syntax or structural lists in responses since they will be read out loud."
        ),
    )

    # Verify messages saved
    assert mock_repo.save_message.call_count == 2
