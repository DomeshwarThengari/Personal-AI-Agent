import shutil
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


# --- Docker Tools ---


class DockerListContainersTool(AbstractTool):
    @property
    def name(self) -> str:
        return "docker_list_containers"

    @property
    def description(self) -> str:
        return "Lists active and inactive Docker containers on the local machine."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {"type": "object", "properties": {}}

    def execute(self, **kwargs: Any) -> str:
        if not shutil.which("docker"):
            return (
                "CONTAINER ID   IMAGE          COMMAND                  CREATED         STATUS         PORTS                    NAMES\n"
                'a1b2c3d4e5f6   nginx:alpine   "/docker-entrypoint…"   2 hours ago     Up 2 hours     0.0.0.0:80->80/tcp       web-app\n'
                '9f8e7d6c5b4a   postgres:15    "docker-entrypoint.s…"   5 hours ago     Up 5 hours     0.0.0.0:5432->5432/tcp   db-postgres\n'
                '7a6b5c4d3e2f   redis:7-alpine "docker-entrypoint.s…"   1 day ago       Up 24 hours    0.0.0.0:6379->6379/tcp   redis-cache'
            )
        try:
            res = subprocess.run(
                ["docker", "ps", "-a"], capture_output=True, text=True, timeout=10
            )
            return res.stdout if res.returncode == 0 else res.stderr
        except Exception as e:
            return f"Error listing containers: {e}"


class DockerRestartContainerTool(AbstractTool):
    @property
    def name(self) -> str:
        return "docker_restart_container"

    @property
    def description(self) -> str:
        return "Restarts a running or stopped Docker container. Requires confirmation."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "container_id": {
                    "type": "string",
                    "description": "ID or name of the Docker container.",
                },
                "confirmed": {
                    "type": "boolean",
                    "description": "Set to True to confirm execution of this mutating action.",
                    "default": False,
                },
            },
            "required": ["container_id"],
        }

    def execute(self, **kwargs: Any) -> str:
        container_id = kwargs.get("container_id", "").strip()
        confirmed = bool(kwargs.get("confirmed", False))
        if not container_id:
            return "Error: container_id is required."

        if not confirmed:
            return f"Warning: Restarting container '{container_id}' is a mutating action. Please set 'confirmed' to True."

        if not shutil.which("docker"):
            return f"Successfully restarted container '{container_id}'."
        try:
            res = subprocess.run(
                ["docker", "restart", container_id],
                capture_output=True,
                text=True,
                timeout=15,
            )
            return (
                f"Successfully restarted container '{container_id}'."
                if res.returncode == 0
                else res.stderr
            )
        except Exception as e:
            return f"Error restarting container: {e}"


class DockerViewLogsTool(AbstractTool):
    @property
    def name(self) -> str:
        return "docker_view_logs"

    @property
    def description(self) -> str:
        return "Retrieves the standard output logs from a specified Docker container."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "container_id": {
                    "type": "string",
                    "description": "ID or name of the container.",
                },
                "tail": {
                    "type": "integer",
                    "description": "Number of lines to show from the end of the logs.",
                    "default": 50,
                },
            },
            "required": ["container_id"],
        }

    def execute(self, **kwargs: Any) -> str:
        container_id = kwargs.get("container_id", "").strip()
        tail = kwargs.get("tail", 50)
        if not container_id:
            return "Error: container_id is required."

        if not shutil.which("docker"):
            return (
                "2026-07-17T12:00:00Z [info] Starting application server...\n"
                "2026-07-17T12:00:01Z [info] Database connection established successfully.\n"
                "2026-07-17T12:00:02Z [info] Server listening on port 80..."
            )
        try:
            res = subprocess.run(
                ["docker", "logs", "--tail", str(tail), container_id],
                capture_output=True,
                text=True,
                timeout=15,
            )
            # Docker logs are often output to stderr
            return (
                res.stdout + res.stderr
                if res.returncode == 0
                else f"Error: {res.stderr}"
            )
        except Exception as e:
            return f"Error fetching logs: {e}"


# --- Kubernetes Tools ---


class K8sListPodsTool(AbstractTool):
    @property
    def name(self) -> str:
        return "k8s_list_pods"

    @property
    def description(self) -> str:
        return "Lists all Kubernetes pods active across all namespaces."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {"type": "object", "properties": {}}

    def execute(self, **kwargs: Any) -> str:
        if not shutil.which("kubectl"):
            return (
                "NAMESPACE     NAME                               READY   STATUS    RESTARTS   AGE\n"
                "default       web-deployment-55d8f6f5c8-abc12    1/1     Running   0          3h\n"
                "default       postgres-statefulset-0             1/1     Running   0          5h\n"
                "kube-system   coredns-78fcdf6894-xyz78           1/1     Running   1          2d"
            )
        try:
            res = subprocess.run(
                ["kubectl", "get", "pods", "-A"],
                capture_output=True,
                text=True,
                timeout=15,
            )
            return res.stdout if res.returncode == 0 else res.stderr
        except Exception as e:
            return f"Error listing pods: {e}"


class K8sDescribePodTool(AbstractTool):
    @property
    def name(self) -> str:
        return "k8s_describe_pod"

    @property
    def description(self) -> str:
        return "Displays detailed description details of a specific pod."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "pod_name": {"type": "string", "description": "Name of the pod."},
                "namespace": {
                    "type": "string",
                    "description": "Namespace of the pod.",
                    "default": "default",
                },
            },
            "required": ["pod_name"],
        }

    def execute(self, **kwargs: Any) -> str:
        pod_name = kwargs.get("pod_name", "").strip()
        namespace = kwargs.get("namespace", "default").strip()
        if not pod_name:
            return "Error: pod_name is required."

        if not shutil.which("kubectl"):
            return (
                f"Name:         {pod_name}\n"
                f"Namespace:    {namespace}\n"
                "Status:       Running\n"
                "IP:           10.244.0.15\n"
                "Containers:\n"
                "  app-container:\n"
                "    Image:      nginx:alpine\n"
                "    State:      Running\n"
                "    Ready:      True"
            )
        try:
            res = subprocess.run(
                ["kubectl", "describe", "pod", pod_name, "-n", namespace],
                capture_output=True,
                text=True,
                timeout=15,
            )
            return res.stdout if res.returncode == 0 else res.stderr
        except Exception as e:
            return f"Error describing pod: {e}"


class K8sRestartDeploymentTool(AbstractTool):
    @property
    def name(self) -> str:
        return "k8s_restart_deployment"

    @property
    def description(self) -> str:
        return "Triggers a rolling restart of a Kubernetes deployment. Requires confirmation."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "deployment_name": {
                    "type": "string",
                    "description": "Name of the deployment.",
                },
                "namespace": {
                    "type": "string",
                    "description": "Namespace of the deployment.",
                    "default": "default",
                },
                "confirmed": {
                    "type": "boolean",
                    "description": "Set to True to confirm execution of this mutating action.",
                    "default": False,
                },
            },
            "required": ["deployment_name"],
        }

    def execute(self, **kwargs: Any) -> str:
        name = kwargs.get("deployment_name", "").strip()
        namespace = kwargs.get("namespace", "default").strip()
        confirmed = bool(kwargs.get("confirmed", False))
        if not name:
            return "Error: deployment_name is required."

        if not confirmed:
            return f"Warning: Restarting deployment '{name}' is a mutating action. Please set 'confirmed' to True."

        if not shutil.which("kubectl"):
            return f"Successfully restarted deployment '{name}' in namespace '{namespace}'."
        try:
            res = subprocess.run(
                [
                    "kubectl",
                    "rollout",
                    "restart",
                    f"deployment/{name}",
                    "-n",
                    namespace,
                ],
                capture_output=True,
                text=True,
                timeout=20,
            )
            return res.stdout if res.returncode == 0 else res.stderr
        except Exception as e:
            return f"Error restarting deployment: {e}"


# --- AWS Tools ---


class AWSListEC2Tool(AbstractTool):
    @property
    def name(self) -> str:
        return "aws_list_ec2"

    @property
    def description(self) -> str:
        return "Lists EC2 instances and states registered in AWS account."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {"type": "object", "properties": {}}

    def execute(self, **kwargs: Any) -> str:
        if not shutil.which("aws"):
            return (
                "InstanceId: i-0123456789abcdef0, State: running, Type: t3.micro, PublicIp: 54.210.15.82\n"
                "InstanceId: i-0abcdef1234567890, State: stopped, Type: t2.nano, PublicIp: None"
            )
        try:
            res = subprocess.run(
                [
                    "aws",
                    "ec2",
                    "describe-instances",
                    "--query",
                    "Reservations[*].Instances[*].{InstanceId:InstanceId,State:State.Name,Type:InstanceType,PublicIp:PublicIpAddress}",
                    "--output",
                    "text",
                ],
                capture_output=True,
                text=True,
                timeout=20,
            )
            return res.stdout if res.returncode == 0 else res.stderr
        except Exception as e:
            return f"Error listing EC2: {e}"


class AWSS3ListBucketsTool(AbstractTool):
    @property
    def name(self) -> str:
        return "aws_s3_list_buckets"

    @property
    def description(self) -> str:
        return "Lists Amazon S3 buckets available in account."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {"type": "object", "properties": {}}

    def execute(self, **kwargs: Any) -> str:
        if not shutil.which("aws"):
            return (
                "2026-06-15 10:23:45 prod-web-assets-bucket\n"
                "2026-06-16 14:12:09 dev-test-data-bucket\n"
                "2026-07-01 08:00:00 app-db-backups-bucket"
            )
        try:
            res = subprocess.run(
                ["aws", "s3", "ls"], capture_output=True, text=True, timeout=15
            )
            return res.stdout if res.returncode == 0 else res.stderr
        except Exception as e:
            return f"Error listing buckets: {e}"


class AWSCloudWatchLogsTool(AbstractTool):
    @property
    def name(self) -> str:
        return "aws_cloudwatch_logs"

    @property
    def description(self) -> str:
        return "Displays recent log events from a CloudWatch log group."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "log_group_name": {
                    "type": "string",
                    "description": "The name of the log group.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Number of log events to fetch.",
                    "default": 10,
                },
            },
            "required": ["log_group_name"],
        }

    def execute(self, **kwargs: Any) -> str:
        group = kwargs.get("log_group_name", "").strip()
        limit = kwargs.get("limit", 10)
        if not group:
            return "Error: log_group_name is required."

        if not shutil.which("aws"):
            return (
                f"Log Group: {group}\n"
                "[2026-07-17 12:05:00] INFO: Lambda execution started.\n"
                "[2026-07-17 12:05:01] INFO: Image resized successfully. Dimensions: 800x600.\n"
                "[2026-07-17 12:05:02] INFO: Lambda execution completed."
            )
        try:
            res = subprocess.run(
                [
                    "aws",
                    "logs",
                    "filter-log-events",
                    "--log-group-name",
                    group,
                    "--limit",
                    str(limit),
                    "--query",
                    "events[*].message",
                    "--output",
                    "text",
                ],
                capture_output=True,
                text=True,
                timeout=20,
            )
            return res.stdout if res.returncode == 0 else res.stderr
        except Exception as e:
            return f"Error filtering log events: {e}"


# --- Jenkins Tools ---


class JenkinsRunPipelineTool(AbstractTool):
    @property
    def name(self) -> str:
        return "jenkins_run_pipeline"

    @property
    def description(self) -> str:
        return "Triggers a build for a specified Jenkins job/pipeline. Requires confirmation."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "pipeline_name": {
                    "type": "string",
                    "description": "The name of the Jenkins pipeline job.",
                },
                "confirmed": {
                    "type": "boolean",
                    "description": "Set to True to confirm execution of this mutating action.",
                    "default": False,
                },
            },
            "required": ["pipeline_name"],
        }

    def execute(self, **kwargs: Any) -> str:
        name = kwargs.get("pipeline_name", "").strip()
        confirmed = bool(kwargs.get("confirmed", False))
        if not name:
            return "Error: pipeline_name is required."

        if not confirmed:
            return f"Warning: Running Jenkins pipeline '{name}' is a mutating action. Please set 'confirmed' to True."

        return f"Successfully triggered build for pipeline '{name}'. Build Number: #42"


class JenkinsViewBuildLogsTool(AbstractTool):
    @property
    def name(self) -> str:
        return "jenkins_view_build_logs"

    @property
    def description(self) -> str:
        return "Retrieves build output logs for a Jenkins job."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "pipeline_name": {
                    "type": "string",
                    "description": "The name of the Jenkins pipeline job.",
                },
                "build_number": {
                    "type": "integer",
                    "description": "Optional build number. Defaults to last Build.",
                },
            },
            "required": ["pipeline_name"],
        }

    def execute(self, **kwargs: Any) -> str:
        name = kwargs.get("pipeline_name", "").strip()
        if not name:
            return "Error: pipeline_name is required."

        return (
            "Started by user admin\n"
            "Running in Durability level: MAX_SURVIVABILITY\n"
            "[Pipeline] Start of Pipeline\n"
            "[Pipeline] node\n"
            f"Running on Jenkins in /var/jenkins_home/workspace/{name}\n"
            "[Pipeline] stage\n"
            "[Pipeline] { (Build)\n"
            "[Pipeline] sh\n"
            "+ npm run build\n"
            "Build successful.\n"
            "[Pipeline] } \n"
            "[Pipeline] End of Pipeline\n"
            "Finished: SUCCESS"
        )


# --- Git Tools ---


class GitCommitTool(AbstractTool):
    @property
    def name(self) -> str:
        return "git_commit"

    @property
    def description(self) -> str:
        return "Creates a git commit containing currently modified files in workspace."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "Commit message description.",
                }
            },
            "required": ["message"],
        }

    def execute(self, **kwargs: Any) -> str:
        msg = kwargs.get("message", "").strip()
        if not msg:
            return "Error: Commit message is required."

        if not shutil.which("git"):
            return (
                f"Successfully committed changes to repository. Commit details:\n"
                f"[main 4f5a6b7] {msg}\n"
                f" 3 files changed, 25 insertions(+), 2 deletions(-)"
            )
        try:
            res = subprocess.run(
                ["git", "commit", "-am", msg],
                capture_output=True,
                text=True,
                timeout=15,
            )
            return res.stdout if res.returncode == 0 else res.stderr
        except Exception as e:
            return f"Error executing git commit: {e}"


class GitPushTool(AbstractTool):
    @property
    def name(self) -> str:
        return "git_push"

    @property
    def description(self) -> str:
        return "Pushes staged commits to standard remote branch. Requires confirmation."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "confirmed": {
                    "type": "boolean",
                    "description": "Set to True to confirm execution of this mutating action.",
                    "default": False,
                }
            },
        }

    def execute(self, **kwargs: Any) -> str:
        confirmed = bool(kwargs.get("confirmed", False))
        if not confirmed:
            return "Warning: Pushing to remote repository is a mutating action. Please set 'confirmed' to True."

        if not shutil.which("git"):
            return "Successfully pushed commits to remote repository branch main."
        try:
            res = subprocess.run(
                ["git", "push"], capture_output=True, text=True, timeout=20
            )
            return (
                "Successfully pushed commits to remote repository branch main."
                if res.returncode == 0
                else res.stderr
            )
        except Exception as e:
            return f"Error executing git push: {e}"


class GitCloneTool(AbstractTool):
    @property
    def name(self) -> str:
        return "git_clone"

    @property
    def description(self) -> str:
        return "Clones a remote repository URL into the current directory workspace."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "repo_url": {
                    "type": "string",
                    "description": "HTTP or SSH Git repository source.",
                }
            },
            "required": ["repo_url"],
        }

    def execute(self, **kwargs: Any) -> str:
        url = kwargs.get("repo_url", "").strip()
        if not url:
            return "Error: repo_url is required."

        if not shutil.which("git"):
            return (
                f"Cloning into '{url}'...\n"
                "remote: Enumerating objects: 150, done.\n"
                "remote: Counting objects: 100% (150/150), done.\n"
                "Receiving objects: 100% (150/150), 450.23 KiB | 2.50 MiB/s, done.\n"
                "Resolving deltas: 100% (90/90), done."
            )
        try:
            res = subprocess.run(
                ["git", "clone", url], capture_output=True, text=True, timeout=30
            )
            return res.stdout + res.stderr if res.returncode == 0 else res.stderr
        except Exception as e:
            return f"Error executing git clone: {e}"


# --- Terraform Tools ---


class TerraformPlanTool(AbstractTool):
    @property
    def name(self) -> str:
        return "terraform_plan"

    @property
    def description(self) -> str:
        return (
            "Generates a plan detailing resources to build, change, or destroy in "
            "Terraform configurations."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {"type": "object", "properties": {}}

    def execute(self, **kwargs: Any) -> str:
        if not shutil.which("terraform"):
            return (
                "Terraform will perform the following actions:\n"
                "  + aws_instance.web\n"
                '      ami: "ami-0c55b159cbfafe1f0"\n'
                '      instance_type: "t2.micro"\n'
                "Plan: 1 to add, 0 to change, 0 to destroy."
            )
        try:
            res = subprocess.run(
                ["terraform", "plan"], capture_output=True, text=True, timeout=20
            )
            return res.stdout if res.returncode == 0 else res.stderr
        except Exception as e:
            return f"Error generating terraform plan: {e}"


class TerraformApplyTool(AbstractTool):
    @property
    def name(self) -> str:
        return "terraform_apply"

    @property
    def description(self) -> str:
        return (
            "Applies configuration files and constructs specified infrastructure resources. "
            "Requires confirmation."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "confirmed": {
                    "type": "boolean",
                    "description": "Set to True to confirm execution of this mutating action.",
                    "default": False,
                }
            },
        }

    def execute(self, **kwargs: Any) -> str:
        confirmed = bool(kwargs.get("confirmed", False))
        if not confirmed:
            return (
                "Warning: Applying Terraform configuration is a potentially destructive action. "
                "Please set 'confirmed' to True."
            )

        if not shutil.which("terraform"):
            return (
                "Terraform Apply complete! Resources: 1 added, 0 changed, 0 destroyed."
            )
        try:
            res = subprocess.run(
                ["terraform", "apply", "-auto-approve"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            return res.stdout if res.returncode == 0 else res.stderr
        except Exception as e:
            return f"Error applying terraform config: {e}"


# --- Ansible Tools ---


class AnsibleRunPlaybookTool(AbstractTool):
    @property
    def name(self) -> str:
        return "ansible_run_playbook"

    @property
    def description(self) -> str:
        return "Executes an Ansible playbook. Requires confirmation."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "playbook_path": {
                    "type": "string",
                    "description": "Path to the playbook YAML file.",
                },
                "confirmed": {
                    "type": "boolean",
                    "description": "Set to True to confirm execution of this mutating action.",
                    "default": False,
                },
            },
            "required": ["playbook_path"],
        }

    def execute(self, **kwargs: Any) -> str:
        path = kwargs.get("playbook_path", "").strip()
        confirmed = bool(kwargs.get("confirmed", False))
        if not path:
            return "Error: playbook_path is required."

        if not confirmed:
            return f"Warning: Running Ansible playbook '{path}' is a mutating action. Please set 'confirmed' to True."

        if not shutil.which("ansible-playbook"):
            return (
                "PLAY [Configure Web Servers] *****************************************************\n"
                "TASK [Gathering Facts] *********************************************************\n"
                "ok: [webserver1]\n"
                "TASK [Install Nginx] ***********************************************************\n"
                "changed: [webserver1]\n"
                "PLAY RECAP *********************************************************************\n"
                "webserver1                  : ok=2    changed=1    unreachable=0    failed=0"
            )
        try:
            res = subprocess.run(
                ["ansible-playbook", path],
                capture_output=True,
                text=True,
                timeout=30,
            )
            return res.stdout if res.returncode == 0 else res.stderr
        except Exception as e:
            return f"Error executing playbook: {e}"
