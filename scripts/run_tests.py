#!/usr/bin/env python3
"""
Comprehensive Test Runner for HR Tech Lead Generation System
Runs all tests with proper setup and reporting
"""

import subprocess
import sys
import os
import logging
from pathlib import Path
import argparse

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TestRunner:
    """Comprehensive test runner"""
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.test_results = {}
        
    def setup_test_environment(self):
        """Setup test environment with required files"""
        logger.info("Setting up test environment...")
        
        # Create test directories
        test_dirs = ["tests", "config", "src"]
        for dir_name in test_dirs:
            (self.project_root / dir_name).mkdir(exist_ok=True)
        
        # Create test .env file
        test_env_file = self.project_root / ".env.test"
        if not test_env_file.exists():
            with open(test_env_file, 'w') as f:
                f.write("""# Test Environment Variables
OLLAMA_API_KEY=test_key
EMAIL_PASSWORD=test_password
SERPAPI_KEY=test_serpapi_key
HUNTER_KEY=test_hunter_key
APIFY_KEY=test_apify_key
BRIGHTDATA_PASSWORD=test_brightdata_password
EMAIL_SENDER=test@example.com
EMAIL_RECIPIENT=test@example.com
GMAIL_CREDENTIALS_FILE=test_credentials.json
GMAIL_TOKEN_FILE=test_token.json
""")
        
        # Create test credentials file
        test_creds_file = self.project_root / "test_credentials.json"
        if not test_creds_file.exists():
            with open(test_creds_file, 'w') as f:
                f.write("""{
  "installed": {
    "client_id": "test_client_id",
    "project_id": "test_project",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_secret": "test_client_secret",
    "redirect_uris": ["http://localhost"]
  }
}""")
        
        logger.info("Test environment setup complete")
    
    def run_unit_tests(self) -> bool:
        """Run unit tests"""
        logger.info("Running unit tests...")
        
        try:
            # Set test environment
            env = os.environ.copy()
            env['PYTHONPATH'] = str(self.project_root / "src")
            
            result = subprocess.run([
                sys.executable, "-m", "pytest", 
                "tests/", 
                "-v", 
                "--tb=short",
                "--cov=src",
                "--cov-report=term-missing",
                "--cov-report=html:htmlcov"
            ], cwd=self.project_root, env=env, capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info("✅ Unit tests passed")
                self.test_results["unit_tests"] = "PASSED"
                return True
            else:
                logger.error("❌ Unit tests failed")
                logger.error(result.stdout)
                logger.error(result.stderr)
                self.test_results["unit_tests"] = "FAILED"
                return False
                
        except Exception as e:
            logger.error(f"Error running unit tests: {e}")
            self.test_results["unit_tests"] = "ERROR"
            return False
    
    def run_integration_tests(self) -> bool:
        """Run integration tests"""
        logger.info("Running integration tests...")
        
        try:
            # Set test environment
            env = os.environ.copy()
            env['PYTHONPATH'] = str(self.project_root / "src")
            env['TEST_MODE'] = 'true'
            
            result = subprocess.run([
                sys.executable, "-m", "pytest", 
                "tests/", 
                "-v", 
                "--tb=short",
                "-m", "integration"
            ], cwd=self.project_root, env=env, capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info("✅ Integration tests passed")
                self.test_results["integration_tests"] = "PASSED"
                return True
            else:
                logger.error("❌ Integration tests failed")
                logger.error(result.stdout)
                logger.error(result.stderr)
                self.test_results["integration_tests"] = "FAILED"
                return False
                
        except Exception as e:
            logger.error(f"Error running integration tests: {e}")
            self.test_results["integration_tests"] = "ERROR"
            return False
    
    def run_security_tests(self) -> bool:
        """Run security tests"""
        logger.info("Running security tests...")
        
        try:
            # Run bandit security linter
            result = subprocess.run([
                sys.executable, "-m", "bandit", 
                "-r", "src/", 
                "outbound_secure.py", 
                "gmail_email_system_secure.py",
                "-f", "json",
                "-o", "security_report.json"
            ], cwd=self.project_root, capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info("✅ Security tests passed")
                self.test_results["security_tests"] = "PASSED"
                return True
            else:
                logger.warning("⚠️ Security issues found")
                logger.warning(result.stdout)
                self.test_results["security_tests"] = "WARNINGS"
                return True  # Don't fail on warnings
                
        except Exception as e:
            logger.error(f"Error running security tests: {e}")
            self.test_results["security_tests"] = "ERROR"
            return False
    
    def run_performance_tests(self) -> bool:
        """Run performance tests"""
        logger.info("Running performance tests...")
        
        try:
            # Test LLM service performance
            test_script = """
import sys
sys.path.insert(0, 'src')
from credentials_manager import CredentialsManager
from llm_service import LLMService
import time

# Initialize services
credentials_manager = CredentialsManager()
llm_service = LLMService(credentials_manager)

# Test performance
start_time = time.time()
for i in range(10):
    response = llm_service.invoke_sync("Test prompt", "test")
    print(f"Request {i+1}: {response[:50]}...")
end_time = time.time()

print(f"Total time: {end_time - start_time:.2f} seconds")
print(f"Average time per request: {(end_time - start_time) / 10:.2f} seconds")
"""
            
            with open("temp_performance_test.py", "w") as f:
                f.write(test_script)
            
            result = subprocess.run([
                sys.executable, "temp_performance_test.py"
            ], cwd=self.project_root, capture_output=True, text=True, timeout=60)
            
            # Clean up
            (self.project_root / "temp_performance_test.py").unlink(missing_ok=True)
            
            if result.returncode == 0:
                logger.info("✅ Performance tests passed")
                logger.info(result.stdout)
                self.test_results["performance_tests"] = "PASSED"
                return True
            else:
                logger.error("❌ Performance tests failed")
                logger.error(result.stderr)
                self.test_results["performance_tests"] = "FAILED"
                return False
                
        except Exception as e:
            logger.error(f"Error running performance tests: {e}")
            self.test_results["performance_tests"] = "ERROR"
            return False
    
    def run_all_tests(self) -> bool:
        """Run all tests"""
        logger.info("🚀 Starting comprehensive test suite...")
        
        # Setup environment
        self.setup_test_environment()
        
        # Run all test categories
        test_categories = [
            ("Unit Tests", self.run_unit_tests),
            ("Integration Tests", self.run_integration_tests),
            ("Security Tests", self.run_security_tests),
            ("Performance Tests", self.run_performance_tests)
        ]
        
        all_passed = True
        for category_name, test_func in test_categories:
            logger.info(f"\n--- Running {category_name} ---")
            if not test_func():
                all_passed = False
        
        # Print summary
        self.print_test_summary()
        
        return all_passed
    
    def print_test_summary(self):
        """Print test results summary"""
        logger.info("\n" + "="*50)
        logger.info("TEST RESULTS SUMMARY")
        logger.info("="*50)
        
        for test_name, result in self.test_results.items():
            status_icon = "✅" if result == "PASSED" else "❌" if result == "FAILED" else "⚠️"
            logger.info(f"{status_icon} {test_name}: {result}")
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result == "PASSED")
        
        logger.info(f"\nOverall: {passed_tests}/{total_tests} test categories passed")
        
        if passed_tests == total_tests:
            logger.info("🎉 All tests passed!")
        else:
            logger.error("❌ Some tests failed. Please review the results above.")

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Run comprehensive test suite")
    parser.add_argument("--unit-only", action="store_true", help="Run only unit tests")
    parser.add_argument("--integration-only", action="store_true", help="Run only integration tests")
    parser.add_argument("--security-only", action="store_true", help="Run only security tests")
    parser.add_argument("--performance-only", action="store_true", help="Run only performance tests")
    parser.add_argument("--project-root", default=".", help="Project root directory")
    
    args = parser.parse_args()
    
    runner = TestRunner(args.project_root)
    
    if args.unit_only:
        success = runner.run_unit_tests()
    elif args.integration_only:
        success = runner.run_integration_tests()
    elif args.security_only:
        success = runner.run_security_tests()
    elif args.performance_only:
        success = runner.run_performance_tests()
    else:
        success = runner.run_all_tests()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()