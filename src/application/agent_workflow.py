from typing import Any, Dict, List, Literal, Optional, Sequence, TypedDict
from langgraph.graph import END, StateGraph
from src.domain.entities import Action, ActionResult, AgentResponse, Message
from src.domain.interfaces.action_engine import AbstractActionEngine
from src.domain.interfaces.llm import AbstractLLMService
from src.domain.interfaces.tool import AbstractTool
from src.utils.logging import get_logger

logger = get_logger("agent_workflow")


class AgentState(TypedDict):
    """Represents the operational state of the LangGraph agent workflow."""

    messages: List[Message]
    pending_actions: List[Action]
    action_results: List[ActionResult]
    session_id: str
    system_instruction: Optional[str]


class AgentWorkflowRunner:
    """Compiles and executes the LangGraph agent reasoning and tool usage loop."""

    def __init__(
        self,
        llm_service: AbstractLLMService,
        action_engine: AbstractActionEngine,
        tools: Sequence[AbstractTool],
    ):
        """Initializes nodes, registers tools, and compiles the state graph."""
        self.llm_service = llm_service
        self.action_engine = action_engine
        self.tools = list(tools)

        # Build and compile graph
        self.app = self._build_graph()

    def _llm_node(self, state: AgentState) -> Dict[str, Any]:
        """Node executing the LLM reasoning step."""
        logger.info(f"Executing LLM Node for session: '{state['session_id']}'")

        # Call Gemini with the message history and tool schemas
        agent_response = self.llm_service.generate_response(
            messages=state["messages"],
            system_instruction=state["system_instruction"],
            tools=self.tools,
        )

        updated_messages = list(state["messages"])
        # Append text response if any exists
        if agent_response.message.content:
            updated_messages.append(agent_response.message)

        return {
            "messages": updated_messages,
            "pending_actions": agent_response.actions,
        }

    def _action_node(self, state: AgentState) -> Dict[str, Any]:
        """Node running tool execution logic for any pending actions."""
        logger.info(
            f"Executing Action Node with {len(state['pending_actions'])} pending tools."
        )

        updated_messages = list(state["messages"])
        results = list(state["action_results"])

        for action in state["pending_actions"]:
            tool_name = action.action_type
            logger.info(f"Invoking tool via Action Engine: '{tool_name}'...")

            # Delegate tool execution entirely to the Action Engine
            result = self.action_engine.execute_action(action)
            results.append(result)

            # Append the tool result message to the chat history to feed it back to LLM
            outcome_msg = (
                result.output
                if result.status == "success"
                else f"Error: {result.error_message}"
            )
            updated_messages.append(
                Message(
                    role="system",
                    content=f"Tool '{tool_name}' execution returned: {outcome_msg}",
                )
            )

        # Clear pending actions once executed
        return {
            "messages": updated_messages,
            "action_results": results,
            "pending_actions": [],
        }

    def _should_continue(self, state: AgentState) -> Literal["continue", "end"]:
        """Conditional edge evaluating whether to continue execution or terminate."""
        if state["pending_actions"]:
            logger.info("Pending actions detected. Routing to Action Node.")
            return "continue"
        logger.info("No pending actions. Terminating workflow.")
        return "end"

    def _build_graph(self) -> Any:
        """Constructs the state graph with nodes, edges, and conditions."""
        workflow = StateGraph(AgentState)

        # Register nodes
        workflow.add_node("llm", self._llm_node)
        workflow.add_node("action", self._action_node)

        # Establish workflow entry point
        workflow.set_entry_point("llm")

        # Routing rules
        workflow.add_conditional_edges(
            "llm",
            self._should_continue,
            {"continue": "action", "end": END},
        )
        workflow.add_edge("action", "llm")

        return workflow.compile()

    def run(
        self,
        session_id: str,
        history: List[Message],
        user_input: str,
        system_instruction: Optional[str] = None,
    ) -> AgentResponse:
        """Executes the workflow with user query input and history."""
        # Wrap the user query
        user_msg = Message(role="user", content=user_input)
        initial_messages = history + [user_msg]

        initial_state: AgentState = {
            "messages": initial_messages,
            "pending_actions": [],
            "action_results": [],
            "session_id": session_id,
            "system_instruction": system_instruction,
        }

        # Invoke workflow runner
        final_state = self.app.invoke(initial_state)

        # Find the final text response from the assistant
        final_msg_content = ""
        # Search backwards for the last assistant message
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
