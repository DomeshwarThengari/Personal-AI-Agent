from unittest.mock import MagicMock
from src.application.services.security_manager import (
    SecurityManager,
    UserRole,
    RiskLevel,
)
from src.application.action_engine.engine import ActionEngine
from src.domain.entities import Action
from src.application.tools.registry import ToolRegistry
from src.application.tools.security_tools import (
    AssistantViewSecurityStatusTool,
    AssistantConfigureSecurityTool,
    AssistantViewAuditLogsTool,
)


def test_security_manager_defaults() -> None:
    sm = SecurityManager()
    # Enforce safe defaults
    assert sm.get_user_role() == UserRole.ADMIN
    assert sm.get_safe_mode() is True


def test_security_manager_configuration() -> None:
    sm = SecurityManager()

    sm.set_user_role(UserRole.OPERATOR)
    assert sm.get_user_role() == UserRole.OPERATOR

    sm.set_safe_mode(False)
    assert sm.get_safe_mode() is False

    # Restore defaults
    sm.set_user_role(UserRole.ADMIN)
    sm.set_safe_mode(True)


def test_tool_risk_classification() -> None:
    sm = SecurityManager()

    # Low risk tools
    assert sm.get_tool_risk("system_time", {}) == RiskLevel.LOW
    assert sm.get_tool_risk("assistant_get_weather", {}) == RiskLevel.LOW

    # Medium risk tools
    assert sm.get_tool_risk("git_commit", {}) == RiskLevel.MEDIUM
    assert sm.get_tool_risk("assistant_calendar", {"action": "add"}) == RiskLevel.MEDIUM

    # High risk tools
    assert sm.get_tool_risk("system_delete_file", {}) == RiskLevel.HIGH
    assert (
        sm.get_tool_risk("assistant_calendar", {"action": "delete"}) == RiskLevel.HIGH
    )


def test_rbac_security_matrix_policies() -> None:
    sm = SecurityManager()

    # Reset security settings
    sm.set_user_role(UserRole.ADMIN)
    sm.set_safe_mode(True)

    # 1. Admin with safe mode on -> High risk requires confirmation
    assert (
        sm.verify_execution("system_delete_file", {"confirmed": False})
        == "confirmation_required"
    )
    assert sm.verify_execution("system_delete_file", {"confirmed": True}) == "allowed"

    # 2. Admin with safe mode off -> High risk allowed directly
    sm.set_safe_mode(False)
    assert sm.verify_execution("system_delete_file", {"confirmed": False}) == "allowed"

    # 3. Viewer -> Only Low risk allowed
    sm.set_user_role(UserRole.VIEWER)
    assert sm.verify_execution("system_time", {}) == "allowed"
    assert sm.verify_execution("git_commit", {}) == "denied"
    assert sm.verify_execution("system_delete_file", {}) == "denied"

    # 4. Operator -> Low and Medium allowed. High requires confirmation
    sm.set_user_role(UserRole.OPERATOR)
    assert sm.verify_execution("system_time", {}) == "allowed"
    assert sm.verify_execution("git_commit", {}) == "allowed"
    assert (
        sm.verify_execution("system_delete_file", {"confirmed": False})
        == "confirmation_required"
    )
    assert sm.verify_execution("system_delete_file", {"confirmed": True}) == "allowed"

    # Restore defaults
    sm.set_user_role(UserRole.ADMIN)
    sm.set_safe_mode(True)


def test_api_key_masking() -> None:
    sm = SecurityManager()
    assert sm.mask_key(None) == "Not Configured"
    assert sm.mask_key("12345") == "****"
    assert sm.mask_key("AIzaSy123456789") == "AIzaSy...6789"


def test_audit_logs() -> None:
    sm = SecurityManager()
    sm.log_audit(
        "run_command", UserRole.ADMIN, RiskLevel.HIGH, "allowed", "Test execute"
    )

    logs = sm.get_audit_logs(limit=1)
    assert len(logs) == 1
    assert logs[0]["tool_name"] == "run_command"
    assert logs[0]["user_role"] == "admin"
    assert logs[0]["risk_level"] == "high"
    assert logs[0]["status"] == "allowed"


def test_action_engine_interceptor() -> None:
    # Set up a mock registry with a tool
    registry = ToolRegistry()
    mock_tool = MagicMock()
    mock_tool.name = "system_delete_file"
    mock_tool.execute.return_value = "Deleted file"
    registry.register(mock_tool)

    sm = SecurityManager()
    engine = ActionEngine(registry=registry, security_manager=sm)

    # Test denied (Viewer role running High risk tool)
    sm.set_user_role(UserRole.VIEWER)
    act = Action(
        id="act-123",
        action_type="system_delete_file",
        parameters={"path": "test.txt"},
    )
    res = engine.execute_action(act)
    assert res.status == "failure"
    assert res.error_message is not None
    assert "Access Denied" in res.error_message

    # Test confirmation required (Operator role running High risk tool unconfirmed)
    sm.set_user_role(UserRole.OPERATOR)
    res = engine.execute_action(act)
    assert res.status == "failure"
    assert res.error_message is not None
    assert "Security Confirmation Required" in res.error_message

    # Test execution approved (Operator role running High risk tool with confirmed=True)
    act_confirmed = Action(
        id="act-124",
        action_type="system_delete_file",
        parameters={"path": "test.txt", "confirmed": True},
    )
    res = engine.execute_action(act_confirmed)
    assert res.status == "success"
    assert res.output == "Deleted file"

    # Restore defaults
    sm.set_user_role(UserRole.ADMIN)


def test_security_tools() -> None:
    sm = SecurityManager()
    sm.set_user_role(UserRole.ADMIN)
    sm.set_safe_mode(True)

    # 1. View Status Tool
    status_tool = AssistantViewSecurityStatusTool()
    res_status = status_tool.execute()
    assert "User Role: ADMIN" in res_status
    assert "Safe Mode: ENABLED" in res_status

    # 2. Configure Tool
    config_tool = AssistantConfigureSecurityTool()

    # Test role change rejection
    res_rejected = config_tool.execute(action="set_role", role="admin")
    assert "Password verification failed" in res_rejected

    # Test role change success with password
    res_accepted = config_tool.execute(
        action="set_role", role="admin", password="admin123"
    )
    assert "Successfully set user role" in res_accepted

    # Test safe mode change rejection
    res_sm_rejected = config_tool.execute(action="set_safe_mode", safe_mode=False)
    assert "Password verification failed" in res_sm_rejected

    # Test safe mode change success
    res_sm_accepted = config_tool.execute(
        action="set_safe_mode", safe_mode=False, password="admin123"
    )
    assert "Successfully set Safe Mode to: DISABLED" in res_sm_accepted

    # 3. View Logs Tool
    logs_tool = AssistantViewAuditLogsTool()
    res_logs = logs_tool.execute(limit=5)
    assert "Security Audit Logs" in res_logs

    # Restore defaults
    sm.set_user_role(UserRole.ADMIN)
    sm.set_safe_mode(True)
