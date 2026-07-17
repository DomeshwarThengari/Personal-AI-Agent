from typing import Any, Dict, List, Literal, Optional, Sequence, TypedDict
from langgraph.graph import END, StateGraph
from src.domain.entities import Action, ActionResult, AgentResponse, Message
from src.domain.interfaces.action_engine import AbstractActionEngine
from src.domain.interfaces.llm import AbstractLLMService
from src.domain.interfaces.tool import AbstractTool
from src.utils.logging import get_logger

logger = get_logger("multi_agent_workflow")


class MultiAgentState(TypedDict):
    """Represents the operational state shared across all agents in the workspace."""

    messages: List[Message]
    pending_actions: List[Action]
    action_results: List[ActionResult]
    session_id: str
    next_agent: (
        str  # Tracks execution token: 'brain', 'planner', 'browser', etc. or 'end'
    )


AGENT_TOOL_MAPPING = {
    "brain": [
        "route_to_agent",
        "vision_take_screenshot",
        "vision_analyze_image",
    ],
    "planner": ["planner_execute_task"],
    "browser": [
        "browser_open_url",
        "browser_search_google",
        "browser_search_youtube",
        "browser_play_youtube",
        "browser_click_element",
        "browser_scroll_page",
        "browser_fill_input",
        "browser_download_file",
        "browser_take_screenshot",
        "browser_read_page_content",
    ],
    "application": [
        "search_apps",
        "launch_app",
        "close_app",
        "focus_app",
    ],
    "file": [
        "system_create_folder",
        "system_rename_file",
        "system_copy_file",
        "system_move_file",
        "system_delete_file",
        "system_search_files",
    ],
    "system": [
        "system_open_downloads",
        "system_open_documents",
        "system_read_cpu",
        "system_read_ram",
        "system_read_disk",
        "system_read_battery",
        "system_monitor_processes",
    ],
    "memory": [
        "preference_set",
        "preference_get",
        "project_save",
        "command_history",
        "memory_save",
        "memory_search",
    ],
    "devops": [
        "devops_run_command",
        "docker_list_containers",
        "docker_restart_container",
        "docker_view_logs",
        "k8s_list_pods",
        "k8s_describe_pod",
        "k8s_restart_deployment",
        "aws_list_ec2",
        "aws_s3_list_buckets",
        "aws_cloudwatch_logs",
        "jenkins_run_pipeline",
        "jenkins_view_build_logs",
        "git_commit",
        "git_push",
        "git_clone",
        "terraform_plan",
        "terraform_apply",
        "ansible_run_playbook",
        "vision_take_screenshot",
        "vision_analyze_image",
    ],
}


class MultiAgentWorkflowRunner:
    """Compiles and executes the Hub-and-Spoke LangGraph Multi-Agent reasoning network."""

    def __init__(
        self,
        llm_service: AbstractLLMService,
        action_engine: AbstractActionEngine,
        tools: Sequence[AbstractTool],
    ) -> None:
        self.llm_service = llm_service
        self.action_engine = action_engine
        self.tools = list(tools)

        # Build and compile graph
        self.app = self._build_graph()

    def _get_agent_tools(self, agent_name: str) -> List[AbstractTool]:
        allowed = AGENT_TOOL_MAPPING.get(agent_name, [])
        return [t for t in self.tools if t.name in allowed]

    def _execute_agent_loop(
        self, agent_name: str, system_instruction: str, state: MultiAgentState
    ) -> Dict[str, Any]:
        """Runs the LLM + Action execution loop for a specific agent persona and tool boundary."""
        logger.info(f"Activating Specialist Agent: '{agent_name}'")
        agent_tools = self._get_agent_tools(agent_name)

        messages = list(state["messages"])
        action_results = list(state["action_results"])
        next_agent = "brain"  # Sub-agents always hand control back to the Brain

        # 1. Ask the LLM
        response = self.llm_service.generate_response(
            messages=messages,
            system_instruction=system_instruction,
            tools=agent_tools,
        )

        if response.message.content:
            messages.append(response.message)

        # 2. Run any generated actions
        for action in response.actions:
            logger.info(f"[{agent_name} Agent] Invoking tool '{action.action_type}'")
            res = self.action_engine.execute_action(action)
            action_results.append(res)

            outcome_msg = (
                res.output if res.status == "success" else f"Error: {res.error_message}"
            )
            messages.append(
                Message(
                    role="system",
                    content=f"Tool '{action.action_type}' returned: {outcome_msg}",
                )
            )

            # Special routing hook for Brain Agent routing tools
            if action.action_type == "route_to_agent":
                target = action.parameters.get("target_agent", "").strip()
                if target in AGENT_TOOL_MAPPING:
                    next_agent = target

        # If it was a normal text response (no action or done), next_agent is determined
        if not response.actions and agent_name == "brain":
            next_agent = "end"

        return {
            "messages": messages,
            "action_results": action_results,
            "next_agent": next_agent,
        }

    # Agent Nodes
    def _brain_node(self, state: MultiAgentState) -> Dict[str, Any]:
        instr = (
            "You are the Brain Agent, the central orchestrator of this multi-agent assistant.\n"
            "Your job is to read the user request. If the request is specialized (needs web browser, "
            "file utility, planning queue, system check, memory recall, app control, or devops checks), "
            "MUST call the 'route_to_agent' tool to route to the correct specialist.\n"
            "If the request was already executed by a specialist agent and returned to you, summarize "
            "the results in a friendly, conversational manner to answer the user request directly.\n"
            "If the query is a general knowledge question that requires no tools, answer it directly."
        )
        return self._execute_agent_loop("brain", instr, state)

    def _planner_node(self, state: MultiAgentState) -> Dict[str, Any]:
        instr = (
            "You are the Planner Agent. Your job is to schedule, sequence, and execute complex "
            "multi-step jobs using your planner execution tool."
        )
        return self._execute_agent_loop("planner", instr, state)

    def _browser_node(self, state: MultiAgentState) -> Dict[str, Any]:
        instr = (
            "You are the Browser Agent. Your duty is web navigation, searches, YouTube controls, "
            "and downloading files via Playwright."
        )
        return self._execute_agent_loop("browser", instr, state)

    def _app_node(self, state: MultiAgentState) -> Dict[str, Any]:
        instr = "You are the Application Agent. Your job is to search, open, focus, or close desktop apps."
        return self._execute_agent_loop("application", instr, state)

    def _file_node(self, state: MultiAgentState) -> Dict[str, Any]:
        instr = (
            "You are the File Agent. Your job is file/folder management (creating, renaming, copying, "
            "moving, searching, deleting files)."
        )
        return self._execute_agent_loop("file", instr, state)

    def _system_node(self, state: MultiAgentState) -> Dict[str, Any]:
        instr = (
            "You are the System Agent. Your job is reading CPU, RAM, Disk, Battery capacity, and "
            "monitoring active systems."
        )
        return self._execute_agent_loop("system", instr, state)

    def _memory_node(self, state: MultiAgentState) -> Dict[str, Any]:
        instr = (
            "You are the Memory Agent. Your duty is writing preferences, saving command history, "
            "and recalling semantic context."
        )
        return self._execute_agent_loop("memory", instr, state)

    def _devops_node(self, state: MultiAgentState) -> Dict[str, Any]:
        instr = (
            "You are the DevOps Agent. Your duty is repository integrity checks, running pytest "
            "suites, executing safe commands, and checking system linters."
        )
        return self._execute_agent_loop("devops", instr, state)

    # Router logic
    def _route_next(self, state: MultiAgentState) -> Literal[
        "brain",
        "planner",
        "browser",
        "application",
        "file",
        "system",
        "memory",
        "devops",
        "end",
    ]:
        next_a = state.get("next_agent", "brain")
        logger.info(f"Routing conditional edge decision: '{next_a}'")
        if next_a in (
            "brain",
            "planner",
            "browser",
            "application",
            "file",
            "system",
            "memory",
            "devops",
        ):
            return next_a  # type: ignore[return-value]
        return "end"

    def _build_graph(self) -> Any:
        workflow = StateGraph(MultiAgentState)

        # Register nodes
        workflow.add_node("brain", self._brain_node)
        workflow.add_node("planner", self._planner_node)
        workflow.add_node("browser", self._browser_node)
        workflow.add_node("application", self._app_node)
        workflow.add_node("file", self._file_node)
        workflow.add_node("system", self._system_node)
        workflow.add_node("memory", self._memory_node)
        workflow.add_node("devops", self._devops_node)

        # Set entry
        workflow.set_entry_point("brain")

        # Routing rules
        workflow.add_conditional_edges(
            "brain",
            self._route_next,
            {
                "brain": "brain",
                "planner": "planner",
                "browser": "browser",
                "application": "application",
                "file": "file",
                "system": "system",
                "memory": "memory",
                "devops": "devops",
                "end": END,
            },
        )

        # All sub-agents return control to Brain
        workflow.add_edge("planner", "brain")
        workflow.add_edge("browser", "brain")
        workflow.add_edge("application", "brain")
        workflow.add_edge("file", "brain")
        workflow.add_edge("system", "brain")
        workflow.add_edge("memory", "brain")
        workflow.add_edge("devops", "brain")

        return workflow.compile()

    def run(
        self,
        session_id: str,
        history: List[Message],
        user_input: str,
        system_instruction: Optional[str] = None,
    ) -> AgentResponse:
        user_msg = Message(role="user", content=user_input)
        initial_messages = history + [user_msg]

        initial_state: MultiAgentState = {
            "messages": initial_messages,
            "pending_actions": [],
            "action_results": [],
            "session_id": session_id,
            "next_agent": "brain",
        }

        final_state = self.app.invoke(initial_state)

        # Find final assistant message
        final_msg_content = ""
        for msg in reversed(final_state["messages"]):
            if msg.role == "assistant":
                final_msg_content = msg.content
                break

        assistant_message = Message(role="assistant", content=final_msg_content)

        return AgentResponse(
            message=assistant_message,
            action_results=final_state["action_results"],
            metadata={"session_id": session_id},
        )
