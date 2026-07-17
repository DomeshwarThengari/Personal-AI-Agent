import subprocess
from typing import Any, Dict
from src.domain.interfaces.tool import AbstractTool


class DevOpsRunCommandTool(AbstractTool):
    """DevOps tool that runs non-destructive system or terminal commands."""

    @property
    def name(self) -> str:
        return "devops_run_command"

    @property
    def description(self) -> str:
        return (
            "Runs a non-destructive terminal command (e.g. pytest, git status, "
            "ruff check, black --check) to verify code health, run test suites, or inspect repository state."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "Terminal command to run (e.g. 'pytest tests/test_system_tools.py').",
                }
            },
            "required": ["command"],
        }

    def execute(self, **kwargs: Any) -> str:
        command = kwargs.get("command", "").strip()
        if not command:
            return "Error: Command is required."

        # Safety Check: block obviously dangerous commands
        cmd_lower = command.lower()
        dangerous_tokens = [
            "rm -rf",
            "sudo",
            "dd ",
            "mkfs",
            "chmod -r",
            "chown",
            "shutdown",
            "reboot",
            "poweroff",
            "killall",
            "pkill",
        ]
        for token in dangerous_tokens:
            if token in cmd_lower:
                return f"Error: Command execution blocked for safety reasons (found dangerous token '{token}')."

        try:
            res = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=20,
            )
            output = []
            if res.stdout:
                output.append(f"STDOUT:\n{res.stdout}")
            if res.stderr:
                output.append(f"STDERR:\n{res.stderr}")
            if not output:
                output.append("Command completed with no output.")
            output.append(f"Exit Code: {res.returncode}")
            return "\n".join(output)
        except subprocess.TimeoutExpired:
            return "Error: Command timed out after 20 seconds."
        except Exception as e:
            return f"Error executing command: {e}"
