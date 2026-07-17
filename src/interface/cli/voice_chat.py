import sys
from src.application.multi_agent.workflow import MultiAgentWorkflowRunner
from src.application.tools.devops_tools import (
    DevOpsRunCommandTool,
    DockerListContainersTool,
    DockerRestartContainerTool,
    DockerViewLogsTool,
    K8sListPodsTool,
    K8sDescribePodTool,
    K8sRestartDeploymentTool,
    AWSListEC2Tool,
    AWSS3ListBucketsTool,
    AWSCloudWatchLogsTool,
    JenkinsRunPipelineTool,
    JenkinsViewBuildLogsTool,
    GitCommitTool,
    GitPushTool,
    GitCloneTool,
    TerraformPlanTool,
    TerraformApplyTool,
    AnsibleRunPlaybookTool,
)
from src.application.tools.vision_tools import (
    VisionTakeScreenshotTool,
    VisionAnalyzeImageTool,
)
from src.application.tools.routing_tools import RouteToAgentTool
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
from src.application.tools.memory_tools import (
    PreferenceSetTool,
    PreferenceGetTool,
    ProjectSaveTool,
    CommandHistoryTool,
    MemorySaveTool,
    MemorySearchTool,
)
from src.application.tools.system_tools import (
    SystemCreateFolderTool,
    SystemRenameFileTool,
    SystemCopyFileTool,
    SystemMoveFileTool,
    SystemDeleteFileTool,
    SystemSearchFilesTool,
    SystemOpenDownloadsTool,
    SystemOpenDocumentsTool,
    SystemReadCpuTool,
    SystemReadRamTool,
    SystemReadDiskTool,
    SystemReadBatteryTool,
    SystemMonitorProcessesTool,
)
from src.application.tools.planner_tools import PlannerExecuteTaskTool
from src.infrastructure.database.sqlite_memory import SQLiteMemoryService
from src.infrastructure.system.local_system_service import LocalSystemService
from src.infrastructure.planner.gemini_planner import GeminiPlannerService
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
        memory_service = SQLiteMemoryService()
        system_service = LocalSystemService()
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

        # Memory tools registration
        registry.register(PreferenceSetTool(memory_service))
        registry.register(PreferenceGetTool(memory_service))
        registry.register(ProjectSaveTool(memory_service))
        registry.register(CommandHistoryTool(memory_service))
        registry.register(MemorySaveTool(memory_service))
        registry.register(MemorySearchTool(memory_service))

        # System tools registration
        registry.register(SystemCreateFolderTool(system_service))
        registry.register(SystemRenameFileTool(system_service))
        registry.register(SystemCopyFileTool(system_service))
        registry.register(SystemMoveFileTool(system_service))
        registry.register(SystemDeleteFileTool(system_service))
        registry.register(SystemSearchFilesTool(system_service))
        registry.register(SystemOpenDownloadsTool(system_service))
        registry.register(SystemOpenDocumentsTool(system_service))
        registry.register(SystemReadCpuTool(system_service))
        registry.register(SystemReadRamTool(system_service))
        registry.register(SystemReadDiskTool(system_service))
        registry.register(SystemReadBatteryTool(system_service))
        registry.register(SystemMonitorProcessesTool(system_service))

        planner_service = GeminiPlannerService()
        action_engine = ActionEngine(registry=registry, memory_service=memory_service)

        registry.register(
            PlannerExecuteTaskTool(
                action_engine=action_engine,
                planner_service=planner_service,
                tools=registry.list_tools(),
            )
        )
        registry.register(RouteToAgentTool())
        registry.register(DevOpsRunCommandTool())
        registry.register(DockerListContainersTool())
        registry.register(DockerRestartContainerTool())
        registry.register(DockerViewLogsTool())
        registry.register(K8sListPodsTool())
        registry.register(K8sDescribePodTool())
        registry.register(K8sRestartDeploymentTool())
        registry.register(AWSListEC2Tool())
        registry.register(AWSS3ListBucketsTool())
        registry.register(AWSCloudWatchLogsTool())
        registry.register(JenkinsRunPipelineTool())
        registry.register(JenkinsViewBuildLogsTool())
        registry.register(GitCommitTool())
        registry.register(GitPushTool())
        registry.register(GitCloneTool())
        registry.register(TerraformPlanTool())
        registry.register(TerraformApplyTool())
        registry.register(AnsibleRunPlaybookTool())
        registry.register(VisionTakeScreenshotTool())
        registry.register(VisionAnalyzeImageTool())

        workflow_runner = MultiAgentWorkflowRunner(
            llm_service=llm_service,
            action_engine=action_engine,
            tools=registry.list_tools(),
        )

        voice_assistant = VoiceAssistant(
            voice_service=voice_service,
            workflow_runner=workflow_runner,
            chat_repo=chat_repo,
            memory_service=memory_service,
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
