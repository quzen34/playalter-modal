#!/usr/bin/env python3
"""
PLAYALTER Deploy and Test Automation (Windows Compatible)
Automatically deploys the app and runs comprehensive tests
"""

import subprocess
import sys
import os
import time
import json
import requests

def run_command(command, description, timeout=120):
    """Run command with proper output handling"""
    print(f"\n>> {description}...")
    print(f"Command: {command}")
    
    try:
        # Set environment for UTF-8
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=timeout,
            env=env
        )
        
        if result.returncode == 0:
            print(f"SUCCESS: {description} completed!")
            
            # Extract URL from output if deploying
            if "modal deploy" in command and "fastapi-app" in result.stdout:
                lines = result.stdout.split('\n')
                for line in lines:
                    if "https://" in line and "fastapi-app" in line:
                        url = line.strip().split()[-1]
                        if url.startswith('https://'):
                            print(f"Deployed URL: {url}")
                            return url
            
            return True
        else:
            print(f"ERROR: {description} failed!")
            print(f"Error: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"ERROR: {description} timed out after {timeout} seconds!")
        return False
    except Exception as e:
        print(f"ERROR: {description} error: {e}")
        return False

def deploy_app():
    """Deploy the PLAYALTER app"""
    print("Starting PLAYALTER deployment...")
    
    # Check if files exist
    if not os.path.exists('main_app_complete.py'):
        print("ERROR: main_app_complete.py not found!")
        return None
    
    # Deploy the app
    deploy_result = run_command(
        "python deploy_modal.py", 
        "Deploying PLAYALTER to Modal",
        timeout=180
    )
    
    if deploy_result and isinstance(deploy_result, str) and deploy_result.startswith('https://'):
        return deploy_result
    elif deploy_result is True:
        # Default URL if extraction failed
        return "https://quzen34--playalter-complete-fastapi-app.modal.run"
    else:
        return None

def wait_for_service(url, max_wait=60):
    """Wait for the service to be ready"""
    print(f"\nWaiting for service to be ready at {url}...")
    
    start_time = time.time()
    while time.time() - start_time < max_wait:
        try:
            response = requests.get(f"{url}/health", timeout=10)
            if response.status_code == 200:
                print("Service is ready!")
                return True
        except:
            pass
        
        print(".", end="", flush=True)
        time.sleep(3)
    
    print(f"\nService not ready after {max_wait} seconds")
    return False

def run_basic_tests(url):
    """Run basic test suite"""
    print(f"\nStarting basic tests for {url}...")
    
    try:
        # Run the simple test suite
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        
        result = subprocess.run(
            ["python", "test_simple.py"],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            env=env
        )
        
        print("Test Results:")
        print(result.stdout)
        
        if result.stderr:
            print("Test Errors:")
            print(result.stderr)
        
        return result.returncode == 0
        
    except Exception as e:
        print(f"Testing failed: {e}")
        return False

def generate_deployment_report(deploy_url, test_success):
    """Generate deployment and test report"""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    
    report = f"""# PLAYALTER Deployment & Test Report
Generated: {timestamp}

## Deployment Status
- **URL**: {deploy_url}
- **Status**: {'SUCCESS' if deploy_url else 'FAILED'}

## Test Results Summary
- **Basic Tests**: {'PASSED' if test_success else 'FAILED'}
- **Service Status**: {'OPERATIONAL' if test_success else 'ISSUES DETECTED'}

## Service Health
- Privacy Mask Generator: {'Working' if test_success else 'Issues'}
- Face Swap Studio: {'Working' if test_success else 'Issues'}

## Next Steps
1. Visit the deployed application: {deploy_url}
2. Test manually: Upload images and verify functionality
3. Check service health at: {deploy_url}/health

---
PLAYALTER v2.0 - Complete System
"""
    
    # Save report
    report_filename = f"deployment_report_{time.strftime('%Y%m%d_%H%M%S')}.md"
    with open(report_filename, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\nDeployment report saved: {report_filename}")
    return report_filename

def main():
    """Main deployment and testing workflow"""
    print("PLAYALTER Automated Deploy & Test System")
    print("=" * 50)
    
    # Step 1: Deploy the application
    deploy_url = deploy_app()
    
    if not deploy_url:
        print("Deployment failed! Cannot proceed with testing.")
        sys.exit(1)
    
    # Step 2: Wait for service to be ready
    if not wait_for_service(deploy_url):
        print("Service failed to start properly!")
        sys.exit(1)
    
    # Step 3: Run basic tests
    test_success = run_basic_tests(deploy_url)
    
    # Step 4: Generate final report
    report_file = generate_deployment_report(deploy_url, test_success)
    
    # Step 5: Final summary
    print("\n" + "=" * 60)
    print("PLAYALTER DEPLOYMENT & TESTING COMPLETE!")
    print("=" * 60)
    print(f"Live Application: {deploy_url}")
    print(f"Test Status: {'SUCCESS' if test_success else 'FAILED'}")
    print(f"Deployment Report: {report_file}")
    print("=" * 60)
    
    # Quick access instructions
    print("\nQUICK ACCESS:")
    print(f"• Homepage: {deploy_url}")
    print(f"• Privacy Masks: {deploy_url}/mask-generator")
    print(f"• Face Swap: {deploy_url}/face-swap")
    print(f"• Health Check: {deploy_url}/health")
    
    # Exit with appropriate code
    if test_success:
        print("\nAll systems operational!")
        sys.exit(0)
    else:
        print("\nSome issues detected. Check reports for details.")
        sys.exit(1)

if __name__ == "__main__":
    main()