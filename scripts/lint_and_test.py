#!/usr/bin/env python3
"""
Automated Linting and Testing Script
Runs all code quality checks and tests before deployment
"""

import argparse
import logging
import os
import subprocess
import sys
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class LintAndTestRunner:
    """Runs linting and testing checks"""

    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.failed_checks = []

    def run_command(self, command: list, description: str) -> bool:
        """Run a command and return success status"""
        logger.info(f"Running: {description}")
        logger.info(f"Command: {' '.join(command)}")

        try:
            result = subprocess.run(
                command,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True,
            )
            logger.info(f"✅ {description} - PASSED")
            if result.stdout:
                logger.debug(f"Output: {result.stdout}")
            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"❌ {description} - FAILED")
            logger.error(f"Error: {e.stderr}")
            if e.stdout:
                logger.error(f"Output: {e.stdout}")
            self.failed_checks.append(description)
            return False

    def check_python_syntax(self) -> bool:
        """Check Python syntax"""
        python_files = list(self.project_root.glob("**/*.py"))
        python_files = [
            f for f in python_files if "venv" not in str(f) and ".venv" not in str(f)
        ]

        for py_file in python_files:
            result = subprocess.run(
                [sys.executable, "-m", "py_compile", str(py_file)],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                logger.error(f"❌ Syntax error in {py_file}: {result.stderr}")
                self.failed_checks.append(f"Syntax check - {py_file}")
                return False

        logger.info("✅ Python syntax check - PASSED")
        return True

    def run_black_check(self) -> bool:
        """Run Black code formatter check"""
        return self.run_command(
            [
                "black",
                "--check",
                "--diff",
                "src/",
                "tests/",
                "outbound.py",
                "gmail_email_system.py",
                "weekly_scheduler.py",
            ],
            "Black code formatting check",
        )

    def run_isort_check(self) -> bool:
        """Run isort import sorting check"""
        return self.run_command(
            [
                "isort",
                "--check-only",
                "--diff",
                "src/",
                "tests/",
                "outbound.py",
                "gmail_email_system.py",
                "weekly_scheduler.py",
            ],
            "isort import sorting check",
        )

    def run_flake8(self) -> bool:
        """Run flake8 linting"""
        return self.run_command(
            [
                "flake8",
                "src/",
                "tests/",
                "outbound.py",
                "gmail_email_system.py",
                "weekly_scheduler.py",
            ],
            "Flake8 linting",
        )

    def run_mypy(self) -> bool:
        """Run mypy type checking"""
        return self.run_command(
            [
                "mypy",
                "src/",
                "outbound.py",
                "gmail_email_system.py",
                "weekly_scheduler.py",
            ],
            "MyPy type checking",
        )

    def run_bandit(self) -> bool:
        """Run bandit security linting"""
        return self.run_command(
            [
                "bandit",
                "-r",
                "src/",
                "outbound.py",
                "gmail_email_system.py",
                "weekly_scheduler.py",
            ],
            "Bandit security linting",
        )

    def run_safety(self) -> bool:
        """Run safety dependency check"""
        return self.run_command(["safety", "check"], "Safety dependency check")

    def run_tests(self) -> bool:
        """Run pytest tests"""
        return self.run_command(
            ["python", "-m", "pytest", "tests/", "-v", "--tb=short"], "Unit tests"
        )

    def run_integration_tests(self) -> bool:
        """Run integration tests"""
        return self.run_command(
            [
                "python",
                "-m",
                "pytest",
                "tests/",
                "-v",
                "--tb=short",
                "-m",
                "integration",
            ],
            "Integration tests",
        )

    def fix_formatting(self) -> bool:
        """Fix code formatting issues"""
        logger.info("🔧 Fixing code formatting...")

        # Run Black
        black_result = self.run_command(
            [
                "black",
                "src/",
                "tests/",
                "outbound.py",
                "gmail_email_system.py",
                "weekly_scheduler.py",
            ],
            "Black code formatting",
        )

        # Run isort
        isort_result = self.run_command(
            [
                "isort",
                "src/",
                "tests/",
                "outbound.py",
                "gmail_email_system.py",
                "weekly_scheduler.py",
            ],
            "isort import sorting",
        )

        return black_result and isort_result

    def run_all_checks(self, fix_formatting: bool = False) -> bool:
        """Run all linting and testing checks"""
        logger.info("🚀 Starting code quality checks...")

        if fix_formatting:
            self.fix_formatting()

        # Run all checks
        checks = [
            self.check_python_syntax,
            self.run_black_check,
            self.run_isort_check,
            self.run_flake8,
            self.run_mypy,
            self.run_bandit,
            self.run_safety,
            self.run_tests,
        ]

        all_passed = True
        for check in checks:
            if not check():
                all_passed = False

        # Summary
        if all_passed:
            logger.info("🎉 All checks passed!")
        else:
            logger.error(f"❌ {len(self.failed_checks)} checks failed:")
            for check in self.failed_checks:
                logger.error(f"  - {check}")

        return all_passed


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Run linting and testing checks")
    parser.add_argument(
        "--fix", action="store_true", help="Fix formatting issues automatically"
    )
    parser.add_argument("--skip-tests", action="store_true", help="Skip running tests")
    parser.add_argument("--only-tests", action="store_true", help="Only run tests")
    parser.add_argument("--project-root", default=".", help="Project root directory")

    args = parser.parse_args()

    runner = LintAndTestRunner(args.project_root)

    if args.only_tests:
        success = runner.run_tests()
    elif args.skip_tests:
        # Run all checks except tests
        checks = [
            runner.check_python_syntax,
            runner.run_black_check,
            runner.run_isort_check,
            runner.run_flake8,
            runner.run_mypy,
            runner.run_bandit,
            runner.run_safety,
        ]
        success = all(check() for check in checks)
    else:
        success = runner.run_all_checks(fix_formatting=args.fix)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
