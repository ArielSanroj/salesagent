#!/usr/bin/env python3
"""
Secure Deployment Script for HR Tech Lead Generation System
Handles deployment with security checks, testing, and configuration validation
"""

import subprocess
import sys
import os
import shutil
import logging
from pathlib import Path
import argparse
import json
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SecureDeployment:
    """Handles secure deployment of the HR Tech Lead Generation System"""
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.backup_dir = self.project_root / "backups" / datetime.now().strftime("%Y%m%d_%H%M%S")
        self.deployment_log = []
        
    def log_step(self, step: str, success: bool, message: str = ""):
        """Log deployment step"""
        status = "✅" if success else "❌"
        log_entry = {
            "step": step,
            "success": success,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
        self.deployment_log.append(log_entry)
        
        if success:
            logger.info(f"{status} {step}: {message}")
        else:
            logger.error(f"{status} {step}: {message}")
    
    def create_backup(self) -> bool:
        """Create backup of current system"""
        try:
            logger.info("Creating backup of current system...")
            
            # Create backup directory
            self.backup_dir.mkdir(parents=True, exist_ok=True)
            
            # Files to backup
            files_to_backup = [
                "outbound.py",
                "gmail_email_system.py", 
                "weekly_scheduler.py",
                "production_config.json",
                ".env"
            ]
            
            for file_name in files_to_backup:
                file_path = self.project_root / file_name
                if file_path.exists():
                    shutil.copy2(file_path, self.backup_dir / file_name)
            
            self.log_step("Backup Creation", True, f"Backup created at {self.backup_dir}")
            return True
            
        except Exception as e:
            self.log_step("Backup Creation", False, str(e))
            return False
    
    def validate_environment(self) -> bool:
        """Validate environment and dependencies"""
        try:
            logger.info("Validating environment...")
            
            # Check Python version
            if sys.version_info < (3, 8):
                raise ValueError("Python 3.8+ required")
            
            # Check required files
            required_files = [
                "config/secure_config.yaml",
                "config/email_templates.yaml",
                "src/credentials_manager.py",
                "src/llm_service.py",
                "outbound_secure.py",
                "gmail_email_system_secure.py"
            ]
            
            for file_path in required_files:
                if not (self.project_root / file_path).exists():
                    raise FileNotFoundError(f"Required file not found: {file_path}")
            
            # Check .env file
            env_file = self.project_root / ".env"
            if not env_file.exists():
                raise FileNotFoundError(".env file not found. Please create it with required environment variables.")
            
            # Validate .env content
            with open(env_file, 'r') as f:
                env_content = f.read()
                required_vars = ["NVIDIA_API_KEY", "EMAIL_PASSWORD"]
                for var in required_vars:
                    if f"{var}=" not in env_content or f"{var}=your_" in env_content:
                        raise ValueError(f"Environment variable {var} not properly configured")
            
            self.log_step("Environment Validation", True, "Environment validated successfully")
            return True
            
        except Exception as e:
            self.log_step("Environment Validation", False, str(e))
            return False
    
    def run_security_checks(self) -> bool:
        """Run security checks"""
        try:
            logger.info("Running security checks...")
            
            # Run bandit security linter
            result = subprocess.run([
                sys.executable, "-m", "bandit", 
                "-r", "src/", 
                "outbound_secure.py", 
                "gmail_email_system_secure.py",
                "-f", "json"
            ], capture_output=True, text=True, cwd=self.project_root)
            
            if result.returncode != 0:
                # Parse bandit output
                try:
                    bandit_results = json.loads(result.stdout)
                    high_severity = [issue for issue in bandit_results.get("results", []) 
                                   if issue.get("issue_severity") == "HIGH"]
                    if high_severity:
                        raise ValueError(f"High severity security issues found: {len(high_severity)}")
                except json.JSONDecodeError:
                    pass
            
            # Check for hardcoded secrets
            secret_patterns = [
                "password.*=.*[\"'][^\"']+[\"']",
                "api_key.*=.*[\"'][^\"']+[\"']",
                "secret.*=.*[\"'][^\"']+[\"']"
            ]
            
            files_to_check = [
                "outbound_secure.py",
                "gmail_email_system_secure.py",
                "src/credentials_manager.py",
                "src/llm_service.py"
            ]
            
            for file_path in files_to_check:
                full_path = self.project_root / file_path
                if full_path.exists():
                    with open(full_path, 'r') as f:
                        content = f.read()
                        for pattern in secret_patterns:
                            import re
                            if re.search(pattern, content, re.IGNORECASE):
                                raise ValueError(f"Potential hardcoded secret found in {file_path}")
            
            self.log_step("Security Checks", True, "Security checks passed")
            return True
            
        except Exception as e:
            self.log_step("Security Checks", False, str(e))
            return False
    
    def run_tests(self) -> bool:
        """Run comprehensive test suite"""
        try:
            logger.info("Running test suite...")
            
            # Run linting and tests
            result = subprocess.run([
                sys.executable, "scripts/lint_and_test.py", "--project-root", str(self.project_root)
            ], capture_output=True, text=True, cwd=self.project_root)
            
            if result.returncode != 0:
                raise ValueError(f"Tests failed: {result.stderr}")
            
            self.log_step("Test Suite", True, "All tests passed")
            return True
            
        except Exception as e:
            self.log_step("Test Suite", False, str(e))
            return False
    
    def deploy_files(self) -> bool:
        """Deploy new files"""
        try:
            logger.info("Deploying new files...")
            
            # Replace main files
            file_mappings = {
                "outbound_secure.py": "outbound.py",
                "gmail_email_system_secure.py": "gmail_email_system.py"
            }
            
            for source, target in file_mappings.items():
                source_path = self.project_root / source
                target_path = self.project_root / target
                
                if source_path.exists():
                    shutil.copy2(source_path, target_path)
                    logger.info(f"Deployed {source} -> {target}")
            
            # Ensure config directory exists
            config_dir = self.project_root / "config"
            config_dir.mkdir(exist_ok=True)
            
            # Ensure src directory exists
            src_dir = self.project_root / "src"
            src_dir.mkdir(exist_ok=True)
            
            self.log_step("File Deployment", True, "Files deployed successfully")
            return True
            
        except Exception as e:
            self.log_step("File Deployment", False, str(e))
            return False
    
    def update_dependencies(self) -> bool:
        """Update Python dependencies"""
        try:
            logger.info("Updating dependencies...")
            
            # Install/update requirements
            result = subprocess.run([
                sys.executable, "-m", "pip", "install", "-r", "requirements.txt", "--upgrade"
            ], capture_output=True, text=True, cwd=self.project_root)
            
            if result.returncode != 0:
                raise ValueError(f"Failed to install dependencies: {result.stderr}")
            
            self.log_step("Dependencies Update", True, "Dependencies updated successfully")
            return True
            
        except Exception as e:
            self.log_step("Dependencies Update", False, str(e))
            return False
    
    def validate_deployment(self) -> bool:
        """Validate deployment"""
        try:
            logger.info("Validating deployment...")
            
            # Test import of main modules
            test_script = """
import sys
sys.path.insert(0, 'src')

try:
    from credentials_manager import CredentialsManager
    from llm_service import LLMService
    print("✅ Core modules import successfully")
    
    # Test credentials manager
    cm = CredentialsManager()
    if cm.validate_required_credentials():
        print("✅ Credentials validation passed")
    else:
        print("❌ Credentials validation failed")
        sys.exit(1)
        
    print("✅ Deployment validation successful")
    
except Exception as e:
    print(f"❌ Deployment validation failed: {e}")
    sys.exit(1)
"""
            
            with open("temp_validation.py", "w") as f:
                f.write(test_script)
            
            result = subprocess.run([
                sys.executable, "temp_validation.py"
            ], capture_output=True, text=True, cwd=self.project_root)
            
            # Clean up
            (self.project_root / "temp_validation.py").unlink(missing_ok=True)
            
            if result.returncode != 0:
                raise ValueError(f"Deployment validation failed: {result.stderr}")
            
            self.log_step("Deployment Validation", True, "Deployment validated successfully")
            return True
            
        except Exception as e:
            self.log_step("Deployment Validation", False, str(e))
            return False
    
    def create_deployment_report(self) -> bool:
        """Create deployment report"""
        try:
            logger.info("Creating deployment report...")
            
            report = {
                "deployment_timestamp": datetime.now().isoformat(),
                "project_root": str(self.project_root),
                "backup_location": str(self.backup_dir),
                "steps": self.deployment_log,
                "overall_success": all(step["success"] for step in self.deployment_log)
            }
            
            report_file = self.project_root / f"deployment_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2)
            
            self.log_step("Deployment Report", True, f"Report saved to {report_file}")
            return True
            
        except Exception as e:
            self.log_step("Deployment Report", False, str(e))
            return False
    
    def deploy(self, skip_tests: bool = False) -> bool:
        """Run complete deployment process"""
        logger.info("🚀 Starting secure deployment...")
        
        deployment_steps = [
            ("Backup Creation", self.create_backup),
            ("Environment Validation", self.validate_environment),
            ("Security Checks", self.run_security_checks),
            ("Test Suite", self.run_tests if not skip_tests else lambda: True),
            ("Dependencies Update", self.update_dependencies),
            ("File Deployment", self.deploy_files),
            ("Deployment Validation", self.validate_deployment),
            ("Deployment Report", self.create_deployment_report)
        ]
        
        all_success = True
        for step_name, step_func in deployment_steps:
            if not step_func():
                all_success = False
                if step_name in ["Environment Validation", "Security Checks"]:
                    logger.error(f"Critical step failed: {step_name}. Aborting deployment.")
                    break
        
        # Print summary
        logger.info("\n" + "="*50)
        logger.info("DEPLOYMENT SUMMARY")
        logger.info("="*50)
        
        for step in self.deployment_log:
            status = "✅" if step["success"] else "❌"
            logger.info(f"{status} {step['step']}: {step['message']}")
        
        if all_success:
            logger.info("🎉 Deployment completed successfully!")
        else:
            logger.error("❌ Deployment failed. Check the logs above for details.")
        
        return all_success

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Deploy HR Tech Lead Generation System securely")
    parser.add_argument("--skip-tests", action="store_true", help="Skip running tests during deployment")
    parser.add_argument("--project-root", default=".", help="Project root directory")
    
    args = parser.parse_args()
    
    deployment = SecureDeployment(args.project_root)
    success = deployment.deploy(skip_tests=args.skip_tests)
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()