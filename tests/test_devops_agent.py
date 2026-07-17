from typing import Any
from unittest.mock import patch
from src.application.tools.devops_tools import (
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


@patch("shutil.which", return_value=None)
def test_docker_tools(mock_which: Any) -> None:
    # 1. List
    list_tool = DockerListContainersTool()
    res_list = list_tool.execute()
    assert "CONTAINER ID" in res_list
    assert "web-app" in res_list

    # 2. Restart (Mutating - needs confirmation)
    restart_tool = DockerRestartContainerTool()
    res_unconfirmed = restart_tool.execute(container_id="web-app", confirmed=False)
    assert "Warning: Restarting container" in res_unconfirmed
    assert "confirmed" in res_unconfirmed

    res_confirmed = restart_tool.execute(container_id="web-app", confirmed=True)
    assert "Successfully restarted container" in res_confirmed

    # 3. View Logs
    logs_tool = DockerViewLogsTool()
    res_logs = logs_tool.execute(container_id="web-app")
    assert "Starting application server" in res_logs


@patch("shutil.which", return_value=None)
def test_kubernetes_tools(mock_which: Any) -> None:
    # 1. List Pods
    list_tool = K8sListPodsTool()
    res_list = list_tool.execute()
    assert "NAMESPACE" in res_list
    assert "web-deployment" in res_list

    # 2. Describe Pod
    desc_tool = K8sDescribePodTool()
    res_desc = desc_tool.execute(pod_name="web-pod")
    assert "Name:         web-pod" in res_desc

    # 3. Restart Deployment (Mutating - needs confirmation)
    restart_tool = K8sRestartDeploymentTool()
    res_unconfirmed = restart_tool.execute(
        deployment_name="web-deploy", confirmed=False
    )
    assert "Warning: Restarting deployment" in res_unconfirmed

    res_confirmed = restart_tool.execute(deployment_name="web-deploy", confirmed=True)
    assert "Successfully restarted deployment" in res_confirmed


@patch("shutil.which", return_value=None)
def test_aws_tools(mock_which: Any) -> None:
    # 1. List EC2
    ec2_tool = AWSListEC2Tool()
    res_ec2 = ec2_tool.execute()
    assert "InstanceId:" in res_ec2

    # 2. List S3
    s3_tool = AWSS3ListBucketsTool()
    res_s3 = s3_tool.execute()
    assert "prod-web-assets-bucket" in res_s3

    # 3. Logs
    logs_tool = AWSCloudWatchLogsTool()
    res_logs = logs_tool.execute(log_group_name="/aws/lambda/image-resizer")
    assert "Lambda execution started" in res_logs


def test_jenkins_tools() -> None:
    # 1. Run Pipeline (Mutating - needs confirmation)
    run_tool = JenkinsRunPipelineTool()
    res_unconfirmed = run_tool.execute(pipeline_name="prod-deploy", confirmed=False)
    assert "Warning: Running Jenkins pipeline" in res_unconfirmed

    res_confirmed = run_tool.execute(pipeline_name="prod-deploy", confirmed=True)
    assert "triggered build" in res_confirmed

    # 2. View Logs
    logs_tool = JenkinsViewBuildLogsTool()
    res_logs = logs_tool.execute(pipeline_name="prod-deploy")
    assert "Finished: SUCCESS" in res_logs


@patch("shutil.which", return_value=None)
def test_git_tools(mock_which: Any) -> None:
    # 1. Commit
    commit_tool = GitCommitTool()
    res_commit = commit_tool.execute(message="Initial commit")
    assert "Successfully committed changes" in res_commit

    # 2. Push (Mutating - needs confirmation)
    push_tool = GitPushTool()
    res_unconfirmed = push_tool.execute(confirmed=False)
    assert "Warning: Pushing to remote" in res_unconfirmed

    res_confirmed = push_tool.execute(confirmed=True)
    assert "Successfully pushed commits" in res_confirmed

    # 3. Clone
    clone_tool = GitCloneTool()
    res_clone = clone_tool.execute(repo_url="https://github.com/test/repo.git")
    assert "Cloning into" in res_clone


@patch("shutil.which", return_value=None)
def test_terraform_tools(mock_which: Any) -> None:
    # 1. Plan
    plan_tool = TerraformPlanTool()
    res_plan = plan_tool.execute()
    assert "Terraform will perform the following actions" in res_plan

    # 2. Apply (Mutating - needs confirmation)
    apply_tool = TerraformApplyTool()
    res_unconfirmed = apply_tool.execute(confirmed=False)
    assert "Warning: Applying Terraform" in res_unconfirmed

    res_confirmed = apply_tool.execute(confirmed=True)
    assert "Apply complete" in res_confirmed


@patch("shutil.which", return_value=None)
def test_ansible_tools(mock_which: Any) -> None:
    # 1. Run Playbook (Mutating - needs confirmation)
    ansible_tool = AnsibleRunPlaybookTool()
    res_unconfirmed = ansible_tool.execute(playbook_path="site.yml", confirmed=False)
    assert "Warning: Running Ansible playbook" in res_unconfirmed

    res_confirmed = ansible_tool.execute(playbook_path="site.yml", confirmed=True)
    assert "Configure Web Servers" in res_confirmed
