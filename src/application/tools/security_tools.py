from typing import Any, Dict
from src.domain.interfaces.tool import AbstractTool
from src.application.services.security_manager import (
    SecurityManager,
    UserRole,
)


class AssistantViewSecurityStatusTool(AbstractTool):
    """Tool that displays current security posture and masked credentials."""

    @property
    def name(self) -> str:
        return "assistant_view_security_status"

    @property
    def description(self) -> str:
        return "Displays current active user role, safe mode status, and masked environment credentials."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {"type": "object", "properties": {}}

    def execute(self, **kwargs: Any) -> str:
        sm = SecurityManager()
        role = sm.get_user_role().value
        safe_mode = sm.get_safe_mode()
        masked = sm.get_masked_credentials()

        lines = [
            "=== Active Security Status ===",
            f"User Role: {role.upper()}",
            f"Safe Mode: {'ENABLED' if safe_mode else 'DISABLED'}",
            "",
            "=== Credentials Masking Status ===",
        ]
        for key, val in masked.items():
            lines.append(f"- {key}: {val}")

        return "\n".join(lines)


class AssistantConfigureSecurityTool(AbstractTool):
    """Tool that configures user security levels and safe mode settings."""

    @property
    def name(self) -> str:
        return "assistant_configure_security"

    @property
    def description(self) -> str:
        return (
            "Configures security posture. Actions: 'set_role' (requires role='admin'|'operator'|'viewer'), "
            "'set_safe_mode' (requires safe_mode=True|False). "
            "Passcode 'admin123' is required to elevate to 'admin' or disable safe mode."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["set_role", "set_safe_mode"],
                    "description": "Configuration action.",
                },
                "role": {
                    "type": "string",
                    "enum": ["admin", "operator", "viewer"],
                    "description": "User role to apply.",
                },
                "safe_mode": {
                    "type": "boolean",
                    "description": "Safe mode flag.",
                },
                "password": {
                    "type": "string",
                    "description": "Passcode required for sensitive elevation.",
                },
            },
            "required": ["action"],
        }

    def execute(self, **kwargs: Any) -> str:
        action = kwargs.get("action", "").lower().strip()
        password = kwargs.get("password", "").strip()
        sm = SecurityManager()

        if action == "set_role":
            role_str = kwargs.get("role", "").lower().strip()
            if not role_str:
                return "Error: role is required for set_role action."

            role = UserRole(role_str)
            if role == UserRole.ADMIN:
                if password != "admin123":
                    return (
                        "Error: Password verification failed. Cannot elevate to Admin."
                    )

            sm.set_user_role(role)
            return f"Successfully set user role to: {role.value.upper()}"

        elif action == "set_safe_mode":
            safe_val = kwargs.get("safe_mode")
            if safe_val is None:
                return "Error: safe_mode (true/false) is required for set_safe_mode action."

            safe_bool = bool(safe_val)
            if not safe_bool:  # Turning Safe Mode off
                if password != "admin123":
                    return (
                        "Error: Password verification failed. Cannot disable Safe Mode."
                    )

            sm.set_safe_mode(safe_bool)
            return f"Successfully set Safe Mode to: {'ENABLED' if safe_bool else 'DISABLED'}"

        return f"Error: Unknown action '{action}'."


class AssistantViewAuditLogsTool(AbstractTool):
    """Tool that displays security audit logs."""

    @property
    def name(self) -> str:
        return "assistant_view_audit_logs"

    @property
    def description(self) -> str:
        return "Retrieves the recent security audit logs. Restricted to Admin."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Number of logs to fetch.",
                    "default": 10,
                }
            },
        }

    def execute(self, **kwargs: Any) -> str:
        sm = SecurityManager()
        # Double-check inside execution (defense in depth)
        if sm.get_user_role() != UserRole.ADMIN:
            return "Security Violation: Access Denied. Audit logs are restricted to Administrator role."

        limit = kwargs.get("limit", 10)
        logs = sm.get_audit_logs(limit)
        if not logs:
            return "No audit logs found."

        lines = ["=== Security Audit Logs ==="]
        for log in logs:
            lines.append(
                f"[{log['timestamp'][:19]}] Tool: {log['tool_name']} | Role: {log['user_role'].upper()} | "
                f"Risk: {log['risk_level'].upper()} | Status: {log['status'].upper()} | Details: {log['details']}"
            )
        return "\n".join(lines)
