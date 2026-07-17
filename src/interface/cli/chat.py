from src.application.agent_workflow import AgentWorkflowRunner
from src.application.tools.system_time import SystemTimeTool
from src.application.tools.app_launcher import AppLauncherTool
from src.application.tools.registry import ToolRegistry
from src.application.tools.app_agent_tools import (
    SearchAppsTool,
    LaunchAppTool,
    CloseAppTool,
    FocusAppTool,
)
from src.application.action_engine.engine import ActionEngine
from src.config.settings import settings
from src.domain.entities import Message
from src.infrastructure.database.sqlite_repo import SQLiteChatRepository
from src.infrastructure.llm.gemini import GeminiLLMError, GeminiLLMService
from src.utils.logging import setup_logging

# Color Escape Codes for Rich Terminal Styling
USER_COLOR = "\x1b[1;34m"  # Bold Blue
AGENT_COLOR = "\x1b[1;32m"  # Bold Green
INFO_COLOR = "\x1b[0;36m"  # Cyan
ERROR_COLOR = "\x1b[1;31m"  # Bold Red
SYSTEM_COLOR = "\x1b[1;35m"  # Bold Magenta
RESET = "\x1b[0m"

SYSTEM_INSTRUCTION = (
    "You are a premium, production-grade Personal AI Assistant. "
    "Respond with clear, helpful, and concise answers."
)


def run_chat_loop() -> None:
    """Runs the terminal-based interactive chat assistant with LangGraph and SQLite."""
    # Ensure logging is initialized
    setup_logging()

    print(f"{SYSTEM_COLOR}==================================================")
    print("Welcome to your Personal AI Assistant CLI Chat (LangGraph)")
    print(f"Type '/exit' or '/quit' to close the session.{RESET}")
    print(f"{SYSTEM_COLOR}=================================================={RESET}")

    # Check API Key configuration
    if (
        not settings.GEMINI_API_KEY
        or settings.GEMINI_API_KEY == "your_gemini_api_key_here"
    ):
        print(
            f"{ERROR_COLOR}Error: GEMINI_API_KEY is not configured in your .env file."
        )
        print(f"Please update the .env file with your API key to start.{RESET}")
        return

    try:
        # Initialize Database repository
        chat_repo = SQLiteChatRepository()

        # Ask the user for a session ID (default to "default_session")
        session_id = (
            input(f"{INFO_COLOR}Enter Session ID [default_session]: {RESET}").strip()
            or "default_session"
        )

        # Retrieve and display history if it exists
        history = chat_repo.get_session_messages(session_id)
        if history:
            print(
                f"\n{SYSTEM_COLOR}--- Restored past session history ({len(history)} messages) ---{RESET}"
            )
            for msg in history:
                color = USER_COLOR if msg.role == "user" else AGENT_COLOR
                prefix = "You" if msg.role == "user" else "AI"
                print(f"{color}{prefix}: {RESET}{msg.content}")
            print(
                f"{SYSTEM_COLOR}------------------------------------------------------------{RESET}"
            )

        # Initialize Gemini LLM, Tool Registry, Action Engine, and LangGraph runner
        llm_service = GeminiLLMService()

        registry = ToolRegistry()
        registry.register(SystemTimeTool())
        registry.register(AppLauncherTool())
        registry.register(SearchAppsTool())
        registry.register(LaunchAppTool())
        registry.register(CloseAppTool())
        registry.register(FocusAppTool())

        action_engine = ActionEngine(registry=registry)

        workflow_runner = AgentWorkflowRunner(
            llm_service=llm_service,
            action_engine=action_engine,
            tools=registry.list_tools(),
        )

    except Exception as e:
        print(f"{ERROR_COLOR}Failed to initialize chat components: {e}{RESET}")
        return

    while True:
        try:
            # Prompt user
            user_input = input(f"\n{USER_COLOR}You: {RESET}").strip()

            if not user_input:
                continue

            # Check exit commands
            if user_input.lower() in ("/exit", "/quit"):
                print(f"\n{SYSTEM_COLOR}Goodbye!{RESET}")
                break

            # Print thinking indicator
            print(
                f"{INFO_COLOR}Assistant is thinking (LangGraph reasoning)...{RESET}",
                end="\r",
            )

            # Load history context from database dynamically in case it changed
            current_history = chat_repo.get_session_messages(session_id)

            # Execute Workflow
            response = workflow_runner.run(
                session_id=session_id,
                history=current_history,
                user_input=user_input,
                system_instruction=SYSTEM_INSTRUCTION,
            )

            # Clear thinking indicator
            print(" " * 60, end="\r")

            # Output response
            print(f"{AGENT_COLOR}AI: {RESET}{response.message.content}")

            # Save new messages to SQLite Database
            chat_repo.save_message(session_id, Message(role="user", content=user_input))
            chat_repo.save_message(session_id, response.message)

        except KeyboardInterrupt:
            print(f"\n{SYSTEM_COLOR}Goodbye! (Session interrupted){RESET}")
            break
        except GeminiLLMError as ge:
            print(f"\n{ERROR_COLOR}Gemini Error: {ge}{RESET}")
        except Exception as e:
            print(f"\n{ERROR_COLOR}Unexpected error: {e}{RESET}")


if __name__ == "__main__":
    run_chat_loop()
