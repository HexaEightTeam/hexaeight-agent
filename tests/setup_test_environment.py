#!/usr/bin/env python3
"""
HexaEight Agent Environment Setup Helper

This script helps users set up and verify their HexaEight Agent environment:
- Check system requirements (.NET runtime, Python version)
- Verify HexaEight License installation and env-file
- Validate environment variables
- Test library imports and DLL loading
- Configure client credentials
- Test PubSub server connectivity

Usage:
    python setup_test_environment.py [--check-only] [--setup-credentials]
    
Examples:
    python setup_test_environment.py                    # Full setup and verification
    python setup_test_environment.py --check-only       # Only check current setup
    python setup_test_environment.py --setup-credentials # Setup credentials interactively
"""

import sys
import os
import platform
import subprocess
import json
from datetime import datetime
from typing import Dict, List, Tuple, Optional


class EnvironmentSetup:
    def __init__(self):
        self.checks_passed = 0
        self.checks_total = 0
        self.warnings = []
        self.errors = []
        
    def print_header(self, title: str):
        """Print a formatted header."""
        print(f"\n{'='*60}")
        print(f" {title}")
        print(f"{'='*60}")
    
    def print_check(self, description: str, passed: bool, details: str = ""):
        """Print a check result."""
        self.checks_total += 1
        if passed:
            self.checks_passed += 1
            icon = "✅"
        else:
            icon = "❌"
        
        print(f"{icon} {description}")
        if details:
            print(f"   {details}")
    
    def print_warning(self, message: str):
        """Print a warning message."""
        self.warnings.append(message)
        print(f"⚠️ Warning: {message}")
    
    def print_error(self, message: str):
        """Print an error message."""
        self.errors.append(message)
        print(f"❌ Error: {message}")
    
    def check_python_version(self):
        """Check Python version compatibility."""
        self.print_header("Python Environment Check")
        
        version = sys.version_info
        version_str = f"{version.major}.{version.minor}.{version.micro}"
        
        # Check Python version (3.8+)
        if version >= (3, 8):
            self.print_check(f"Python version {version_str}", True, "Compatible with hexaeight-agent")
        else:
            self.print_check(f"Python version {version_str}", False, "Requires Python 3.8 or higher")
        
        # Check platform
        platform_name = platform.system()
        architecture = platform.machine()
        self.print_check(f"Platform: {platform_name} {architecture}", True, "Platform information")
    
    def check_dotnet_runtime(self):
        """Check .NET runtime availability."""
        self.print_header(".NET Runtime Check")
        
        try:
            # Check if dotnet is available
            result = subprocess.run(['dotnet', '--version'], 
                                  capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                version = result.stdout.strip()
                self.print_check(f".NET version {version}", True, "Available in PATH")
                
                # Check if it's .NET 8.0+
                try:
                    major_version = int(version.split('.')[0])
                    if major_version >= 8:
                        self.print_check("Version compatibility", True, ".NET 8.0+ detected")
                    else:
                        self.print_check("Version compatibility", False, "Requires .NET 8.0 or higher")
                except:
                    self.print_warning("Could not parse .NET version number")
                
            else:
                self.print_check(".NET runtime", False, "dotnet command failed")
                self.print_error("Install .NET 8.0+ runtime: https://dotnet.microsoft.com/download")
                
        except FileNotFoundError:
            self.print_check(".NET runtime", False, "dotnet command not found")
            self.print_error("Install .NET 8.0+ runtime: https://dotnet.microsoft.com/download")
        except subprocess.TimeoutExpired:
            self.print_check(".NET runtime", False, "dotnet command timed out")
        except Exception as e:
            self.print_check(".NET runtime", False, f"Error: {e}")
    
    def check_hexaeight_license(self):
        """Check HexaEight License installation."""
        self.print_header("HexaEight License Check")
        
        # Check for env-file in current directory
        env_file_path = "env-file"
        if os.path.exists(env_file_path):
            self.print_check("env-file exists", True, f"Found at: {os.path.abspath(env_file_path)}")
            
            # Try to read and validate env-file
            try:
                with open(env_file_path, 'r') as f:
                    content = f.read()
                
                required_vars = [
                    "HEXAEIGHT_RESOURCENAME",
                    "HEXAEIGHT_MACHINETOKEN", 
                    "HEXAEIGHT_SECRET",
                    "HEXAEIGHT_LICENSECODE"
                ]
                
                found_vars = []
                for var in required_vars:
                    if var in content:
                        found_vars.append(var)
                
                if len(found_vars) == len(required_vars):
                    self.print_check("env-file content", True, f"Contains all {len(required_vars)} required variables")
                else:
                    missing = set(required_vars) - set(found_vars)
                    self.print_check("env-file content", False, f"Missing: {', '.join(missing)}")
                
            except Exception as e:
                self.print_check("env-file readable", False, f"Error reading file: {e}")
        else:
            self.print_check("env-file exists", False, "Not found in current directory")
            self.print_error("HexaEight License must be installed to create env-file automatically")
    
    def check_library_imports(self):
        """Check hexaeight-agent library imports."""
        self.print_header("HexaEight Agent Library Check")
        
        # Check if hexaeight_agent can be imported
        try:
            import hexaeight_agent
            self.print_check("hexaeight_agent import", True, f"Version: {hexaeight_agent.__version__}")
            
            # Check availability flags
            if hexaeight_agent.DOTNET_AVAILABLE:
                self.print_check(".NET integration", True, "Python.NET working")
            else:
                self.print_check(".NET integration", False, "Python.NET not available")
            
            if hexaeight_agent.HEXAEIGHT_AGENT_AVAILABLE:
                self.print_check("HexaEight Agent DLLs", True, "All DLLs loaded successfully")
            else:
                self.print_check("HexaEight Agent DLLs", False, "DLL loading failed")
            
            # Try to create agent instance
            try:
                agent = hexaeight_agent.HexaEightAgent()
                self.print_check("Agent instantiation", True, "HexaEightAgent created successfully")
                agent.dispose()
            except Exception as e:
                self.print_check("Agent instantiation", False, f"Error: {e}")
                
        except ImportError as e:
            self.print_check("hexaeight_agent import", False, f"Import error: {e}")
            self.print_error("Install hexaeight-agent: pip install hexaeight-agent")
        except Exception as e:
            self.print_check("hexaeight_agent import", False, f"Unexpected error: {e}")
    
    def check_environment_variables(self):
        """Check environment variables setup."""
        self.print_header("Environment Variables Check")
        
        # Load environment from env-file first
        try:
            from hexaeight_agent import HexaEightEnvironmentManager
            env_vars = HexaEightEnvironmentManager.load_hexaeight_variables_from_env_file("env-file")
            self.print_check("Environment loading", True, f"Loaded {len(env_vars)} variables")
            
            # Check specific variables
            resource_name, machine_token, secret, license_code = (
                HexaEightEnvironmentManager.get_all_environment_variables()
            )
            
            variables = {
                "Resource Name": resource_name,
                "Machine Token": machine_token, 
                "Secret": secret,
                "License Code": license_code
            }
            
            for name, value in variables.items():
                if value:
                    self.print_check(f"{name}", True, f"Set (length: {len(value)})")
                else:
                    self.print_check(f"{name}", False, "Not set or empty")
            
            # Check client credentials
            client_id = os.environ.get("HEXAEIGHT_CLIENT_ID", "")
            token_server_url = os.environ.get("HEXAEIGHT_TOKENSERVER_URL", "")
            
            if client_id:
                self.print_check("Client ID", True, f"Set (length: {len(client_id)})")
            else:
                self.print_check("Client ID", False, "Not set (HEXAEIGHT_CLIENT_ID)")
                self.print_warning("Set HEXAEIGHT_CLIENT_ID environment variable")
            
            if token_server_url:
                self.print_check("Token Server URL", True, f"Set: {token_server_url}")
            else:
                self.print_check("Token Server URL", False, "Not set (HEXAEIGHT_TOKENSERVER_URL)")
                self.print_warning("Set HEXAEIGHT_TOKENSERVER_URL environment variable")
                
        except Exception as e:
            self.print_check("Environment loading", False, f"Error: {e}")
    
    def check_pubsub_connectivity(self, pubsub_url: str = "http://localhost:5000"):
        """Check PubSub server connectivity."""
        self.print_header("PubSub Server Connectivity Check")
        
        try:
            import requests
            
            # Test basic connectivity
            print(f"Testing connection to: {pubsub_url}")
            
            try:
                response = requests.get(f"{pubsub_url}/api/resourceinfo", timeout=10)
                
                if response.status_code == 200:
                    self.print_check("PubSub server reachable", True, f"Status: {response.status_code}")
                    
                    # Try to parse server info
                    try:
                        server_info = response.json()
                        server_name = server_info.get("agentName", "Unknown")
                        features = server_info.get("features", [])
                        
                        self.print_check("Server information", True, f"Server: {server_name}")
                        print(f"   Features: {', '.join(features[:3])}{'...' if len(features) > 3 else ''}")
                        
                    except Exception as e:
                        self.print_warning(f"Could not parse server info: {e}")
                        
                else:
                    self.print_check("PubSub server reachable", False, f"HTTP {response.status_code}")
                    
            except requests.exceptions.ConnectTimeout:
                self.print_check("PubSub server reachable", False, "Connection timeout")
            except requests.exceptions.ConnectionError:
                self.print_check("PubSub server reachable", False, "Connection refused")
            except Exception as e:
                self.print_check("PubSub server reachable", False, f"Error: {e}")
                
        except ImportError:
            self.print_warning("requests library not available for connectivity test")
            print("   Install with: pip install requests")
    
    def setup_credentials_interactive(self):
        """Interactively setup credentials."""
        self.print_header("Interactive Credentials Setup")
        
        print("This will help you set up HexaEight client credentials.")
        print("You can obtain these from your HexaEight provider.\n")
        
        client_id = input("Enter HEXAEIGHT_CLIENT_ID: ").strip()
        token_server_url = input("Enter HEXAEIGHT_TOKENSERVER_URL: ").strip()
        pubsub_url = input("Enter PubSub server URL (default: http://localhost:5000): ").strip()
        
        if not pubsub_url:
            pubsub_url = "http://localhost:5000"
        
        # Create a credentials file
        credentials = {
            "HEXAEIGHT_CLIENT_ID": client_id,
            "HEXAEIGHT_TOKENSERVER_URL": token_server_url,
            "HEXAEIGHT_PUBSUB_URL": pubsub_url,
            "created_at": datetime.utcnow().isoformat()
        }
        
        # Save to credentials.json
        try:
            with open("hexaeight_credentials.json", "w") as f:
                json.dump(credentials, f, indent=2)
            
            print(f"\n✅ Credentials saved to: hexaeight_credentials.json")
            print("Set these environment variables:")
            print(f"export HEXAEIGHT_CLIENT_ID='{client_id}'")
            print(f"export HEXAEIGHT_TOKENSERVER_URL='{token_server_url}'")
            print(f"export HEXAEIGHT_PUBSUB_URL='{pubsub_url}'")
            
            # Set in current environment
            os.environ["HEXAEIGHT_CLIENT_ID"] = client_id
            os.environ["HEXAEIGHT_TOKENSERVER_URL"] = token_server_url
            os.environ["HEXAEIGHT_PUBSUB_URL"] = pubsub_url
            
            print("\n✅ Environment variables set for current session")
            
        except Exception as e:
            self.print_error(f"Could not save credentials: {e}")
    
    def load_saved_credentials(self):
        """Load previously saved credentials."""
        try:
            if os.path.exists("hexaeight_credentials.json"):
                with open("hexaeight_credentials.json", "r") as f:
                    credentials = json.load(f)
                
                for key, value in credentials.items():
                    if key.startswith("HEXAEIGHT_") and value:
                        os.environ[key] = value
                
                print("✅ Loaded saved credentials from hexaeight_credentials.json")
                return True
        except Exception as e:
            self.print_warning(f"Could not load saved credentials: {e}")
        
        return False
    
    def run_comprehensive_check(self, check_pubsub: bool = True):
        """Run all environment checks."""
        print("🚀 HexaEight Agent Environment Setup")
        print(f"Starting comprehensive environment check at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Load any saved credentials
        self.load_saved_credentials()
        
        # Run all checks
        self.check_python_version()
        self.check_dotnet_runtime()
        self.check_hexaeight_license()
        self.check_library_imports()
        self.check_environment_variables()
        
        if check_pubsub:
            pubsub_url = os.environ.get("HEXAEIGHT_PUBSUB_URL", "http://localhost:5000")
            self.check_pubsub_connectivity(pubsub_url)
        
        # Summary
        self.print_summary()
    
    def print_summary(self):
        """Print setup summary."""
        self.print_header("Setup Summary")
        
        success_rate = (self.checks_passed / self.checks_total * 100) if self.checks_total > 0 else 0
        
        print(f"📊 Checks passed: {self.checks_passed}/{self.checks_total} ({success_rate:.1f}%)")
        
        if self.warnings:
            print(f"⚠️ Warnings: {len(self.warnings)}")
            for warning in self.warnings:
                print(f"   - {warning}")
        
        if self.errors:
            print(f"❌ Errors: {len(self.errors)}")
            for error in self.errors:
                print(f"   - {error}")
        
        if success_rate >= 80 and not self.errors:
            print("\n🎉 Environment setup looks good! You should be able to run HexaEight Agent demos.")
        elif success_rate >= 60:
            print("\n⚠️ Environment setup has some issues but might work. Check warnings above.")
        else:
            print("\n❌ Environment setup has significant issues. Please resolve errors above.")
        
        # Next steps
        print("\n📋 Next Steps:")
        if not os.path.exists("env-file"):
            print("   1. Install HexaEight License to create env-file")
        if not os.environ.get("HEXAEIGHT_CLIENT_ID"):
            print("   2. Set up client credentials with --setup-credentials")


def main():
    """Main function."""
    setup = EnvironmentSetup()
    
    # Parse command line arguments
    args = sys.argv[1:]
    
    if "--help" in args or "-h" in args:
        print(__doc__)
        return
    
    if "--setup-credentials" in args:
        setup.setup_credentials_interactive()
        print("\nRun setup again to verify credentials:")
        print("python setup_test_environment.py")
        return
    
    check_only = "--check-only" in args
    
    # Run comprehensive check
    setup.run_comprehensive_check(check_pubsub=not check_only)
    
    # Offer to setup credentials if needed
    if not check_only and not os.environ.get("HEXAEIGHT_CLIENT_ID"):
        print("\n❓ Would you like to set up client credentials now?")
        response = input("Enter 'y' to continue, or any other key to skip: ").strip().lower()
        if response in ['y', 'yes']:
            setup.setup_credentials_interactive()


if __name__ == "__main__":
    main()
