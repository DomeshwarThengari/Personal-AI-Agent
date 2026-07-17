import sys
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
from src.application.tools.browser_tools import (
    BrowserOpenTool,
    BrowserSearchGoogleTool,
    BrowserSearchYoutubeTool,
    BrowserPlayYoutubeTool,
    BrowserClickTool,
    BrowserScrollTool,
    BrowserFillTool,
    BrowserDownloadTool,
    BrowserScreenshotTool,
    BrowserReadContentTool,
)
from src.application.action_engine.engine import ActionEngine
from src.config.settings import settings
from src.infrastructure.database.sqlite_repo import SQLiteChatRepository
from src.infrastructure.llm.gemini import GeminiLLMService
from src.infrastructure.browser.playwright_service import PlaywrightBrowserService
from src.infrastructure.voice.voice_service import VoiceService
from src.application.voice.voice_assistant import VoiceAssistant
from src.utils.logging import setup_logging

# Color Escape Codes
INFO_COLOR = "\x1b[1;36m"  # Bold Cyan
SYSTEM_COLOR = "\x1b[1;33m"  # Bold Yellow
ERROR_COLOR = "\x1b[1;31m"  # Bold Red
RESET = "\x1b[0m"


def run_voice_chat() -> None:
    setup_logging()

    # 1. Check API Key
    if (
        not settings.GEMINI_API_KEY
        or settings.GEMINI_API_KEY == "your_gemini_api_key_here"
    ):
        print(
            f"{ERROR_COLOR}Error: GEMINI_API_KEY is not configured in your .env file."
        )
        print(f"Please update the .env file with your API key to start.{RESET}")
        return

    # Option to force mock voice mode (useful if running in containers / without microphone)
    force_mock = "--mock" in sys.argv

    browser_service = None
    voice_service = None
    voice_assistant = None

    try:
        chat_repo = SQLiteChatRepository()
        session_id = "voice_session"

        # Initialize voice service
        voice_service = VoiceService(force_mock=force_mock)

        # Initialize Gemini LLM, Tool Registry, Action Engine, and LangGraph runner
        llm_service = GeminiLLMService()
        browser_service = PlaywrightBrowserService()

        registry = ToolRegistry()
        registry.register(SystemTimeTool())
        registry.register(AppLauncherTool())
        registry.register(SearchAppsTool())
        registry.register(LaunchAppTool())
        registry.register(CloseAppTool())
        registry.register(FocusAppTool())
        # Browser tools registration
        registry.register(BrowserOpenTool(browser_service))
        registry.register(BrowserSearchGoogleTool(browser_service))
        registry.register(BrowserSearchYoutubeTool(browser_service))
        registry.register(BrowserPlayYoutubeTool(browser_service))
        registry.register(BrowserClickTool(browser_service))
        registry.register(BrowserScrollTool(browser_service))
        registry.register(BrowserFillTool(browser_service))
        registry.register(BrowserDownloadTool(browser_service))
        registry.register(BrowserScreenshotTool(browser_service))
        registry.register(BrowserReadContentTool(browser_service))

        action_engine = ActionEngine(registry=registry)

        workflow_runner = AgentWorkflowRunner(
            llm_service=llm_service,
            action_engine=action_engine,
            tools=registry.list_tools(),
        )

        voice_assistant = VoiceAssistant(
            voice_service=voice_service,
            workflow_runner=workflow_runner,
            chat_repo=chat_repo,
            session_id=session_id,
        )

        # Start continuous voice loop
        voice_assistant.start()

    except Exception as e:
        print(f"{ERROR_COLOR}Failed to initialize voice chat: {e}{RESET}")
    finally:
        # Clean up browser and voice sessions on exit
        if browser_service:
            try:
                browser_service.close()
            except Exception:
                pass
        if voice_assistant:
            try:
                voice_assistant.stop()
            except Exception:
                pass


if __name__ == "__main__":
    run_voice_chat()
