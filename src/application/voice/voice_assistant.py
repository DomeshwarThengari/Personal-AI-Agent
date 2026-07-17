import time
from typing import Optional
from src.domain.interfaces.voice_service import AbstractVoiceService
from src.domain.interfaces.memory_service import AbstractMemoryService
from src.application.agent_workflow import AgentWorkflowRunner
from src.infrastructure.database.sqlite_repo import SQLiteChatRepository
from src.domain.entities import Message
from src.config.settings import settings
from src.utils.logging import get_logger

logger = get_logger("voice_assistant")


class VoiceAssistant:
    """Orchestrates the Siri-like voice conversation loop.

    Coordinates wake word detection, continuous speech listening, LLM workflows,
    TTS output, and voice interruption monitoring.
    """

    def __init__(
        self,
        voice_service: AbstractVoiceService,
        workflow_runner: AgentWorkflowRunner,
        chat_repo: SQLiteChatRepository,
        memory_service: Optional[AbstractMemoryService] = None,
        session_id: str = "voice_session",
    ) -> None:
        self._voice_service = voice_service
        self._workflow_runner = workflow_runner
        self._chat_repo = chat_repo
        self._memory_service = memory_service
        self._session_id = session_id

        self._wake_word = settings.VOICE_WAKE_WORD
        self._is_running = False

    def start(self) -> None:
        """Starts the main passive wake word loop."""
        self._is_running = True
        logger.info("Starting Voice Assistant passive listening loop.")
        print("\n==============================================")
        print("Siri-like Voice Assistant Active")
        print(f"Wake word: '{self._wake_word}'")
        print(f"Hardware Audio Present: {self._voice_service.is_audio_available()}")
        print("==============================================")

        try:
            while self._is_running:
                # Passive listening for wake word
                triggered = self._voice_service.listen_for_wake_word(self._wake_word)
                if triggered and self._is_running:
                    logger.info("Wake word detected! Entering active session.")
                    self._voice_service.speak_text("Mh-hmm? How can I help you?")
                    self._run_dialogue_session()
        except KeyboardInterrupt:
            logger.info("Voice Assistant stopped via keyboard interrupt.")
            self.stop()

    def stop(self) -> None:
        """Stops the voice assistant loops."""
        self._is_running = False
        self._voice_service.stop_playback()
        logger.info("Voice Assistant stopped.")

    def _run_dialogue_session(self) -> None:
        """Runs the active, continuous conversation dialogue session.

        Allows continuous conversation without requiring the wake word
        for each command, until it times out due to silence.
        """
        consecutive_silence = 0
        max_silence_attempts = 2  # Go back to sleep after 2 silent prompts

        while self._is_running:
            # 1. Record voice command
            # Using a slightly shorter timeout for active dialogue prompts (e.g. 5 seconds)
            command = self._voice_service.record_command(duration=5.0)

            # Check interruption state
            if self._voice_service.is_interrupted():
                logger.info("Active dialogue session interrupted.")
                break

            if not command:
                consecutive_silence += 1
                if consecutive_silence >= max_silence_attempts:
                    logger.info("Active session timed out due to silence.")
                    self._voice_service.speak_text(
                        "Going to sleep. Let me know if you need anything!"
                    )
                    break
                else:
                    self._voice_service.speak_text(
                        "I didn't catch that. Could you repeat?"
                    )
                    continue

            consecutive_silence = 0  # Reset silence counter

            if self._memory_service:
                self._memory_service.log_command(
                    command=command, executed_by="user", status="success"
                )

            # 2. Check for explicit exit commands
            clean_cmd = command.lower().strip()
            if clean_cmd in ("exit", "quit", "goodbye", "go to sleep", "sleep"):
                self._voice_service.speak_text("Goodbye!")
                break

            logger.info(f"Processing command: '{command}'")
            print(f"Executing: '{command}'...")

            # 3. Retrieve conversation history context
            current_history = self._chat_repo.get_session_messages(self._session_id)

            # 4. Invoke LLM LangGraph runner
            try:
                # Run the agent workflow
                response = self._workflow_runner.run(
                    session_id=self._session_id,
                    history=current_history,
                    user_input=command,
                    system_instruction=(
                        "You are a helpful, brief voice assistant like Siri. "
                        "Keep your responses very concise, professional, and friendly. "
                        "Avoid markdown syntax or structural lists in responses since they will be read out loud."
                    ),
                )

                response_text = response.message.content
                logger.info(f"Agent response: {response_text}")

                # Save dialog history
                self._chat_repo.save_message(
                    self._session_id, Message(role="user", content=command)
                )
                self._chat_repo.save_message(self._session_id, response.message)

                # 5. Speak response with barge-in support
                self._voice_service.speak_text(response_text)

            except Exception as e:
                logger.error(f"Error processing command in workflow: {e}")
                self._voice_service.speak_text(
                    "Sorry, I ran into an error processing that command."
                )

            # Pause briefly before listening again
            time.sleep(0.5)
