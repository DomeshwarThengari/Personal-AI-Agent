import sys
from typing import List, Literal, cast
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTextEdit,
    QLineEdit,
    QPushButton,
    QLabel,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QComboBox,
    QCheckBox,
    QSplitter,
    QMessageBox,
    QHeaderView,
    QInputDialog,
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer

# Import existing application dependencies
from src.infrastructure.database.sqlite_repo import SQLiteChatRepository
from src.infrastructure.database.sqlite_memory import SQLiteMemoryService
from src.infrastructure.system.local_system_service import LocalSystemService
from src.infrastructure.planner.gemini_planner import GeminiPlannerService
from src.infrastructure.llm.gemini import GeminiLLMService
from src.infrastructure.browser.playwright_service import PlaywrightBrowserService
from src.infrastructure.voice.voice_service import VoiceService
from src.application.tools.registry import ToolRegistry
from src.application.action_engine.engine import ActionEngine
from src.application.multi_agent.workflow import MultiAgentWorkflowRunner
from src.application.services.security_manager import SecurityManager, UserRole
from src.domain.entities import Message

# Import all tools to register them
from src.application.tools.routing_tools import RouteToAgentTool
from src.application.tools.system_time import SystemTimeTool
from src.application.tools.app_launcher import AppLauncherTool
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
from src.application.tools.personal_assistant_tools import (
    AssistantCalendarTool,
    AssistantTodoTool,
    AssistantNotesTool,
    AssistantGetWeatherTool,
    AssistantGetNewsTool,
    AssistantSummarizeEmailsTool,
    AssistantSendNotificationTool,
    AssistantDailyBriefingTool,
    AssistantTriggerRoutineTool,
)
from src.application.tools.security_tools import (
    AssistantViewSecurityStatusTool,
    AssistantConfigureSecurityTool,
    AssistantViewAuditLogsTool,
)


class AgentWorker(QThread):
    """Thread worker to execute LLM & multi-agent logic in a non-blocking background thread."""

    response_received = Signal(str, str)  # role, text
    status_changed = Signal(str)  # status description
    finished = Signal()

    def __init__(
        self,
        runner: MultiAgentWorkflowRunner,
        session_id: str,
        user_input: str,
        history: List[Message],
    ) -> None:
        super().__init__()
        self.runner = runner
        self.session_id = session_id
        self.user_input = user_input
        self.history = history

    def run(self) -> None:
        self.status_changed.emit("Running Agent Workflow...")
        try:
            res = self.runner.run(
                session_id=self.session_id,
                history=self.history,
                user_input=self.user_input,
                system_instruction="You are JOJO, a helpful desktop personal AI assistant.",
            )
            self.response_received.emit("assistant", res.message.content)
        except Exception as e:
            self.response_received.emit("system", f"Workflow execution error: {e}")
        self.status_changed.emit("Idle")
        self.finished.emit()


class VoiceInputWorker(QThread):
    """Thread worker to capture speech input asynchronously without blocking Qt events."""

    transcription_received = Signal(str)
    status_changed = Signal(str)
    finished = Signal()

    def __init__(self, voice_service: VoiceService) -> None:
        super().__init__()
        self.voice_service = voice_service

    def run(self) -> None:
        self.status_changed.emit("Listening...")
        if self.voice_service.is_audio_available():
            try:
                # Capture standard audio input
                transcription = self.voice_service.record_command(duration=4.0)
                if transcription:
                    self.transcription_received.emit(transcription)
                else:
                    self.transcription_received.emit("")
            except Exception:
                self.transcription_received.emit("")
        else:
            # Headless or missing hardware fallback (simulate voice dialog)
            self.status_changed.emit("Simulating Voice...")
            # We don't call input() here since it blocks CLI. We return empty to let GUI handle it.
            self.transcription_received.emit("__simulate__")

        self.status_changed.emit("Idle")
        self.finished.emit()


class MainWindow(QMainWindow):
    """Main window for the desktop agent interface."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("AI Agent JOJO - Desktop Assistant")
        self.setMinimumSize(1024, 720)

        # 1. Initialize core layers
        self.chat_repo = SQLiteChatRepository()
        self.memory_service = SQLiteMemoryService()
        self.browser_service = PlaywrightBrowserService()
        self.system_service = LocalSystemService()
        self.llm_service = GeminiLLMService()
        self.voice_service = VoiceService()
        self.security_manager = SecurityManager()

        self.session_id = "desktop_session"
        self.history: List[Message] = self.chat_repo.get_session_messages(
            self.session_id
        )

        # Build Tool Registry
        self.registry = ToolRegistry()
        self._register_all_tools()

        # Build Action Engine & Planner
        self.planner_service = GeminiPlannerService()
        self.action_engine = ActionEngine(
            registry=self.registry,
            memory_service=self.memory_service,
            security_manager=self.security_manager,
        )

        # Register execution tool
        self.registry.register(
            PlannerExecuteTaskTool(
                action_engine=self.action_engine,
                planner_service=self.planner_service,
                tools=self.registry.list_tools(),
            )
        )

        # Build workflow runner
        self.runner = MultiAgentWorkflowRunner(
            llm_service=self.llm_service,
            action_engine=self.action_engine,
            tools=self.registry.list_tools(),
        )

        # 2. Build layouts and tabs
        self._init_ui()
        self._apply_theme()

        # 3. Restore chat history to UI view
        self._restore_chat_view()

        # 4. Timer to update status and system monitoring stats
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self._update_system_stats)
        self.status_timer.start(5000)  # Every 5 seconds

    def _register_all_tools(self) -> None:
        # Base/App tools
        self.registry.register(SystemTimeTool())
        self.registry.register(AppLauncherTool())
        self.registry.register(SearchAppsTool())
        self.registry.register(LaunchAppTool())
        self.registry.register(CloseAppTool())
        self.registry.register(FocusAppTool())

        # Browser tools
        self.registry.register(BrowserOpenTool(self.browser_service))
        self.registry.register(BrowserSearchGoogleTool(self.browser_service))
        self.registry.register(BrowserSearchYoutubeTool(self.browser_service))
        self.registry.register(BrowserPlayYoutubeTool(self.browser_service))
        self.registry.register(BrowserClickTool(self.browser_service))
        self.registry.register(BrowserScrollTool(self.browser_service))
        self.registry.register(BrowserFillTool(self.browser_service))
        self.registry.register(BrowserDownloadTool(self.browser_service))
        self.registry.register(BrowserScreenshotTool(self.browser_service))
        self.registry.register(BrowserReadContentTool(self.browser_service))

        # Memory tools
        self.registry.register(PreferenceSetTool(self.memory_service))
        self.registry.register(PreferenceGetTool(self.memory_service))
        self.registry.register(ProjectSaveTool(self.memory_service))
        self.registry.register(CommandHistoryTool(self.memory_service))
        self.registry.register(MemorySaveTool(self.memory_service))
        self.registry.register(MemorySearchTool(self.memory_service))

        # System tools
        self.registry.register(SystemCreateFolderTool(self.system_service))
        self.registry.register(SystemRenameFileTool(self.system_service))
        self.registry.register(SystemCopyFileTool(self.system_service))
        self.registry.register(SystemMoveFileTool(self.system_service))
        self.registry.register(SystemDeleteFileTool(self.system_service))
        self.registry.register(SystemSearchFilesTool(self.system_service))
        self.registry.register(SystemOpenDownloadsTool(self.system_service))
        self.registry.register(SystemOpenDocumentsTool(self.system_service))
        self.registry.register(SystemReadCpuTool(self.system_service))
        self.registry.register(SystemReadRamTool(self.system_service))
        self.registry.register(SystemReadDiskTool(self.system_service))
        self.registry.register(SystemReadBatteryTool(self.system_service))
        self.registry.register(SystemMonitorProcessesTool(self.system_service))

        # Other tools
        self.registry.register(RouteToAgentTool())
        self.registry.register(DevOpsRunCommandTool())
        self.registry.register(DockerListContainersTool())
        self.registry.register(DockerRestartContainerTool())
        self.registry.register(DockerViewLogsTool())
        self.registry.register(K8sListPodsTool())
        self.registry.register(K8sDescribePodTool())
        self.registry.register(K8sRestartDeploymentTool())
        self.registry.register(AWSListEC2Tool())
        self.registry.register(AWSS3ListBucketsTool())
        self.registry.register(AWSCloudWatchLogsTool())
        self.registry.register(JenkinsRunPipelineTool())
        self.registry.register(JenkinsViewBuildLogsTool())
        self.registry.register(GitCommitTool())
        self.registry.register(GitPushTool())
        self.registry.register(GitCloneTool())
        self.registry.register(TerraformPlanTool())
        self.registry.register(TerraformApplyTool())
        self.registry.register(AnsibleRunPlaybookTool())

        # Multimodal Vision tools
        self.registry.register(VisionTakeScreenshotTool())
        self.registry.register(VisionAnalyzeImageTool())

        # Assistant tools
        self.registry.register(AssistantCalendarTool())
        self.registry.register(AssistantTodoTool())
        self.registry.register(AssistantNotesTool())
        self.registry.register(AssistantGetWeatherTool())
        self.registry.register(AssistantGetNewsTool())
        self.registry.register(AssistantSummarizeEmailsTool())
        self.registry.register(AssistantSendNotificationTool())
        self.registry.register(AssistantDailyBriefingTool())
        self.registry.register(AssistantTriggerRoutineTool())

        # Security tools
        self.registry.register(AssistantViewSecurityStatusTool())
        self.registry.register(AssistantConfigureSecurityTool())
        self.registry.register(AssistantViewAuditLogsTool())

    def _init_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)

        # HEADER
        header_layout = QHBoxLayout()
        self.lbl_title = QLabel("AI Agent JOJO")
        self.lbl_title.setStyleSheet("font-weight: bold; font-size: 20px;")

        self.lbl_agent_status = QLabel("Agent: Idle")
        self.lbl_agent_status.setStyleSheet("color: #a6e3a1; font-weight: bold;")

        header_layout.addWidget(self.lbl_title)
        header_layout.addStretch()
        header_layout.addWidget(self.lbl_agent_status)
        main_layout.addLayout(header_layout)

        # SPLITTER FOR CHAT AND SIDEBAR
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)

        # LEFT SIDE - CHAT WINDOW
        chat_widget = QWidget()
        chat_layout = QVBoxLayout(chat_widget)
        chat_layout.setContentsMargins(0, 0, 0, 0)

        self.txt_chat_history = QTextEdit()
        self.txt_chat_history.setReadOnly(True)
        chat_layout.addWidget(self.txt_chat_history)

        input_layout = QHBoxLayout()
        self.txt_input = QLineEdit()
        self.txt_input.setPlaceholderText("Type a message or command...")
        self.txt_input.returnPressed.connect(self._send_message)

        self.btn_send = QPushButton("Send")
        self.btn_send.clicked.connect(self._send_message)

        self.btn_voice = QPushButton("🎙️ Voice")
        self.btn_voice.clicked.connect(self._toggle_voice_input)

        input_layout.addWidget(self.txt_input)
        input_layout.addWidget(self.btn_send)
        input_layout.addWidget(self.btn_voice)
        chat_layout.addLayout(input_layout)

        splitter.addWidget(chat_widget)

        # RIGHT SIDE - CONTROL & DISPLAY TABS
        self.tabs = QTabWidget()
        splitter.addWidget(self.tabs)

        # Tab 1: Settings
        self._build_settings_tab()

        # Tab 2: Security Logs
        self._build_logs_tab()

        # Tab 3: Memory Viewer
        self._build_memory_tab()

        # Tab 4: Agent Status
        self._build_status_tab()

        splitter.setSizes([600, 424])

    def _build_settings_tab(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Role
        role_layout = QHBoxLayout()
        role_layout.addWidget(QLabel("User Role:"))
        self.cmb_role = QComboBox()
        self.cmb_role.addItems(["viewer", "operator", "admin"])
        # Set active role
        active_role = self.security_manager.get_user_role().value
        self.cmb_role.setCurrentText(active_role)
        self.cmb_role.currentTextChanged.connect(self._role_changed)
        role_layout.addWidget(self.cmb_role)
        layout.addLayout(role_layout)

        # Safe Mode
        safe_mode_layout = QHBoxLayout()
        safe_mode_layout.addWidget(QLabel("Safe Mode:"))
        self.chk_safe_mode = QCheckBox()
        self.chk_safe_mode.setChecked(self.security_manager.get_safe_mode())
        self.chk_safe_mode.stateChanged.connect(self._safe_mode_toggled)
        safe_mode_layout.addWidget(self.chk_safe_mode)
        layout.addLayout(safe_mode_layout)

        # Credentials List
        layout.addWidget(QLabel("\n=== Masked Credentials ==="))
        self.lbl_credentials = QLabel()
        self._update_masked_credentials_display()
        layout.addWidget(self.lbl_credentials)

        layout.addStretch()
        self.tabs.addTab(tab, "Settings")

    def _build_logs_tab(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        self.tbl_logs = QTableWidget()
        self.tbl_logs.setColumnCount(4)
        self.tbl_logs.setHorizontalHeaderLabels(["Time", "Tool", "Role", "Status"])
        self.tbl_logs.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        layout.addWidget(self.tbl_logs)

        btn_refresh_logs = QPushButton("Refresh Audit Logs")
        btn_refresh_logs.clicked.connect(self._refresh_logs)
        layout.addWidget(btn_refresh_logs)

        self.tabs.addTab(tab, "Audit Logs")
        self._refresh_logs()

    def _build_memory_tab(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        self.txt_memory = QTextEdit()
        self.txt_memory.setReadOnly(True)
        layout.addWidget(self.txt_memory)

        btn_refresh_mem = QPushButton("Refresh Preferences & Projects")
        btn_refresh_mem.clicked.connect(self._refresh_memory)
        layout.addWidget(btn_refresh_mem)

        self.tabs.addTab(tab, "Memory Viewer")
        self._refresh_memory()

    def _build_status_tab(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        layout.addWidget(QLabel("=== Agent System Telemetry ==="))
        self.lbl_cpu = QLabel("CPU: Querying...")
        self.lbl_ram = QLabel("RAM: Querying...")
        self.lbl_disk = QLabel("Disk: Querying...")
        self.lbl_battery = QLabel("Battery: Querying...")

        layout.addWidget(self.lbl_cpu)
        layout.addWidget(self.lbl_ram)
        layout.addWidget(self.lbl_disk)
        layout.addWidget(self.lbl_battery)

        layout.addStretch()
        self.tabs.addTab(tab, "Status Monitor")
        self._update_system_stats()

    def _apply_theme(self) -> None:
        theme = """
        QMainWindow {
            background-color: #1e1e2e;
        }
        QWidget {
            font-family: 'Segoe UI', Arial, sans-serif;
            color: #cdd6f4;
        }
        QTextEdit, QListWidget, QTableWidget {
            background-color: #181825;
            border: 1px solid #313244;
            border-radius: 8px;
            padding: 8px;
            color: #cdd6f4;
        }
        QLineEdit {
            background-color: #181825;
            border: 1px solid #313244;
            border-radius: 6px;
            padding: 8px;
            color: #cdd6f4;
        }
        QPushButton {
            background-color: #89b4fa;
            color: #11111b;
            border: none;
            border-radius: 6px;
            padding: 8px 16px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #b4befe;
        }
        QPushButton:pressed {
            background-color: #74c7ec;
        }
        QTabWidget::pane {
            border: 1px solid #313244;
            border-radius: 8px;
            background-color: #252538;
        }
        QTabBar::tab {
            background-color: #11111b;
            border: 1px solid #313244;
            border-top-left-radius: 6px;
            border-top-right-radius: 6px;
            padding: 6px 12px;
            margin-right: 2px;
        }
        QTabBar::tab:selected {
            background-color: #252538;
            border-bottom-color: #252538;
        }
        QCheckBox, QComboBox {
            padding: 4px;
            border: 1px solid #313244;
            border-radius: 4px;
            background-color: #181825;
            color: #cdd6f4;
        }
        QLabel {
            font-size: 13px;
        }
        """
        self.setStyleSheet(theme)

    # --- UI Logic Methods ---

    def _restore_chat_view(self) -> None:
        self.txt_chat_history.clear()
        for msg in self.history:
            prefix = "You" if msg.role == "user" else "AI"
            self.txt_chat_history.append(f"<b>{prefix}:</b> {msg.content}\n")

    def _update_masked_credentials_display(self) -> None:
        masked = self.security_manager.get_masked_credentials()
        lines = []
        for k, v in masked.items():
            lines.append(f"{k}: {v}")
        self.lbl_credentials.setText("\n".join(lines))

    def _role_changed(self, text: str) -> None:
        target_role = UserRole(text)
        current_role = self.security_manager.get_user_role()

        # Elevating to admin requires passcode verification
        if target_role == UserRole.ADMIN and current_role != UserRole.ADMIN:
            pwd, ok = QInputDialog.getText(
                self,
                "Security Permission",
                "Enter Passcode to elevate role to Admin:",
                QLineEdit.EchoMode.Password,
            )
            if ok and pwd == "admin123":
                self.security_manager.set_user_role(target_role)
                QMessageBox.information(self, "Success", "User role elevated to ADMIN.")
            else:
                QMessageBox.warning(self, "Access Denied", "Incorrect passcode.")
                # Revert combo box
                self.cmb_role.blockSignals(True)
                self.cmb_role.setCurrentText(current_role.value)
                self.cmb_role.blockSignals(False)
        else:
            self.security_manager.set_user_role(target_role)

    def _safe_mode_toggled(self, state: int) -> None:
        enabled = bool(state == Qt.CheckState.Checked.value)
        current_safe = self.security_manager.get_safe_mode()

        # Disabling safe mode requires passcode verification
        if not enabled and current_safe:
            pwd, ok = QInputDialog.getText(
                self,
                "Security Settings",
                "Enter Passcode to disable Safe Mode:",
                QLineEdit.EchoMode.Password,
            )
            if ok and pwd == "admin123":
                self.security_manager.set_safe_mode(False)
                QMessageBox.warning(
                    self,
                    "Warning",
                    "Safe Mode is now DISABLED. Mutating actions won't require confirmation.",
                )
            else:
                QMessageBox.warning(self, "Access Denied", "Incorrect passcode.")
                # Revert checkbox
                self.chk_safe_mode.blockSignals(True)
                self.chk_safe_mode.setChecked(True)
                self.chk_safe_mode.blockSignals(False)
        else:
            self.security_manager.set_safe_mode(enabled)

    def _refresh_logs(self) -> None:
        logs = self.security_manager.get_audit_logs(limit=25)
        self.tbl_logs.setRowCount(len(logs))
        for row, log in enumerate(logs):
            # Format time
            t_str = log["timestamp"][11:19]
            self.tbl_logs.setItem(row, 0, QTableWidgetItem(t_str))
            self.tbl_logs.setItem(row, 1, QTableWidgetItem(log["tool_name"]))
            self.tbl_logs.setItem(row, 2, QTableWidgetItem(log["user_role"].upper()))
            self.tbl_logs.setItem(row, 3, QTableWidgetItem(log["status"].upper()))

    def _refresh_memory(self) -> None:
        # Fetch preferences
        prefs = self.memory_service.list_preferences()
        projects = self.memory_service.list_projects()

        lines = ["=== User Preferences ==="]
        for k, v in prefs.items():
            lines.append(f"{k}: {v}")

        lines.append("\n=== Saved Projects ===")
        for p in projects:
            lines.append(f"- {p.get('name', 'Unnamed')}")

        self.txt_memory.setText("\n".join(lines))

    def _update_system_stats(self) -> None:
        try:
            cpu = self.system_service.read_cpu()
            ram = self.system_service.read_ram()
            disk = self.system_service.read_disk()
            battery = self.system_service.read_battery()

            self.lbl_cpu.setText(f"CPU: {cpu.get('percent', 0)}%")
            self.lbl_ram.setText(
                f"RAM: Used {ram.get('percent', 0)}% (Free: {ram.get('free_gb', 0)} GB)"
            )
            self.lbl_disk.setText(f"Disk: {disk.get('percent', 0)}% Used")
            self.lbl_battery.setText(
                f"Battery: {battery.get('percent', 0)}% ({'Charging' if battery.get('charging') else 'Discharging'})"
            )
        except Exception:
            pass

    # --- Agent Interaction and Workers ---

    def _send_message(self) -> None:
        user_text = self.txt_input.text().strip()
        if not user_text:
            return

        self.txt_input.clear()
        self.txt_chat_history.append(f"<b>You:</b> {user_text}\n")

        # Save message in DB history
        self.chat_repo.save_message(
            self.session_id, Message(role="user", content=user_text)
        )
        self.history.append(Message(role="user", content=user_text))

        # Disable send interface while running
        self.btn_send.setEnabled(False)
        self.txt_input.setEnabled(False)

        # Trigger Worker Thread
        self.worker = AgentWorker(
            runner=self.runner,
            session_id=self.session_id,
            user_input=user_text,
            history=self.history,
        )
        self.worker.response_received.connect(self._on_agent_response)
        self.worker.status_changed.connect(self._on_status_changed)
        self.worker.finished.connect(self._on_agent_finished)
        self.worker.start()

    def _on_agent_response(self, role: str, text: str) -> None:
        prefix = "AI" if role == "assistant" else "System"
        self.txt_chat_history.append(f"<b>{prefix}:</b> {text}\n")
        # Save in database
        self.chat_repo.save_message(
            self.session_id,
            Message(
                role=cast(Literal["user", "assistant", "system"], role), content=text
            ),
        )
        self.history.append(
            Message(
                role=cast(Literal["user", "assistant", "system"], role), content=text
            )
        )

        # Speak it out if voice output is allowed
        try:
            self.voice_service.speak_text(text)
        except Exception:
            pass

    def _on_status_changed(self, status: str) -> None:
        self.lbl_agent_status.setText(f"Agent: {status}")
        if status == "Idle":
            self.lbl_agent_status.setStyleSheet("color: #a6e3a1; font-weight: bold;")
        elif "Listening" in status:
            self.lbl_agent_status.setStyleSheet("color: #f9e2af; font-weight: bold;")
        else:
            self.lbl_agent_status.setStyleSheet("color: #89b4fa; font-weight: bold;")

    def _on_agent_finished(self) -> None:
        self.btn_send.setEnabled(True)
        self.txt_input.setEnabled(True)
        self.txt_input.setFocus()
        self._refresh_logs()
        self._refresh_memory()

    def _toggle_voice_input(self) -> None:
        self.btn_voice.setEnabled(False)
        self.voice_worker = VoiceInputWorker(self.voice_service)
        self.voice_worker.transcription_received.connect(self._on_voice_transcription)
        self.voice_worker.status_changed.connect(self._on_status_changed)
        self.voice_worker.finished.connect(self._on_voice_finished)
        self.voice_worker.start()

    def _on_voice_transcription(self, text: str) -> None:
        if text == "__simulate__":
            # Trigger input dialog for simulated speech
            sim_text, ok = QInputDialog.getText(
                self,
                "Voice Assistant Simulator",
                "Hardware mic not present. Type simulated voice input:",
            )
            if ok and sim_text.strip():
                self.txt_input.setText(sim_text)
                self._send_message()
        elif text.strip():
            self.txt_input.setText(text)
            self._send_message()
        else:
            QMessageBox.information(self, "Speech Input", "No speech recognized.")

    def _on_voice_finished(self) -> None:
        self.btn_voice.setEnabled(True)


def main() -> None:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
