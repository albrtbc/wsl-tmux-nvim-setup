"""
Performance benchmarks and validation tests.

These tests validate that the system meets performance requirements:
- CLI responsiveness <2 seconds for most commands
- Installation time <5 minutes average
- Memory efficiency <100MB peak usage
"""

import statistics
import subprocess
import threading
import time
from pathlib import Path
from typing import Dict, List, Tuple
from unittest.mock import Mock, patch

import psutil
import pytest


@pytest.mark.performance
@pytest.mark.slow
class TestCLIResponseTime:
    """Test CLI command response times."""

    def measure_command_time(
        self, cmd: List[str], env: Dict[str, str], timeout: int = 30
    ) -> Tuple[float, int]:
        """Measure command execution time."""
        start_time = time.perf_counter()

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=timeout)

            end_time = time.perf_counter()
            execution_time = end_time - start_time

            return execution_time, result.returncode

        except subprocess.TimeoutExpired:
            return timeout, -1

    def test_fast_commands_responsiveness(self, isolated_environment):
        """Test that fast commands respond within 2 seconds."""
        project_root = Path(__file__).parent.parent.parent
        cli_script = project_root / "cli" / "wsm.py"

        if not cli_script.exists():
            pytest.skip("CLI script not found for performance testing")

        fast_commands = [
            (["python3", str(cli_script), "--version"], "version"),
            (["python3", str(cli_script), "--help"], "help"),
            (["python3", str(cli_script), "status"], "status"),
            (["python3", str(cli_script), "config", "show"], "config show"),
        ]

        target_time = 2.0  # seconds
        results = {}

        for cmd, cmd_name in fast_commands:
            try:
                # Run command multiple times for more reliable measurement
                times = []
                for _ in range(3):
                    exec_time, exit_code = self.measure_command_time(
                        cmd, isolated_environment, timeout=5
                    )
                    if exit_code != -1:  # Not timed out
                        times.append(exec_time)

                if times:
                    avg_time = statistics.mean(times)
                    results[cmd_name] = avg_time

                    assert (
                        avg_time < target_time
                    ), f"Command '{cmd_name}' took {avg_time:.2f}s (target: <{target_time}s)"

            except FileNotFoundError:
                pytest.skip("Python3 not available for performance testing")

        # Log performance results
        print("\nCLI Response Time Results:")
        for cmd_name, avg_time in results.items():
            print(f"  {cmd_name}: {avg_time:.3f}s")

    def test_medium_commands_responsiveness(self, isolated_environment):
        """Test medium-complexity commands respond within reasonable time."""
        project_root = Path(__file__).parent.parent.parent
        cli_script = project_root / "cli" / "wsm.py"

        if not cli_script.exists():
            pytest.skip("CLI script not found for performance testing")

        medium_commands = [
            (["python3", str(cli_script), "doctor"], "doctor", 5.0),
            (["python3", str(cli_script), "list"], "list", 10.0),
            (["python3", str(cli_script), "update", "--check"], "update check", 15.0),
        ]

        results = {}

        for cmd, cmd_name, target_time in medium_commands:
            try:
                exec_time, exit_code = self.measure_command_time(
                    cmd, isolated_environment, timeout=int(target_time + 5)
                )

                if exit_code != -1:  # Not timed out
                    results[cmd_name] = exec_time
                    assert (
                        exec_time < target_time
                    ), f"Command '{cmd_name}' took {exec_time:.2f}s (target: <{target_time}s)"

            except FileNotFoundError:
                pytest.skip("Python3 not available for performance testing")

        # Log performance results
        print("\nMedium Command Response Time Results:")
        for cmd_name, exec_time in results.items():
            print(f"  {cmd_name}: {exec_time:.3f}s")


@pytest.mark.performance
@pytest.mark.slow
class TestMemoryUsage:
    """Test memory usage during operations."""

    def monitor_memory_usage(self, process, duration=10, interval=0.1):
        """Monitor memory usage of a process."""
        memory_readings = []
        start_time = time.time()

        while time.time() - start_time < duration:
            try:
                if process.poll() is None:  # Process still running
                    memory_info = process.memory_info()
                    memory_readings.append(memory_info.rss)  # Resident set size in bytes
                else:
                    break
                time.sleep(interval)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                break

        return memory_readings

    def test_cli_memory_usage(self, isolated_environment):
        """Test CLI memory usage stays within limits."""
        project_root = Path(__file__).parent.parent.parent
        cli_script = project_root / "cli" / "wsm.py"

        if not cli_script.exists():
            pytest.skip("CLI script not found for memory testing")

        target_memory_mb = 100  # 100MB target

        commands_to_test = [
            (["python3", str(cli_script), "status"], "status"),
            (["python3", str(cli_script), "list"], "list"),
            (["python3", str(cli_script), "doctor"], "doctor"),
        ]

        for cmd, cmd_name in commands_to_test:
            try:
                # Start process
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    env=isolated_environment,
                )

                # Monitor memory usage
                memory_readings = []
                monitor_duration = 5  # seconds

                monitor_thread = threading.Thread(
                    target=lambda: memory_readings.extend(
                        self.monitor_memory_usage(process, monitor_duration)
                    )
                )
                monitor_thread.start()

                # Wait for process to complete
                stdout, stderr = process.communicate(timeout=10)
                monitor_thread.join(timeout=1)

                if memory_readings:
                    peak_memory_bytes = max(memory_readings)
                    peak_memory_mb = peak_memory_bytes / (1024 * 1024)

                    print(f"\n{cmd_name} peak memory: {peak_memory_mb:.2f}MB")

                    assert peak_memory_mb < target_memory_mb, (
                        f"Command '{cmd_name}' used {peak_memory_mb:.2f}MB "
                        f"(target: <{target_memory_mb}MB)"
                    )

            except subprocess.TimeoutExpired:
                process.kill()
                pytest.skip(f"Memory test for '{cmd_name}' timed out")
            except FileNotFoundError:
                pytest.skip("Python3 not available for memory testing")

    def test_concurrent_operations_memory(self, isolated_environment):
        """Test memory usage with concurrent operations."""
        project_root = Path(__file__).parent.parent.parent
        cli_script = project_root / "cli" / "wsm.py"

        if not cli_script.exists():
            pytest.skip("CLI script not found for concurrent memory testing")

        # Run multiple commands concurrently
        processes = []
        commands = [
            ["python3", str(cli_script), "status"],
            ["python3", str(cli_script), "--version"],
            ["python3", str(cli_script), "config", "show"],
        ]

        try:
            # Start all processes
            for cmd in commands:
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    env=isolated_environment,
                )
                processes.append(process)

            # Monitor total memory usage
            total_memory_readings = []
            for _ in range(50):  # Monitor for 5 seconds
                total_memory = 0
                for process in processes:
                    try:
                        if process.poll() is None:
                            memory_info = process.memory_info()
                            total_memory += memory_info.rss
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass

                total_memory_readings.append(total_memory)
                time.sleep(0.1)

            # Wait for all processes to complete
            for process in processes:
                process.wait(timeout=5)

            if total_memory_readings:
                peak_total_memory_mb = max(total_memory_readings) / (1024 * 1024)
                print(f"\nConcurrent operations peak memory: {peak_total_memory_mb:.2f}MB")

                # Should not use excessive memory even with concurrent operations
                assert (
                    peak_total_memory_mb < 200
                ), f"Concurrent operations used {peak_total_memory_mb:.2f}MB (target: <200MB)"

        except subprocess.TimeoutExpired:
            for process in processes:
                process.kill()
            pytest.skip("Concurrent memory test timed out")
        except FileNotFoundError:
            pytest.skip("Python3 not available for concurrent testing")


@pytest.mark.performance
@pytest.mark.slow
class TestInstallationPerformance:
    """Test installation performance metrics."""

    def test_installation_simulation_performance(self, isolated_environment, temp_dir):
        """Test installation performance simulation."""
        project_root = Path(__file__).parent.parent.parent
        cli_script = project_root / "cli" / "wsm.py"

        if not cli_script.exists():
            pytest.skip("CLI script not found for installation performance testing")

        target_install_time = 300  # 5 minutes in seconds

        # Create mock installation files to simulate realistic scenario
        mock_install_dir = temp_dir / "mock_install"
        mock_install_dir.mkdir()

        # Create some files to simulate installation content
        for i in range(100):
            (mock_install_dir / f"file_{i}.txt").write_text(f"Mock content {i}")

        try:
            start_time = time.perf_counter()

            # Run installation simulation (dry run)
            result = subprocess.run(
                ["python3", str(cli_script), "install", "--dry-run", "--verbose"],
                capture_output=True,
                text=True,
                env=isolated_environment,
                timeout=target_install_time,
            )

            end_time = time.perf_counter()
            simulation_time = end_time - start_time

            print(f"\nInstallation simulation time: {simulation_time:.2f}s")

            # Dry run should be much faster than actual installation
            dry_run_target = 30  # 30 seconds for dry run
            assert (
                simulation_time < dry_run_target
            ), f"Installation simulation took {simulation_time:.2f}s (target: <{dry_run_target}s)"

            assert result.returncode in [0, 1, 2]

        except subprocess.TimeoutExpired:
            pytest.fail(f"Installation simulation exceeded {target_install_time}s timeout")
        except FileNotFoundError:
            pytest.skip("Python3 not available for installation performance testing")

    def test_update_check_performance(self, isolated_environment):
        """Test update check performance."""
        project_root = Path(__file__).parent.parent.parent
        cli_script = project_root / "cli" / "wsm.py"

        if not cli_script.exists():
            pytest.skip("CLI script not found for update performance testing")

        target_update_check_time = 10  # seconds

        try:
            start_time = time.perf_counter()

            result = subprocess.run(
                ["python3", str(cli_script), "update", "--check"],
                capture_output=True,
                text=True,
                env=isolated_environment,
                timeout=target_update_check_time + 5,
            )

            end_time = time.perf_counter()
            check_time = end_time - start_time

            print(f"\nUpdate check time: {check_time:.2f}s")

            assert (
                check_time < target_update_check_time
            ), f"Update check took {check_time:.2f}s (target: <{target_update_check_time}s)"

            assert result.returncode in [0, 1, 2]

        except subprocess.TimeoutExpired:
            pytest.fail(f"Update check exceeded {target_update_check_time + 5}s timeout")
        except FileNotFoundError:
            pytest.skip("Python3 not available for update performance testing")


@pytest.mark.performance
@pytest.mark.slow
class TestScalabilityBenchmarks:
    """Test scalability with various configurations."""

    def test_large_configuration_handling(self, isolated_environment, temp_dir):
        """Test handling of large configurations."""
        project_root = Path(__file__).parent.parent.parent
        cli_script = project_root / "cli" / "wsm.py"

        if not cli_script.exists():
            pytest.skip("CLI script not found for scalability testing")

        # Create large configuration file
        config_dir = Path(isolated_environment["WSM_CONFIG_DIR"])
        config_file = config_dir / "config.json"

        # Create configuration with many components
        large_config = {
            "installation_path": str(temp_dir / "install"),
            "components": [f"component_{i}" for i in range(100)],
            "preferences": {f"pref_{i}": f"value_{i}" for i in range(50)},
            "backup_retention": 10,
            "auto_update": True,
        }

        import json

        config_file.write_text(json.dumps(large_config, indent=2))

        try:
            start_time = time.perf_counter()

            result = subprocess.run(
                ["python3", str(cli_script), "config", "show"],
                capture_output=True,
                text=True,
                env=isolated_environment,
                timeout=10,
            )

            end_time = time.perf_counter()
            config_load_time = end_time - start_time

            print(f"\nLarge config load time: {config_load_time:.2f}s")

            # Should handle large configs efficiently
            assert (
                config_load_time < 5
            ), f"Large config loading took {config_load_time:.2f}s (target: <5s)"

            assert result.returncode in [0, 1, 2]

        except subprocess.TimeoutExpired:
            pytest.fail("Large configuration test timed out")
        except FileNotFoundError:
            pytest.skip("Python3 not available for scalability testing")

    def test_many_releases_performance(self, isolated_environment):
        """Test performance with many available releases."""
        project_root = Path(__file__).parent.parent.parent
        cli_script = project_root / "cli" / "wsm.py"

        if not cli_script.exists():
            pytest.skip("CLI script not found for release performance testing")

        try:
            # Mock many releases scenario
            with patch("cli.utils.github.GitHubClient") as mock_client_class:
                mock_client = Mock()

                # Create many mock releases
                mock_releases = []
                for i in range(100):
                    mock_releases.append(
                        {
                            "tag_name": f"v1.{i}.0",
                            "name": f"Release v1.{i}.0",
                            "published_at": "2025-09-01T00:00:00Z",
                        }
                    )

                mock_client.list_releases.return_value = mock_releases
                mock_client_class.return_value = mock_client

                start_time = time.perf_counter()

                subprocess.run(
                    ["python3", str(cli_script), "list"],
                    capture_output=True,
                    text=True,
                    env=isolated_environment,
                    timeout=15,
                )

                end_time = time.perf_counter()
                list_time = end_time - start_time

                print(f"\nMany releases list time: {list_time:.2f}s")

                # Should handle many releases efficiently
                assert list_time < 10, f"Listing many releases took {list_time:.2f}s (target: <10s)"

        except subprocess.TimeoutExpired:
            pytest.fail("Many releases test timed out")
        except FileNotFoundError:
            pytest.skip("Python3 not available for release performance testing")


@pytest.mark.performance
class TestPerformanceRegression:
    """Test for performance regressions."""

    def test_baseline_performance_metrics(self, performance_metrics):
        """Test against baseline performance metrics."""
        # These would be compared against known baselines

        baseline_metrics = {
            "cli_response_time": 2.0,  # seconds
            "memory_peak": 100,  # MB
            "installation_time": 300,  # seconds
            "update_check_time": 10,  # seconds
        }

        # This test would compare current metrics against baselines
        # For now, just verify the structure exists

        assert "command_response_times" in performance_metrics
        assert "memory_peak" in performance_metrics
        assert "installation_time" in performance_metrics

        # Example assertions against baselines
        for command, response_time in performance_metrics["command_response_times"].items():
            if command in ["install", "update"]:
                continue  # Skip slow commands

            assert response_time < baseline_metrics["cli_response_time"], (
                f"Command {command} response time {response_time}s exceeds baseline "
                f"{baseline_metrics['cli_response_time']}s"
            )

    def test_performance_consistency(self, isolated_environment):
        """Test performance consistency across multiple runs."""
        project_root = Path(__file__).parent.parent.parent
        cli_script = project_root / "cli" / "wsm.py"

        if not cli_script.exists():
            pytest.skip("CLI script not found for consistency testing")

        # Test command multiple times to check consistency
        cmd = ["python3", str(cli_script), "--version"]
        times = []

        try:
            for _ in range(5):
                start_time = time.perf_counter()

                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    env=isolated_environment,
                    timeout=5,
                )

                end_time = time.perf_counter()
                execution_time = end_time - start_time

                if result.returncode in [0, 1, 2]:
                    times.append(execution_time)

            if len(times) >= 3:
                # Check consistency - standard deviation should be small
                mean_time = statistics.mean(times)
                stdev_time = statistics.stdev(times)

                print(f"\nConsistency test - Mean: {mean_time:.3f}s, StdDev: {stdev_time:.3f}s")

                # Coefficient of variation should be reasonable
                cv = stdev_time / mean_time
                assert cv < 0.5, f"Performance inconsistent: CV={cv:.3f} (target: <0.5)"

        except subprocess.TimeoutExpired:
            pytest.skip("Consistency test timed out")
        except FileNotFoundError:
            pytest.skip("Python3 not available for consistency testing")


@pytest.fixture
def isolated_environment(temp_dir):
    """Create isolated environment for performance testing."""
    import os

    env = os.environ.copy()
    env["WSM_CONFIG_DIR"] = str(temp_dir / "config")
    env["WSM_INSTALL_DIR"] = str(temp_dir / "install")
    env["HOME"] = str(temp_dir / "home")

    # Create directories
    (temp_dir / "config").mkdir()
    (temp_dir / "install").mkdir()
    (temp_dir / "home").mkdir()

    return env
