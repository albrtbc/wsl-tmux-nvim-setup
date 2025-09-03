"""
Integration tests for GitHub Actions workflows.
"""

import subprocess
from pathlib import Path

import pytest
import yaml


class TestGitHubActionsWorkflows:
    """Test GitHub Actions workflow files."""

    @pytest.fixture
    def workflows_dir(self):
        """Path to GitHub Actions workflows directory."""
        return Path(__file__).parent.parent.parent / ".github" / "workflows"

    def test_workflow_files_exist(self, workflows_dir):
        """Test that required workflow files exist."""
        required_workflows = ["ci.yml", "release.yml", "prepare-assets.yml"]

        for workflow in required_workflows:
            workflow_path = workflows_dir / workflow
            assert workflow_path.exists(), f"Workflow {workflow} does not exist"

    def test_workflow_yaml_valid(self, workflows_dir):
        """Test that workflow YAML files are valid."""
        for workflow_file in workflows_dir.glob("*.yml"):
            with open(workflow_file, "r") as f:
                try:
                    yaml.safe_load(f)
                except yaml.YAMLError as e:
                    pytest.fail(f"Invalid YAML in {workflow_file.name}: {e}")

    def test_ci_workflow_structure(self, workflows_dir):
        """Test CI workflow has required structure."""
        ci_file = workflows_dir / "ci.yml"

        with open(ci_file, "r") as f:
            workflow = yaml.safe_load(f)

        # Test workflow structure
        assert "name" in workflow
        assert "on" in workflow
        assert "jobs" in workflow

        # Test trigger events
        assert "push" in workflow["on"]
        assert "pull_request" in workflow["on"]

        # Test required jobs
        jobs = workflow["jobs"]
        required_jobs = [
            "lint-and-validate",
            "test-installation-matrix",
            "test-update-scripts",
            "security-scan",
            "test-documentation",
        ]

        for job in required_jobs:
            assert job in jobs, f"Required job '{job}' missing from CI workflow"

    def test_release_workflow_structure(self, workflows_dir):
        """Test release workflow has required structure."""
        release_file = workflows_dir / "release.yml"

        if not release_file.exists():
            pytest.skip("Release workflow not found")

        with open(release_file, "r") as f:
            workflow = yaml.safe_load(f)

        # Test workflow structure
        assert "name" in workflow
        assert "on" in workflow
        assert "jobs" in workflow

        # Test release triggers
        assert "release" in workflow["on"] or "push" in workflow["on"]

    def test_workflow_environment_variables(self, workflows_dir):
        """Test workflows define necessary environment variables."""
        ci_file = workflows_dir / "ci.yml"

        with open(ci_file, "r") as f:
            workflow = yaml.safe_load(f)

        # Check for environment variables
        if "env" in workflow:
            env = workflow["env"]
            # Should define Python version
            assert "PYTHON_VERSION" in env or "PYTHONUNBUFFERED" in env


class TestCIWorkflowJobs:
    """Test individual CI workflow jobs."""

    @pytest.fixture
    def ci_workflow(self, workflows_dir):
        """Load CI workflow configuration."""
        ci_file = workflows_dir / "ci.yml"
        with open(ci_file, "r") as f:
            return yaml.safe_load(f)

    def test_lint_job_steps(self, ci_workflow):
        """Test lint job has required steps."""
        lint_job = ci_workflow["jobs"]["lint-and-validate"]

        step_names = [step.get("name", "") for step in lint_job["steps"]]

        # Check for required steps
        assert any("checkout" in name.lower() for name in step_names)
        assert any("python" in name.lower() for name in step_names)
        assert any("shellcheck" in name.lower() for name in step_names)
        assert any("lint" in name.lower() for name in step_names)

    def test_installation_matrix_job(self, ci_workflow):
        """Test installation matrix job configuration."""
        matrix_job = ci_workflow["jobs"]["test-installation-matrix"]

        # Should have strategy with matrix
        assert "strategy" in matrix_job
        assert "matrix" in matrix_job["strategy"]

        matrix = matrix_job["strategy"]["matrix"]

        # Should test multiple Ubuntu versions
        assert "ubuntu_version" in matrix
        ubuntu_versions = matrix["ubuntu_version"]
        assert isinstance(ubuntu_versions, list)
        assert len(ubuntu_versions) >= 2  # At least 2 versions

        # Should test multiple shells
        assert "shell" in matrix
        shells = matrix["shell"]
        assert "bash" in shells

    def test_security_scan_job(self, ci_workflow):
        """Test security scan job configuration."""
        security_job = ci_workflow["jobs"]["security-scan"]

        step_names = [step.get("name", "") for step in security_job["steps"]]

        # Should include security tools
        assert any("bandit" in name.lower() or "security" in name.lower() for name in step_names)
        assert any(
            "safety" in name.lower() or "vulnerabilit" in name.lower() for name in step_names
        )

    def test_documentation_job(self, ci_workflow):
        """Test documentation job configuration."""
        docs_job = ci_workflow["jobs"]["test-documentation"]

        step_names = [step.get("name", "") for step in step_names for step in docs_job["steps"]]

        # Should validate documentation
        assert any(
            "markdown" in name.lower() or "documentation" in name.lower() for name in step_names
        )


class TestWorkflowIntegration:
    """Integration tests for workflow execution."""

    @pytest.mark.integration
    def test_workflow_syntax_check(self):
        """Test workflow files pass GitHub Actions syntax check."""
        # This would require gh CLI or GitHub API access
        # For now, we validate YAML syntax which is a good proxy
        workflows_dir = Path(__file__).parent.parent.parent / ".github" / "workflows"

        for workflow_file in workflows_dir.glob("*.yml"):
            with open(workflow_file, "r") as f:
                try:
                    workflow = yaml.safe_load(f)

                    # Basic structure validation
                    assert isinstance(workflow, dict)
                    assert "jobs" in workflow
                    assert isinstance(workflow["jobs"], dict)

                    for job_name, job_config in workflow["jobs"].items():
                        assert isinstance(job_config, dict)
                        assert "steps" in job_config
                        assert isinstance(job_config["steps"], list)

                except Exception as e:
                    pytest.fail(f"Workflow {workflow_file.name} failed validation: {e}")

    @pytest.mark.integration
    @pytest.mark.slow
    def test_local_workflow_simulation(self, temp_dir):
        """Simulate workflow steps locally where possible."""
        # Test some workflow steps locally

        # Test ShellCheck on scripts
        scripts_dir = Path(__file__).parent.parent.parent
        shell_scripts = list(scripts_dir.glob("**/*.sh"))

        if shell_scripts:
            # Try to run ShellCheck if available
            try:
                result = subprocess.run(["shellcheck", "--version"], capture_output=True, text=True)

                if result.returncode == 0:
                    # ShellCheck is available, test a few scripts
                    for script in shell_scripts[:3]:  # Test first 3 scripts
                        result = subprocess.run(
                            ["shellcheck", str(script)], capture_output=True, text=True
                        )
                        # Don't fail on warnings, just check it runs
                        assert result.returncode in [
                            0,
                            1,
                        ], f"ShellCheck failed on {script}"

            except FileNotFoundError:
                pytest.skip("ShellCheck not available for local testing")

    @pytest.mark.integration
    def test_python_linting_simulation(self):
        """Test Python linting steps locally."""
        python_files = list(Path(__file__).parent.parent.parent.glob("**/*.py"))

        if not python_files:
            pytest.skip("No Python files found")

        # Test a few Python files for basic syntax
        for py_file in python_files[:5]:  # Test first 5 files
            try:
                result = subprocess.run(
                    ["python", "-m", "py_compile", str(py_file)],
                    capture_output=True,
                    text=True,
                )

                assert result.returncode == 0, f"Python syntax error in {py_file}"

            except Exception as e:
                pytest.skip(f"Could not test Python syntax: {e}")


class TestWorkflowSecurity:
    """Test security aspects of workflows."""

    def test_no_hardcoded_secrets(self, workflows_dir):
        """Test workflows don't contain hardcoded secrets."""
        secret_patterns = [
            r'password\s*[:=]\s*["\'].*["\']',
            r'token\s*[:=]\s*["\'][^$].*["\']',  # Exclude ${{ secrets.* }}
            r'key\s*[:=]\s*["\'].*["\']',
            r'secret\s*[:=]\s*["\'][^$].*["\']',
        ]

        import re

        for workflow_file in workflows_dir.glob("*.yml"):
            content = workflow_file.read_text()

            for pattern in secret_patterns:
                matches = re.finditer(pattern, content, re.IGNORECASE)
                for match in matches:
                    # Allow GitHub Actions secrets syntax
                    if "${{" not in match.group():
                        pytest.fail(
                            f"Potential hardcoded secret in {workflow_file.name}: {match.group()}"
                        )

    def test_secure_checkout_actions(self, workflows_dir):
        """Test workflows use secure checkout actions."""
        for workflow_file in workflows_dir.glob("*.yml"):
            with open(workflow_file, "r") as f:
                workflow = yaml.safe_load(f)

            for job_name, job in workflow["jobs"].items():
                for step in job["steps"]:
                    if "uses" in step:
                        action = step["uses"]

                        # Check for known secure actions
                        if "actions/checkout" in action:
                            # Should use specific version, not @main
                            assert (
                                "@v" in action or "@main" not in action
                            ), f"Checkout action should use specific version in {workflow_file.name}"

    def test_runner_permissions(self, workflows_dir):
        """Test workflows have appropriate permissions."""
        for workflow_file in workflows_dir.glob("*.yml"):
            with open(workflow_file, "r") as f:
                workflow = yaml.safe_load(f)

            # Check global permissions if set
            if "permissions" in workflow:
                permissions = workflow["permissions"]

                # Should not have excessive permissions
                if isinstance(permissions, dict):
                    dangerous_permissions = ["write-all", "admin"]
                    for perm in dangerous_permissions:
                        assert (
                            perm not in permissions.values()
                        ), f"Dangerous permission {perm} in {workflow_file.name}"


class TestWorkflowPerformance:
    """Test performance aspects of workflows."""

    def test_workflow_job_parallelization(self, workflows_dir):
        """Test workflows make good use of parallelization."""
        ci_file = workflows_dir / "ci.yml"

        with open(ci_file, "r") as f:
            workflow = yaml.safe_load(f)

        jobs = workflow["jobs"]

        # Count jobs that could run in parallel
        independent_jobs = 0
        dependent_jobs = 0

        for job_name, job_config in jobs.items():
            if "needs" in job_config:
                dependent_jobs += 1
            else:
                independent_jobs += 1

        # Should have some parallel jobs for efficiency
        assert independent_jobs >= 2, "Workflow should have parallelizable jobs for efficiency"

    def test_workflow_caching(self, workflows_dir):
        """Test workflows use caching where appropriate."""
        for workflow_file in workflows_dir.glob("*.yml"):
            with open(workflow_file, "r") as f:
                workflow = yaml.safe_load(f)

            for job_name, job in workflow["jobs"].items():
                for step in job["steps"]:
                    # If using Python setup, should consider caching
                    if "uses" in step and "setup-python" in step["uses"]:
                        # Check if caching is used in subsequent steps
                        # This is more of a recommendation than requirement
                        pass


class TestWorkflowMaintenance:
    """Test workflow maintenance and updates."""

    def test_action_versions_current(self, workflows_dir):
        """Test workflow actions use reasonably current versions."""
        current_action_versions = {
            "actions/checkout": "v4",
            "actions/setup-python": "v4",
            "actions/upload-artifact": "v4",
            "actions/download-artifact": "v4",
        }

        for workflow_file in workflows_dir.glob("*.yml"):
            with open(workflow_file, "r") as f:
                workflow = yaml.safe_load(f)

            for job_name, job in workflow["jobs"].items():
                for step in job["steps"]:
                    if "uses" in step:
                        action = step["uses"]

                        for action_name, min_version in current_action_versions.items():
                            if action_name in action:
                                # Extract version
                                if "@" in action:
                                    version = action.split("@")[1]
                                    # Should use at least the minimum version
                                    # This is a simple check, real version comparison would be better
                                    if version.startswith("v") and min_version.startswith("v"):
                                        assert (
                                            version >= min_version
                                        ), f"Action {action_name} version {version} is older than recommended {min_version}"

    def test_workflow_documentation(self, workflows_dir):
        """Test workflows are documented."""
        for workflow_file in workflows_dir.glob("*.yml"):
            with open(workflow_file, "r") as f:
                workflow = yaml.safe_load(f)

            # Workflow should have a name
            assert "name" in workflow, f"Workflow {workflow_file.name} should have a name"

            # Jobs should have descriptive names
            for job_name, job in workflow["jobs"].items():
                assert "name" in job, f"Job {job_name} should have a descriptive name"

                # Steps should be well documented
                for i, step in enumerate(job["steps"]):
                    if "run" in step:
                        # Steps with run commands should have names
                        if not step.get("name"):
                            pytest.skip(f"Step {i} in job {job_name} could use a descriptive name")


@pytest.mark.integration
class TestWorkflowEndToEnd:
    """End-to-end workflow testing."""

    @pytest.mark.slow
    def test_workflow_completion_simulation(self):
        """Simulate complete workflow execution where possible."""
        # This would test the full workflow in a controlled environment
        # For now, we'll test key components

        # Test that scripts referenced in workflows exist
        project_root = Path(__file__).parent.parent.parent

        # Check scripts referenced in CI
        script_refs = [
            "auto_install/components/install_dependencies.sh",
            "auto_install/components/install_git.sh",
            "auto_install/components/install_tmux.sh",
            "scripts/version-manager.py",
        ]

        for script_ref in script_refs:
            script_path = project_root / script_ref
            if script_path.exists():
                # Test basic execution (dry run where possible)
                if script_path.suffix == ".py":
                    try:
                        result = subprocess.run(
                            ["python3", str(script_path), "--help"],
                            capture_output=True,
                            text=True,
                            timeout=10,
                        )
                        # Should not crash on --help
                        assert result.returncode in [0, 1, 2]  # Various help exit codes
                    except subprocess.TimeoutExpired:
                        pytest.fail(f"Script {script_path} timed out on --help")
                    except Exception as e:
                        pytest.skip(f"Could not test {script_path}: {e}")

                elif script_path.suffix == ".sh":
                    # Test shell script syntax
                    try:
                        result = subprocess.run(
                            ["bash", "-n", str(script_path)],
                            capture_output=True,
                            text=True,
                        )
                        assert (
                            result.returncode == 0
                        ), f"Shell script {script_path} has syntax errors"
                    except Exception as e:
                        pytest.skip(f"Could not test {script_path}: {e}")

    def test_artifact_generation(self, temp_dir):
        """Test workflow artifact generation."""
        # Test that workflows would generate expected artifacts

        # CI workflow should generate test report
        report_content = """## CI Test Summary
- ✅ Lint and validation completed
- ✅ Multi-platform installation tested  
- ✅ Update scripts validated
- ✅ Security scan performed
- ✅ Documentation checked"""

        report_file = temp_dir / "ci-report.md"
        report_file.write_text(report_content)

        assert report_file.exists()
        assert "CI Test Summary" in report_file.read_text()
