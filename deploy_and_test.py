#!/usr/bin/env python3
"""
PLAYALTER Deploy and Test Automation
Automatically deploys the app and runs comprehensive tests
"""

import subprocess
import sys
import os
import time
import json
from test_suite import PlayalterTestSuite

def run_command(command, description, timeout=120):
    """Run command with proper output handling"""
    print(f"\n🔧 {description}...")
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
            print(f"✅ {description} successful!")
            
            # Extract URL from output if deploying
            if "modal deploy" in command and "fastapi-app" in result.stdout:
                lines = result.stdout.split('\n')
                for line in lines:
                    if "https://" in line and "fastapi-app" in line:
                        url = line.strip().split()[-1]
                        if url.startswith('https://'):
                            print(f"🔗 Deployed URL: {url}")
                            return url
            
            return True
        else:
            print(f"❌ {description} failed!")
            print(f"Error: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"❌ {description} timed out after {timeout} seconds!")
        return False
    except Exception as e:
        print(f"❌ {description} error: {e}")
        return False

def deploy_app():
    """Deploy the PLAYALTER app"""
    print("🚀 Starting PLAYALTER deployment...")
    
    # Check if files exist
    if not os.path.exists('main_app_complete.py'):
        print("❌ main_app_complete.py not found!")
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
    print(f"\n⏳ Waiting for service to be ready at {url}...")
    
    import requests
    
    start_time = time.time()
    while time.time() - start_time < max_wait:
        try:
            response = requests.get(f"{url}/health", timeout=10)
            if response.status_code == 200:
                print("✅ Service is ready!")
                return True
        except:
            pass
        
        print(".", end="", flush=True)
        time.sleep(3)
    
    print(f"\n❌ Service not ready after {max_wait} seconds")
    return False

def run_tests(url):
    """Run the comprehensive test suite"""
    print(f"\n🧪 Starting comprehensive tests for {url}...")
    
    # Initialize test suite
    test_suite = PlayalterTestSuite(url)
    
    # Run all tests
    result = test_suite.run_all_tests()
    
    return result

def generate_deployment_report(deploy_url, test_results):
    """Generate deployment and test report"""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    
    report = f"""
# PLAYALTER Deployment & Test Report
Generated: {timestamp}

## Deployment Status
- **URL**: {deploy_url}
- **Status**: {'✅ Success' if deploy_url else '❌ Failed'}

## Test Results Summary
- **Total Tests**: {test_results.get('summary', {}).get('total', 0)}
- **Passed**: {test_results.get('summary', {}).get('passed', 0)}
- **Failed**: {test_results.get('summary', {}).get('failed', 0)}
- **Success Rate**: {test_results.get('summary', {}).get('success_rate', 0):.1f}%

## Service Health
- Privacy Mask Generator: {'✅ Working' if any(t.get('test', '').startswith('mask_') and t.get('status') == 'success' for t in test_results.get('tests', [])) else '❌ Issues'}
- Face Swap Studio: {'✅ Working' if any(t.get('test', '').startswith('face_') and t.get('status') == 'success' for t in test_results.get('tests', [])) else '❌ Issues'}

## Next Steps
1. Visit the deployed application: {deploy_url}
2. Test manually: Upload images and verify functionality
3. Check detailed test report: {test_results.get('report_file', 'N/A')}

---
🎭 PLAYALTER v2.0 - Complete System
    """
    
    # Save report
    report_filename = f"deployment_report_{time.strftime('%Y%m%d_%H%M%S')}.md"
    with open(report_filename, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\n📋 Deployment report saved: {report_filename}")
    return report_filename

def main():
    """Main deployment and testing workflow"""
    print("🎭 PLAYALTER Automated Deploy & Test System")
    print("=" * 50)
    
    # Step 1: Deploy the application
    deploy_url = deploy_app()
    
    if not deploy_url:
        print("❌ Deployment failed! Cannot proceed with testing.")
        sys.exit(1)
    
    # Step 2: Wait for service to be ready
    if not wait_for_service(deploy_url):
        print("❌ Service failed to start properly!")
        sys.exit(1)
    
    # Step 3: Run comprehensive tests
    test_results = run_tests(deploy_url)
    
    # Step 4: Generate final report
    report_file = generate_deployment_report(deploy_url, test_results)
    
    # Step 5: Final summary
    print("\n" + "=" * 60)
    print("🎉 PLAYALTER DEPLOYMENT & TESTING COMPLETE!")
    print("=" * 60)
    print(f"🔗 Live Application: {deploy_url}")
    print(f"📊 Test Success Rate: {test_results.get('summary', {}).get('success_rate', 0):.1f}%")
    print(f"📋 Deployment Report: {report_file}")
    print(f"📋 Test Report: {test_results.get('report_file', 'N/A')}")
    print("=" * 60)
    
    # Quick access instructions
    print("\n🚀 QUICK ACCESS:")
    print(f"• Homepage: {deploy_url}")
    print(f"• Privacy Masks: {deploy_url}/mask-generator")
    print(f"• Face Swap: {deploy_url}/face-swap")
    print(f"• Health Check: {deploy_url}/health")
    
    # Exit with appropriate code
    if test_results.get('success') and test_results.get('summary', {}).get('failed', 1) == 0:
        print("\n✅ All systems operational!")
        sys.exit(0)
    else:
        print("\n⚠️  Some issues detected. Check reports for details.")
        sys.exit(1)

if __name__ == "__main__":
    main()