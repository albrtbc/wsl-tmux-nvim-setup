#!/usr/bin/env python3
"""
Comprehensive test runner for WSL-Tmux-Nvim-Setup.

This script runs the complete test suite with proper categorization,
reporting, and performance metrics collection.
"""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional


class TestRunner:
    """Comprehensive test runner with categorized execution and reporting."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.test_results = {}
        self.start_time = None
        self.total_duration = 0

    def run_test_category(
        self, category: str, markers: List[str], timeout: int = 300, capture_output: bool = True
    ) -> Dict:
        """Run tests for a specific category."""
        print(f"\n{'='*60}")
        print(f"Running {category.upper()} Tests")
        print(f"{'='*60}")

        # Build pytest command
        cmd = [
            sys.executable,
            "-m",
            "pytest",
            f"tests/{category}/",
            "-v",
            "--tb=short",
            "--strict-markers",
            "--strict-config",
        ]

        # Add markers if specified
        if markers:
            for marker in markers:
                cmd.extend(["-m", marker])

        # Add coverage for unit tests
        if category == "unit":
            cmd.extend(
                [
                    "--cov=cli",
                    "--cov-report=term-missing",
                    "--cov-report=html:htmlcov",
                    "--cov-fail-under=70",
                ]
            )

        start_time = time.time()

        try:
            if capture_output:
                result = subprocess.run(
                    cmd, capture_output=True, text=True, timeout=timeout, cwd=self.project_root
                )
            else:
                result = subprocess.run(cmd, timeout=timeout, cwd=self.project_root)
                # Create mock result for non-captured runs
                result.stdout = ""
                result.stderr = ""

            end_time = time.time()
            duration = end_time - start_time

            # Parse results
            test_results = {
                "category": category,
                "duration": duration,
                "exit_code": result.returncode,
                "passed": result.returncode == 0,
                "output": (
                    result.stdout
                    if capture_output
                    else f"Tests executed (duration: {duration:.2f}s)"
                ),
                "errors": result.stderr if capture_output else "",
                "markers": markers,
                "timeout": timeout,
            }

            # Extract test counts from pytest output
            if result.stdout:
                test_results.update(self._parse_pytest_output(result.stdout))

            return test_results

        except subprocess.TimeoutExpired:
            return {
                "category": category,
                "duration": timeout,
                "exit_code": -1,
                "passed": False,
                "output": f"Tests timed out after {timeout}s",
                "errors": "Timeout",
                "markers": markers,
                "timeout": timeout,
                "timed_out": True,
            }
        except Exception as e:
            return {
                "category": category,
                "duration": 0,
                "exit_code": -2,
                "passed": False,
                "output": "",
                "errors": str(e),
                "markers": markers,
                "timeout": timeout,
                "error": True,
            }

    def _parse_pytest_output(self, output: str) -> Dict:
        """Parse pytest output to extract test statistics."""
        stats = {
            "tests_collected": 0,
            "tests_passed": 0,
            "tests_failed": 0,
            "tests_skipped": 0,
            "tests_error": 0,
        }

        # Look for pytest result summary
        lines = output.split("\n")
        for line in lines:
            if "collected" in line and "items" in line:
                try:
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if part == "collected":
                            stats["tests_collected"] = int(parts[i - 1])
                            break
                except (ValueError, IndexError):
                    pass

            # Parse final results line
            if " passed" in line or " failed" in line or " skipped" in line:
                try:
                    if " passed" in line:
                        stats["tests_passed"] = int(line.split(" passed")[0].split()[-1])
                    if " failed" in line:
                        stats["tests_failed"] = int(line.split(" failed")[0].split()[-1])
                    if " skipped" in line:
                        stats["tests_skipped"] = int(line.split(" skipped")[0].split()[-1])
                    if " error" in line:
                        stats["tests_error"] = int(line.split(" error")[0].split()[-1])
                except (ValueError, IndexError):
                    pass

        return stats

    def run_all_tests(self, quick: bool = False, include_slow: bool = True) -> Dict:
        """Run all test categories."""
        self.start_time = time.time()

        # Define test categories and configurations
        test_categories = [
            {
                "name": "unit",
                "markers": ["unit", "not slow"] if not include_slow else ["unit"],
                "timeout": 60 if quick else 180,
                "required": True,
            },
            {
                "name": "integration",
                "markers": ["integration", "not slow"] if not include_slow else ["integration"],
                "timeout": 120 if quick else 300,
                "required": True,
            },
            {
                "name": "e2e",
                "markers": ["e2e", "not slow"] if not include_slow else ["e2e"],
                "timeout": 180 if quick else 600,
                "required": False,
            },
            {
                "name": "performance",
                "markers": ["performance"],
                "timeout": 300 if quick else 900,
                "required": False,
            },
            {
                "name": "security",
                "markers": ["security"],
                "timeout": 60 if quick else 180,
                "required": True,
            },
        ]

        results = {}

        for test_config in test_categories:
            category = test_config["name"]

            # Skip optional categories in quick mode
            if quick and not test_config["required"]:
                print(f"\nSkipping {category} tests in quick mode")
                continue

            # Check if test directory exists
            test_dir = self.project_root / "tests" / category
            if not test_dir.exists():
                print(f"\nSkipping {category} tests - directory not found")
                results[category] = {
                    "category": category,
                    "skipped": True,
                    "reason": "Directory not found",
                }
                continue

            # Run tests for this category
            results[category] = self.run_test_category(
                category, test_config["markers"], test_config["timeout"]
            )

            # Print immediate results
            self._print_category_results(results[category])

        self.total_duration = time.time() - self.start_time
        self.test_results = results

        return results

    def _print_category_results(self, result: Dict):
        """Print results for a test category."""
        category = result["category"]
        duration = result.get("duration", 0)

        if result.get("skipped"):
            print(f"❓ {category.upper()}: SKIPPED ({result.get('reason', 'Unknown')})")
            return

        if result.get("timed_out"):
            print(f"⏰ {category.upper()}: TIMEOUT after {duration:.1f}s")
            return

        if result.get("error"):
            print(f"💥 {category.upper()}: ERROR - {result.get('errors', 'Unknown error')}")
            return

        status = "✅ PASSED" if result["passed"] else "❌ FAILED"
        print(f"{status} {category.upper()}: {duration:.1f}s", end="")

        # Add test counts if available
        if "tests_collected" in result and result["tests_collected"] > 0:
            collected = result["tests_collected"]
            passed = result.get("tests_passed", 0)
            failed = result.get("tests_failed", 0)
            skipped = result.get("tests_skipped", 0)

            print(f" ({passed}/{collected} passed", end="")
            if failed > 0:
                print(f", {failed} failed", end="")
            if skipped > 0:
                print(f", {skipped} skipped", end="")
            print(")")
        else:
            print()

    def print_summary(self):
        """Print comprehensive test summary."""
        print(f"\n{'='*60}")
        print("TEST SUMMARY")
        print(f"{'='*60}")

        if not self.test_results:
            print("No tests were run.")
            return

        total_passed = 0
        total_failed = 0
        total_skipped = 0
        total_collected = 0
        categories_run = 0
        categories_passed = 0

        for category, result in self.test_results.items():
            if result.get("skipped"):
                continue

            categories_run += 1
            if result.get("passed"):
                categories_passed += 1

            total_collected += result.get("tests_collected", 0)
            total_passed += result.get("tests_passed", 0)
            total_failed += result.get("tests_failed", 0)
            total_skipped += result.get("tests_skipped", 0)

        print(f"Categories Run: {categories_run}")
        print(f"Categories Passed: {categories_passed}")
        print(f"Total Duration: {self.total_duration:.1f}s")
        print()

        if total_collected > 0:
            print(f"Tests Collected: {total_collected}")
            print(f"Tests Passed: {total_passed}")
            if total_failed > 0:
                print(f"Tests Failed: {total_failed}")
            if total_skipped > 0:
                print(f"Tests Skipped: {total_skipped}")
            print()

        # Overall result
        overall_success = categories_passed == categories_run and total_failed == 0
        status = "✅ SUCCESS" if overall_success else "❌ FAILURE"
        print(f"Overall Result: {status}")

        if not overall_success:
            print("\nFailed Categories:")
            for category, result in self.test_results.items():
                if not result.get("passed") and not result.get("skipped"):
                    reason = "Timeout" if result.get("timed_out") else "Tests failed"
                    print(f"  - {category}: {reason}")

    def generate_report(self, output_file: Optional[Path] = None) -> Dict:
        """Generate detailed JSON report."""
        report = {
            "timestamp": time.time(),
            "duration": self.total_duration,
            "categories": self.test_results,
            "summary": {
                "total_categories": len(self.test_results),
                "passed_categories": sum(
                    1 for r in self.test_results.values() if r.get("passed", False)
                ),
                "failed_categories": sum(
                    1
                    for r in self.test_results.values()
                    if not r.get("passed", True) and not r.get("skipped", False)
                ),
                "skipped_categories": sum(
                    1 for r in self.test_results.values() if r.get("skipped", False)
                ),
                "total_tests": sum(r.get("tests_collected", 0) for r in self.test_results.values()),
                "passed_tests": sum(r.get("tests_passed", 0) for r in self.test_results.values()),
                "failed_tests": sum(r.get("tests_failed", 0) for r in self.test_results.values()),
                "skipped_tests": sum(r.get("tests_skipped", 0) for r in self.test_results.values()),
            },
        }

        if output_file:
            output_file.write_text(json.dumps(report, indent=2))
            print(f"\nDetailed report saved to: {output_file}")

        return report

    def check_requirements(self) -> bool:
        """Check if test requirements are met."""
        print("Checking test requirements...")

        # Check Python version
        if sys.version_info < (3, 7):
            print("❌ Python 3.7+ required")
            return False
        print("✅ Python version OK")

        # Check pytest installation
        try:
            subprocess.run(
                [sys.executable, "-m", "pytest", "--version"], capture_output=True, check=True
            )
            print("✅ pytest available")
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("❌ pytest not available - install with: pip install pytest")
            return False

        # Check test directory structure
        tests_dir = self.project_root / "tests"
        if not tests_dir.exists():
            print("❌ tests directory not found")
            return False
        print("✅ Test directory structure OK")

        # Check CLI directory
        cli_dir = self.project_root / "cli"
        if not cli_dir.exists():
            print("❌ CLI directory not found")
            return False
        print("✅ CLI directory OK")

        return True


def main():
    """Main entry point for test runner."""
    parser = argparse.ArgumentParser(
        description="Run WSL-Tmux-Nvim-Setup test suite",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_tests.py                    # Run all tests
  python run_tests.py --quick            # Run quick test suite
  python run_tests.py --category unit    # Run only unit tests
  python run_tests.py --no-slow          # Exclude slow tests
  python run_tests.py --report results.json  # Save detailed report
        """,
    )

    parser.add_argument(
        "--quick",
        "-q",
        action="store_true",
        help="Run quick test suite (skip optional categories and slow tests)",
    )

    parser.add_argument(
        "--category",
        "-c",
        choices=["unit", "integration", "e2e", "performance", "security"],
        help="Run only specific test category",
    )

    parser.add_argument("--no-slow", action="store_true", help="Exclude slow tests")

    parser.add_argument("--report", "-r", type=Path, help="Save detailed JSON report to file")

    parser.add_argument(
        "--check-requirements", action="store_true", help="Check test requirements and exit"
    )

    args = parser.parse_args()

    # Find project root
    project_root = Path(__file__).parent
    runner = TestRunner(project_root)

    # Check requirements if requested
    if args.check_requirements:
        success = runner.check_requirements()
        sys.exit(0 if success else 1)

    # Check requirements before running tests
    if not runner.check_requirements():
        print("\n❌ Requirements check failed. Use --check-requirements for details.")
        sys.exit(1)

    print("\n🚀 Starting WSL-Tmux-Nvim-Setup Test Suite")
    print(f"Project: {project_root}")

    try:
        if args.category:
            # Run specific category
            print(f"Running {args.category} tests only...")

            # Determine markers
            markers = [args.category]
            if args.no_slow:
                markers.append("not slow")

            # Set timeout based on category
            timeouts = {
                "unit": 180,
                "integration": 300,
                "e2e": 600,
                "performance": 900,
                "security": 180,
            }

            result = runner.run_test_category(
                args.category, markers, timeouts.get(args.category, 300)
            )

            runner._print_category_results(result)
            success = result.get("passed", False)

        else:
            # Run all tests
            include_slow = not args.no_slow
            runner.run_all_tests(quick=args.quick, include_slow=include_slow)
            runner.print_summary()

            # Generate report if requested
            if args.report:
                runner.generate_report(args.report)

            # Determine overall success
            success = all(
                result.get("passed", False) or result.get("skipped", False)
                for result in runner.test_results.values()
            )

        # Exit with appropriate code
        sys.exit(0 if success else 1)

    except KeyboardInterrupt:
        print("\n\n⚠️  Test run interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
