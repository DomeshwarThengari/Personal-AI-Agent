import os
import sqlite3
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from src.config.settings import settings


class UserRole(str, Enum):
    ADMIN = "admin"
    OPERATOR = "operator"
    VIEWER = "viewer"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class SecurityManager:
    """Manages system security policies, RBAC roles, safe mode configuration,

    tool risk classifications, API key masking, and database-backed audit logging.
    """

    def __init__(self, db_path: str = settings.SQLITE_DB_PATH) -> None:
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _init_db(self) -> None:
        create_audit_logs = """
        CREATE TABLE IF NOT EXISTS assistant_audit_logs (
            id TEXT PRIMARY KEY,
            timestamp TEXT NOT NULL,
            tool_name TEXT NOT NULL,
            user_role TEXT NOT NULL,
            risk_level TEXT NOT NULL,
            status TEXT NOT NULL,
            details TEXT
        );
        """
        create_preferences = """
        CREATE TABLE IF NOT EXISTS preferences (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(create_audit_logs)
            cursor.execute(create_preferences)
            conn.commit()

    # --- Role & Settings Management (via preferences in DB) ---

    def get_user_role(self) -> UserRole:
        """Retrieves user role from DB preferences.

        Defaults to 'admin' if not set.
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT value FROM preferences WHERE key = 'security_role'"
                )
                row = cursor.fetchone()
                if row:
                    return UserRole(row[0].lower())
        except Exception:
            pass
        return UserRole.ADMIN

    def set_user_role(self, role: UserRole) -> None:
        """Saves user role to DB preferences."""
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO preferences (key, value, updated_at) VALUES ('security_role', ?, ?)",
                (role.value, now),
            )
            conn.commit()

    def get_safe_mode(self) -> bool:
        """Retrieves safe mode status from DB preferences.

        Defaults to True.
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT value FROM preferences WHERE key = 'safe_mode'")
                row = cursor.fetchone()
                if row:
                    return bool(row[0].lower() == "true")
        except Exception:
            pass
        return True

    def set_safe_mode(self, enabled: bool) -> None:
        """Saves safe mode status to DB preferences."""
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO preferences (key, value, updated_at) VALUES ('safe_mode', ?, ?)",
                (str(enabled).lower(), now),
            )
            conn.commit()

    # --- Audit Logging ---

    def log_audit(
        self,
        tool_name: str,
        role: UserRole,
        risk: RiskLevel,
        status: str,
        details: str,
    ) -> None:
        """Appends a secure execution log to the sqlite audit table."""
        log_id = str(uuid.uuid4())
        ts = datetime.now(timezone.utc).isoformat()
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO assistant_audit_logs (id, timestamp, tool_name, user_role, risk_level, status, details) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (log_id, ts, tool_name, role.value, risk.value, status, details),
                )
                conn.commit()
        except Exception:
            pass

    def get_audit_logs(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Lists audit logs in descending order."""
        logs = []
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT id, timestamp, tool_name, user_role, risk_level, status, details FROM assistant_audit_logs ORDER BY timestamp DESC LIMIT ?",
                    (limit,),
                )
                rows = cursor.fetchall()
                for row in rows:
                    logs.append(
                        {
                            "id": row[0],
                            "timestamp": row[1],
                            "tool_name": row[2],
                            "user_role": row[3],
                            "risk_level": row[4],
                            "status": row[5],
                            "details": row[6],
                        }
                    )
        except Exception:
            pass
        return logs

    # --- Tool Classification & Policy Verification ---

    def get_tool_risk(self, tool_name: str, params: Dict[str, Any]) -> RiskLevel:
        """Statically maps or dynamically determines tool risk levels based on action arguments."""
        # Check sub-actions for assistant database managers
        if tool_name == "assistant_calendar":
            act = params.get("action", "").lower().strip()
            if act == "delete":
                return RiskLevel.HIGH
            elif act == "add":
                return RiskLevel.MEDIUM
            return RiskLevel.LOW

        if tool_name == "assistant_todo":
            act = params.get("action", "").lower().strip()
            if act == "delete":
                return RiskLevel.HIGH
            elif act in ("add", "complete"):
                return RiskLevel.MEDIUM
            return RiskLevel.LOW

        if tool_name == "assistant_notes":
            act = params.get("action", "").lower().strip()
            if act == "delete":
                return RiskLevel.HIGH
            elif act == "create":
                return RiskLevel.MEDIUM
            return RiskLevel.LOW

        # Statically defined risk map
        risk_map = {
            # Low Risk: pure queries or readings
            "system_time": RiskLevel.LOW,
            "system_cpu": RiskLevel.LOW,
            "system_ram": RiskLevel.LOW,
            "system_disk": RiskLevel.LOW,
            "system_battery": RiskLevel.LOW,
            "system_monitor_processes": RiskLevel.LOW,
            "system_search_files": RiskLevel.LOW,
            "system_open_downloads": RiskLevel.LOW,
            "system_open_documents": RiskLevel.LOW,
            "browser_open_url": RiskLevel.LOW,
            "browser_search_google": RiskLevel.LOW,
            "browser_search_youtube": RiskLevel.LOW,
            "browser_take_screenshot": RiskLevel.LOW,
            "browser_read_page": RiskLevel.LOW,
            "vision_take_screenshot": RiskLevel.LOW,
            "vision_analyze_image": RiskLevel.LOW,
            "assistant_get_weather": RiskLevel.LOW,
            "assistant_get_news": RiskLevel.LOW,
            "assistant_summarize_emails": RiskLevel.LOW,
            "assistant_view_security_status": RiskLevel.LOW,
            "memory_list_preferences": RiskLevel.LOW,
            "memory_get_preference": RiskLevel.LOW,
            "memory_get_project": RiskLevel.LOW,
            "memory_list_projects": RiskLevel.LOW,
            "memory_get_command_history": RiskLevel.LOW,
            "memory_search_vector": RiskLevel.LOW,
            "app_launcher_list_apps": RiskLevel.LOW,
            "docker_list_containers": RiskLevel.LOW,
            "docker_view_logs": RiskLevel.LOW,
            "k8s_list_pods": RiskLevel.LOW,
            "k8s_describe_pod": RiskLevel.LOW,
            "aws_list_ec2": RiskLevel.LOW,
            "aws_s3_list_buckets": RiskLevel.LOW,
            "aws_cloudwatch_logs": RiskLevel.LOW,
            "jenkins_view_build_logs": RiskLevel.LOW,
            "terraform_plan": RiskLevel.LOW,
            # Medium Risk: Creation / State mutation (non-destructive)
            "memory_set_preference": RiskLevel.MEDIUM,
            "memory_save_project": RiskLevel.MEDIUM,
            "memory_save_vector": RiskLevel.MEDIUM,
            "app_launcher_launch_app": RiskLevel.MEDIUM,
            "git_commit": RiskLevel.MEDIUM,
            "git_clone": RiskLevel.MEDIUM,
            "route_to_agent": RiskLevel.MEDIUM,
            "assistant_send_notification": RiskLevel.MEDIUM,
            "assistant_daily_briefing": RiskLevel.MEDIUM,
            "assistant_trigger_routine": RiskLevel.MEDIUM,
            "assistant_configure_security": RiskLevel.MEDIUM,
            "assistant_view_audit_logs": RiskLevel.MEDIUM,
            "browser_click_button": RiskLevel.MEDIUM,
            "browser_scroll": RiskLevel.MEDIUM,
            "browser_fill_form": RiskLevel.MEDIUM,
            "browser_download_file": RiskLevel.MEDIUM,
        }

        # Anything else defaults to HIGH (destructive/mutating/unspecified)
        return risk_map.get(tool_name, RiskLevel.HIGH)

    def verify_execution(self, tool_name: str, params: Dict[str, Any]) -> str:
        """Verifies if the current active role and Safe Mode settings permit tool execution.

        Returns:
            "allowed" if allowed to proceed.
            "denied" if blocked by RBAC role policies.
            "confirmation_required" if execution requires user confirmation.
        """
        role = self.get_user_role()
        safe_mode = self.get_safe_mode()
        risk = self.get_tool_risk(tool_name, params)

        # 1. RBAC Policy Enforcement
        if role == UserRole.VIEWER:
            if risk != RiskLevel.LOW:
                self.log_audit(
                    tool_name,
                    role,
                    risk,
                    "denied",
                    "Blocked: Viewer role cannot execute Medium/High tools.",
                )
                return "denied"

        elif role == UserRole.OPERATOR:
            if risk == RiskLevel.HIGH:
                confirmed = bool(params.get("confirmed", False))
                if not confirmed:
                    self.log_audit(
                        tool_name,
                        role,
                        risk,
                        "pending_confirmation",
                        "Blocked: Operator requires explicit confirmation for High risk tool.",
                    )
                    return "confirmation_required"

        # 2. Safe Mode Policy Enforcement
        if risk == RiskLevel.HIGH and safe_mode:
            confirmed = bool(params.get("confirmed", False))
            if not confirmed:
                self.log_audit(
                    tool_name,
                    role,
                    risk,
                    "pending_confirmation",
                    "Blocked: Safe Mode requires explicit confirmation for High risk tool.",
                )
                return "confirmation_required"

        # Allowed
        self.log_audit(tool_name, role, risk, "allowed", "Executed successfully.")
        return "allowed"

    # --- Credential Protection ---

    def mask_key(self, value: Optional[str]) -> str:
        """Masks sensitive credentials to prevent logs or UI leakage."""
        if not value:
            return "Not Configured"
        if len(value) <= 8:
            return "****"
        return f"{value[:6]}...{value[-4:]}"

    def get_masked_credentials(self) -> Dict[str, str]:
        """Collects and masks all system credentials."""
        return {
            "GEMINI_API_KEY": self.mask_key(os.getenv("GEMINI_API_KEY")),
            "LANGCHAIN_API_KEY": self.mask_key(os.getenv("LANGCHAIN_API_KEY")),
            "AWS_ACCESS_KEY_ID": self.mask_key(os.getenv("AWS_ACCESS_KEY_ID")),
            "AWS_SECRET_ACCESS_KEY": self.mask_key(os.getenv("AWS_SECRET_ACCESS_KEY")),
        }
