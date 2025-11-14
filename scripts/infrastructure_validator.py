#!/usr/bin/env python3
"""
Infrastructure Validator

Pre-deployment validation to ensure all prerequisites are met.
Checks AWS credentials, Terraform installation, Docker, and resource availability.

Supports both SDK-based (S3Vector) and REST API-based (Qdrant, LanceDB) backends.

Usage:
    python scripts/infrastructure_validator.py
    python scripts/infrastructure_validator.py --backend s3vector
    python scripts/infrastructure_validator.py --backend qdrant
    python scripts/infrastructure_validator.py --comprehensive
"""

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import json

# Add project root to path for backend adapters
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.backend_adapters import validate_backend_connectivity, BACKEND_TYPES


class InfrastructureValidator:
    """Validates infrastructure prerequisites"""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.checks_passed = 0
        self.checks_failed = 0
        self.warnings = []
        self.project_root = Path(__file__).parent.parent
    
    def log(self, message: str, level: str = "INFO"):
        """Log message with level"""
        prefix = {
            "INFO": "ℹ",
            "SUCCESS": "✓",
            "ERROR": "✗",
            "WARNING": "⚠"
        }.get(level, "•")
        print(f"{prefix} {message}")
    
    def run_command(self, cmd: List[str], check: bool = False) -> Tuple[int, str, str]:
        """Run command and return exit code, stdout, stderr"""
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=check
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.CalledProcessError as e:
            return e.returncode, e.stdout, e.stderr
        except FileNotFoundError:
            return 127, "", f"Command not found: {cmd[0]}"
    
    def check_command_exists(self, command: str, min_version: Optional[str] = None) -> bool:
        """Check if a command exists and optionally verify version"""
        code, stdout, stderr = self.run_command([command, "--version"])
        
        if code != 0:
            self.log(f"{command} not found", "ERROR")
            self.checks_failed += 1
            return False
        
        if self.verbose:
            self.log(f"{command} found: {stdout.split()[0] if stdout else 'installed'}", "SUCCESS")
        else:
            self.log(f"{command} installed", "SUCCESS")
        
        self.checks_passed += 1
        return True
    
    def check_aws_credentials(self) -> bool:
        """Verify AWS credentials are configured"""
        self.log("Checking AWS credentials...", "INFO")
        
        code, stdout, stderr = self.run_command(
            ["aws", "sts", "get-caller-identity"]
        )
        
        if code != 0:
            self.log("AWS credentials not configured or invalid", "ERROR")
            self.log(f"Error: {stderr}", "ERROR")
            self.checks_failed += 1
            return False
        
        try:
            identity = json.loads(stdout)
            account_id = identity.get("Account", "unknown")
            user_arn = identity.get("Arn", "unknown")
            
            self.log(f"AWS credentials valid", "SUCCESS")
            if self.verbose:
                self.log(f"  Account: {account_id}", "INFO")
                self.log(f"  Identity: {user_arn}", "INFO")
            
            self.checks_passed += 1
            return True
        except json.JSONDecodeError:
            self.log("Failed to parse AWS identity", "ERROR")
            self.checks_failed += 1
            return False
    
    def check_aws_region(self) -> bool:
        """Verify AWS region is configured"""
        self.log("Checking AWS region...", "INFO")
        
        code, stdout, stderr = self.run_command(
            ["aws", "configure", "get", "region"]
        )
        
        if code != 0 or not stdout.strip():
            self.log("AWS region not configured", "WARNING")
            self.warnings.append("AWS_DEFAULT_REGION not set, will use us-east-1")
            return True
        
        region = stdout.strip()
        self.log(f"AWS region: {region}", "SUCCESS")
        self.checks_passed += 1
        return True
    
    def check_terraform_version(self) -> bool:
        """Check Terraform version"""
        self.log("Checking Terraform...", "INFO")
        return self.check_command_exists("terraform")
    
    def check_docker(self) -> bool:
        """Check Docker installation and daemon"""
        self.log("Checking Docker...", "INFO")
        
        if not self.check_command_exists("docker"):
            return False
        
        # Check if Docker daemon is running
        code, stdout, stderr = self.run_command(["docker", "ps"])
        
        if code != 0:
            self.log("Docker daemon not running", "ERROR")
            self.log("Start Docker: sudo systemctl start docker", "INFO")
            self.checks_failed += 1
            return False
        
        self.log("Docker daemon running", "SUCCESS")
        self.checks_passed += 1
        return True
    
    def check_python_version(self) -> bool:
        """Check Python version"""
        self.log("Checking Python...", "INFO")
        
        version = sys.version_info
        if version.major >= 3 and version.minor >= 8:
            self.log(f"Python {version.major}.{version.minor} installed", "SUCCESS")
            self.checks_passed += 1
            return True
        else:
            self.log(f"Python {version.major}.{version.minor} found, but 3.8+ required", "ERROR")
            self.checks_failed += 1
            return False
    
    def check_terraform_state(self, backend: Optional[str] = None) -> bool:
        """Check Terraform state for backend"""
        if not backend:
            return True
        
        self.log(f"Checking Terraform state for {backend}...", "INFO")
        
        terraform_dir = self.project_root / f"terraform/backends/{backend}"
        if not terraform_dir.exists():
            self.log(f"Terraform directory not found: {terraform_dir}", "ERROR")
            self.checks_failed += 1
            return False
        
        # Check if terraform is initialized
        if not (terraform_dir / ".terraform").exists():
            self.log(f"Terraform not initialized for {backend}", "WARNING")
            self.warnings.append(f"Run: cd {terraform_dir} && terraform init")
            return True
        
        self.log(f"Terraform initialized for {backend}", "SUCCESS")
        self.checks_passed += 1
        return True
    
    def check_disk_space(self) -> bool:
        """Check available disk space"""
        self.log("Checking disk space...", "INFO")
        
        code, stdout, stderr = self.run_command(["df", "-h", "."])
        
        if code != 0:
            self.log("Could not check disk space", "WARNING")
            return True
        
        # Parse df output (simplified)
        lines = stdout.strip().split('\n')
        if len(lines) >= 2:
            parts = lines[1].split()
            if len(parts) >= 5:
                avail = parts[3]
                self.log(f"Available disk space: {avail}", "SUCCESS")
                self.checks_passed += 1
                return True
        
        return True
    
    def check_network_connectivity(self) -> bool:
        """Check network connectivity to AWS"""
        self.log("Checking AWS connectivity...", "INFO")
        
        code, stdout, stderr = self.run_command(
            ["aws", "s3", "ls", "--max-items", "1"]
        )
        
        if code != 0:
            self.log("Cannot connect to AWS S3", "WARNING")
            self.warnings.append("Check network connectivity and AWS credentials")
            return True
        
        self.log("AWS connectivity OK", "SUCCESS")
        self.checks_passed += 1
        return True
    
    def check_required_ports(self) -> bool:
        """Check if required ports are available"""
        self.log("Checking port availability...", "INFO")
        
        import socket
        
        ports_to_check = [8000, 8080, 3000]  # API, alternative API, frontend
        blocked_ports = []
        
        for port in ports_to_check:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('localhost', port))
            sock.close()
            
            if result == 0:
                blocked_ports.append(port)
        
        if blocked_ports:
            self.log(f"Ports in use: {', '.join(map(str, blocked_ports))}", "WARNING")
            self.warnings.append(f"Ports {blocked_ports} are in use, may need to stop services")
        else:
            self.log("Required ports available", "SUCCESS")
            self.checks_passed += 1
        
        return True
    
    def check_iam_permissions(self) -> bool:
        """Check basic IAM permissions"""
        self.log("Checking IAM permissions...", "INFO")
        
        required_services = ["s3", "ec2", "ecs", "ecr", "iam"]
        
        for service in required_services:
            # Try a read-only operation
            if service == "s3":
                cmd = ["aws", "s3", "ls", "--max-items", "1"]
            elif service == "ec2":
                cmd = ["aws", "ec2", "describe-regions", "--max-results", "1"]
            elif service == "ecs":
                cmd = ["aws", "ecs", "list-clusters", "--max-results", "1"]
            elif service == "ecr":
                cmd = ["aws", "ecr", "describe-repositories", "--max-results", "1"]
            elif service == "iam":
                cmd = ["aws", "iam", "get-user"]
            else:
                continue
            
            code, stdout, stderr = self.run_command(cmd)
            
            if code != 0 and "AccessDenied" in stderr:
                self.log(f"Insufficient permissions for {service.upper()}", "WARNING")
                self.warnings.append(f"May need {service.upper()} permissions for full deployment")
        
        self.log("IAM permissions check complete", "SUCCESS")
        self.checks_passed += 1
        return True
    
    def check_backend_connectivity(self, backend: str) -> bool:
        """Check connectivity to a specific backend using unified validation"""
        self.log(f"Checking {backend} connectivity...", "INFO")
        
        try:
            backend_type = BACKEND_TYPES.get(backend.lower())
            if not backend_type:
                self.log(f"Unknown backend type: {backend}", "ERROR")
                self.checks_failed += 1
                return False
            
            # Use unified backend validation
            validation = validate_backend_connectivity(backend)
            
            if validation.get("accessible", False):
                endpoint_info = validation.get("endpoint_info", {})
                response_time = validation.get("response_time_ms", 0)
                
                self.log(f"{backend} is accessible", "SUCCESS")
                if self.verbose:
                    self.log(f"  Type: {endpoint_info.get('type', 'unknown')}", "INFO")
                    self.log(f"  Endpoint: {endpoint_info.get('endpoint', 'N/A')}", "INFO")
                    self.log(f"  Response time: {response_time:.2f}ms", "INFO")
                
                self.checks_passed += 1
                return True
            else:
                error = validation.get("error", "Not accessible")
                self.log(f"{backend} is NOT accessible: {error}", "ERROR")
                self.checks_failed += 1
                return False
                
        except Exception as e:
            self.log(f"Backend connectivity check failed: {e}", "ERROR")
            self.checks_failed += 1
            return False
    
    def check_s3vector_connectivity(self) -> bool:
        """Validate S3Vector connectivity via AWS SDK"""
        self.log("Checking S3Vector connectivity...", "INFO")
        
        try:
            from src.services.vector_store_s3vector_provider import S3VectorProvider
            
            provider = S3VectorProvider()
            result = provider.validate_connectivity()
            
            if result.get('accessible', False):
                response_time = result.get('response_time_ms', 0)
                self.log(f"S3Vector is accessible", "SUCCESS")
                if self.verbose:
                    self.log(f"  Endpoint: {result.get('endpoint', 'N/A')}", "INFO")
                    self.log(f"  Response time: {response_time:.2f}ms", "INFO")
                    self.log(f"  Region: {result.get('details', {}).get('region', 'N/A')}", "INFO")
                
                self.checks_passed += 1
                return True
            else:
                error = result.get('error_message', 'Not accessible')
                self.log(f"S3Vector is NOT accessible: {error}", "ERROR")
                self.checks_failed += 1
                return False
                
        except ImportError as e:
            self.log(f"S3Vector provider not available: {e}", "WARNING")
            self.warnings.append("S3Vector provider requires project dependencies")
            return True
        except Exception as e:
            self.log(f"S3Vector connectivity check failed: {e}", "ERROR")
            self.checks_failed += 1
            return False
    
    def check_qdrant_connectivity(self) -> bool:
        """Validate Qdrant connectivity via REST API"""
        self.log("Checking Qdrant connectivity...", "INFO")
        
        try:
            import requests
            
            # Qdrant health check at root path
            endpoint = "http://98.93.105.87:6333"
            response = requests.get(f"{endpoint}/", timeout=5)
            
            if response.status_code == 200:
                self.log(f"Qdrant is accessible at {endpoint}", "SUCCESS")
                if self.verbose:
                    self.log(f"  Status: {response.status_code}", "INFO")
                
                self.checks_passed += 1
                return True
            else:
                self.log(f"Qdrant returned HTTP {response.status_code}", "ERROR")
                self.checks_failed += 1
                return False
                
        except ImportError:
            self.log("requests library not available", "WARNING")
            self.warnings.append("Install requests: pip install requests")
            return True
        except Exception as e:
            self.log(f"Qdrant connectivity check failed: {e}", "ERROR")
            self.checks_failed += 1
            return False
    
    def check_lancedb_connectivity(self) -> bool:
        """Validate LanceDB connectivity via REST API"""
        self.log("Checking LanceDB connectivity...", "INFO")
        
        try:
            import requests
            
            # LanceDB health check
            endpoint = "http://18.234.151.118:8000"  # Updated endpoint
            response = requests.get(f"{endpoint}/health", timeout=5)
            
            if response.status_code == 200:
                self.log(f"LanceDB is accessible at {endpoint}", "SUCCESS")
                if self.verbose:
                    self.log(f"  Status: {response.status_code}", "INFO")
                
                self.checks_passed += 1
                return True
            else:
                self.log(f"LanceDB returned HTTP {response.status_code}", "ERROR")
                self.checks_failed += 1
                return False
                
        except ImportError:
            self.log("requests library not available", "WARNING")
            self.warnings.append("Install requests: pip install requests")
            return True
        except Exception as e:
            self.log(f"LanceDB connectivity check failed: {e}", "ERROR")
            self.checks_failed += 1
            return False
    
    def validate_all(self, backend: Optional[str] = None, comprehensive: bool = False) -> bool:
        """Run all validation checks"""
        self.log("=" * 60, "INFO")
        self.log("Infrastructure Pre-Deployment Validation", "INFO")
        self.log("=" * 60, "INFO")
        
        # Core checks
        self.check_python_version()
        self.check_terraform_version()
        self.check_aws_credentials()
        self.check_aws_region()
        
        # Docker check (only if LanceDB backend selected)
        if backend and "lancedb" in backend.lower():
            self.check_docker()
        
        # Backend-specific connectivity checks
        if backend:
            backend_lower = backend.lower()
            
            # Check backend connectivity using unified validation
            if backend_lower in ['s3vector', 's3_vector']:
                self.check_s3vector_connectivity()
            elif 'qdrant' in backend_lower:
                self.check_qdrant_connectivity()
            elif 'lancedb' in backend_lower:
                self.check_lancedb_connectivity()
            else:
                # Try unified backend validation for other backends
                self.check_backend_connectivity(backend)
            
            # Check terraform state
            self.check_terraform_state(backend)
        
        # Comprehensive checks
        if comprehensive:
            self.check_network_connectivity()
            self.check_disk_space()
            self.check_required_ports()
            self.check_iam_permissions()
            
            # Check all known backends if comprehensive
            self.log("\nChecking all backend connectivity...", "INFO")
            for backend_name in ['s3vector', 'qdrant', 'lancedb']:
                try:
                    self.check_backend_connectivity(backend_name)
                except Exception as e:
                    self.log(f"Could not check {backend_name}: {e}", "WARNING")
        
        # Summary
        self.log("=" * 60, "INFO")
        self.log(f"Validation complete: {self.checks_passed} passed, {self.checks_failed} failed", 
                "SUCCESS" if self.checks_failed == 0 else "ERROR")
        
        if self.warnings:
            self.log(f"Warnings: {len(self.warnings)}", "WARNING")
            for warning in self.warnings:
                self.log(f"  • {warning}", "WARNING")
        
        return self.checks_failed == 0


def main():
    """Main validation entry point"""
    parser = argparse.ArgumentParser(
        description="Validate infrastructure prerequisites for deployment"
    )
    
    parser.add_argument(
        "--backend",
        help="Specific backend to validate (e.g., s3vector, lancedb-s3)"
    )
    parser.add_argument(
        "--comprehensive",
        action="store_true",
        help="Run comprehensive validation including network and IAM checks"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    
    args = parser.parse_args()
    
    validator = InfrastructureValidator(verbose=args.verbose)
    
    success = validator.validate_all(
        backend=args.backend,
        comprehensive=args.comprehensive
    )
    
    if success:
        print("\n✓ All validation checks passed! Ready for deployment.")
        return 0
    else:
        print("\n✗ Validation failed. Please address the errors above before deployment.")
        return 1


if __name__ == "__main__":
    sys.exit(main())