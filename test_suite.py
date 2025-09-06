#!/usr/bin/env python3
"""
PLAYALTER Automated Testing Suite
Comprehensive testing system for all PLAYALTER services
"""

import requests
import time
import json
import base64
import os
from PIL import Image, ImageDraw, ImageFont
import numpy as np
from datetime import datetime
import hashlib
import tempfile
import sys
import traceback

class PlayalterTestSuite:
    def __init__(self, base_url=None):
        self.base_url = base_url or "https://quzen34--playalter-complete-fastapi-app.modal.run"
        self.test_results = []
        self.start_time = time.time()
        self.test_images = {}
        self.report_data = {
            "timestamp": datetime.now().isoformat(),
            "base_url": self.base_url,
            "tests": [],
            "summary": {},
            "performance": {}
        }
    
    def log(self, message, level="INFO"):
        """Enhanced logging with timestamps"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        color_codes = {
            "INFO": "\033[94m",    # Blue
            "SUCCESS": "\033[92m",  # Green
            "WARNING": "\033[93m",  # Yellow
            "ERROR": "\033[91m",    # Red
            "RESET": "\033[0m"      # Reset
        }
        
        color = color_codes.get(level, color_codes["INFO"])
        reset = color_codes["RESET"]
        print(f"{color}[{timestamp}] {level}: {message}{reset}")
    
    def generate_test_images(self):
        """Generate comprehensive test images for all scenarios"""
        self.log("🎨 Generating test images...")
        
        # Generate single face test image (for mask generation)
        single_face = self.create_single_face_image()
        self.test_images['single_face'] = single_face
        
        # Generate multi-face test image (for face swap)
        multi_face = self.create_multi_face_image()
        self.test_images['multi_face'] = multi_face
        
        # Generate target face for swapping
        target_face = self.create_target_face_image()
        self.test_images['target_face'] = target_face
        
        # Generate ethnicity-diverse faces
        diverse_faces = self.create_diverse_ethnicity_faces()
        self.test_images.update(diverse_faces)
        
        self.log(f"✅ Generated {len(self.test_images)} test images", "SUCCESS")
        return self.test_images
    
    def create_single_face_image(self):
        """Create a single face for mask testing"""
        # Create base image
        img = Image.new('RGB', (400, 500), color=(220, 200, 180))
        draw = ImageDraw.Draw(img)
        
        # Draw face outline (oval)
        draw.ellipse([100, 150, 300, 350], fill=(200, 180, 160), outline=(150, 130, 110))
        
        # Draw eyes
        draw.ellipse([130, 200, 160, 220], fill=(255, 255, 255))  # Left eye white
        draw.ellipse([135, 205, 155, 215], fill=(100, 50, 30))    # Left eye iris
        draw.ellipse([240, 200, 270, 220], fill=(255, 255, 255))  # Right eye white
        draw.ellipse([245, 205, 265, 215], fill=(100, 50, 30))    # Right eye iris
        
        # Draw nose
        draw.polygon([(200, 240), (190, 260), (210, 260)], fill=(180, 160, 140))
        
        # Draw mouth
        draw.ellipse([170, 290, 230, 310], fill=(180, 100, 100))
        
        # Add hair
        draw.ellipse([80, 100, 320, 200], fill=(80, 50, 30))
        
        # Add test label
        try:
            draw.text((10, 10), "TEST FACE - SINGLE", fill=(255, 0, 0))
        except:
            pass
        
        return img
    
    def create_multi_face_image(self):
        """Create multiple faces for swap testing"""
        # Create base image
        img = Image.new('RGB', (600, 400), color=(240, 240, 240))
        draw = ImageDraw.Draw(img)
        
        # Face 1 (top-left)
        self.draw_simple_face(draw, (80, 80), size=80, skin_tone=(220, 200, 180))
        
        # Face 2 (top-right)  
        self.draw_simple_face(draw, (400, 80), size=80, skin_tone=(180, 140, 100))
        
        # Face 3 (bottom-center)
        self.draw_simple_face(draw, (240, 240), size=80, skin_tone=(240, 220, 200))
        
        # Add test label
        try:
            draw.text((10, 10), "TEST FACES - MULTI (3 FACES)", fill=(255, 0, 0))
        except:
            pass
            
        return img
    
    def create_target_face_image(self):
        """Create target face for swapping"""
        img = Image.new('RGB', (300, 300), color=(200, 220, 240))
        draw = ImageDraw.Draw(img)
        
        # Draw distinct face for swapping
        self.draw_simple_face(draw, (150, 150), size=100, skin_tone=(160, 180, 160))
        
        try:
            draw.text((10, 10), "TARGET FACE", fill=(0, 255, 0))
        except:
            pass
            
        return img
    
    def create_diverse_ethnicity_faces(self):
        """Create faces representing different ethnicities"""
        faces = {}
        ethnicities = [
            ("African", (120, 80, 60)),
            ("Asian", (220, 200, 160)), 
            ("European", (240, 220, 200)),
            ("Hispanic", (200, 180, 140)),
            ("Middle_Eastern", (200, 170, 130))
        ]
        
        for ethnicity, skin_tone in ethnicities:
            img = Image.new('RGB', (300, 400), color=(250, 250, 250))
            draw = ImageDraw.Draw(img)
            
            # Draw face with ethnicity-specific features
            self.draw_ethnicity_face(draw, (150, 200), ethnicity, skin_tone)
            
            try:
                draw.text((10, 10), f"TEST - {ethnicity}", fill=(255, 0, 0))
            except:
                pass
            
            faces[f'{ethnicity.lower()}_face'] = img
        
        return faces
    
    def draw_simple_face(self, draw, center, size=60, skin_tone=(220, 200, 180)):
        """Draw a simple face at given position"""
        x, y = center
        
        # Face outline
        draw.ellipse([x-size//2, y-size//2, x+size//2, y+size//2], 
                    fill=skin_tone, outline=(150, 130, 110))
        
        # Eyes
        eye_size = size // 8
        draw.ellipse([x-size//4, y-size//6, x-size//4+eye_size, y-size//6+eye_size], fill=(0, 0, 0))
        draw.ellipse([x+size//8, y-size//6, x+size//8+eye_size, y-size//6+eye_size], fill=(0, 0, 0))
        
        # Nose
        draw.polygon([(x, y), (x-size//12, y+size//8), (x+size//12, y+size//8)], 
                    fill=(max(0, skin_tone[0]-20), max(0, skin_tone[1]-20), max(0, skin_tone[2]-20)))
        
        # Mouth
        draw.ellipse([x-size//6, y+size//4, x+size//6, y+size//3], fill=(180, 100, 100))
    
    def draw_ethnicity_face(self, draw, center, ethnicity, skin_tone):
        """Draw face with ethnicity-specific characteristics"""
        x, y = center
        size = 120
        
        # Base face
        draw.ellipse([x-size//2, y-size//2, x+size//2, y+size//2], 
                    fill=skin_tone, outline=(max(0, skin_tone[0]-30), 
                                           max(0, skin_tone[1]-30), 
                                           max(0, skin_tone[2]-30)))
        
        # Ethnicity-specific features
        if ethnicity == "Asian":
            # More horizontal eyes
            draw.ellipse([x-size//3, y-size//8, x-size//6, y], fill=(50, 30, 20))
            draw.ellipse([x+size//6, y-size//8, x+size//3, y], fill=(50, 30, 20))
        elif ethnicity == "African":
            # Fuller features
            draw.ellipse([x-size//4, y-size//6, x-size//8, y+size//12], fill=(30, 20, 15))
            draw.ellipse([x+size//8, y-size//6, x+size//4, y+size//12], fill=(30, 20, 15))
            # Fuller lips
            draw.ellipse([x-size//4, y+size//4, x+size//4, y+size//3], fill=(120, 80, 80))
        else:
            # Standard features
            self.draw_simple_face(draw, center, size, skin_tone)
    
    def image_to_base64(self, image):
        """Convert PIL image to base64 string"""
        if isinstance(image, str):  # If it's already a path
            with open(image, 'rb') as f:
                return base64.b64encode(f.read()).decode()
        
        from io import BytesIO
        buffer = BytesIO()
        image.save(buffer, format='PNG')
        return base64.b64encode(buffer.getvalue()).decode()
    
    def save_temp_image(self, image, prefix="test"):
        """Save image to temporary file and return path"""
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png', prefix=f'{prefix}_')
        image.save(temp_file.name, format='PNG')
        return temp_file.name
    
    def test_health_check(self):
        """Test if the service is running"""
        self.log("🏥 Testing health check...")
        start_time = time.time()
        
        try:
            response = requests.get(f"{self.base_url}/health", timeout=10)
            response_time = time.time() - start_time
            
            result = {
                "test": "health_check",
                "status": "success" if response.status_code == 200 else "failed",
                "response_time": response_time,
                "status_code": response.status_code,
                "details": response.json() if response.status_code == 200 else response.text
            }
            
            if response.status_code == 200:
                self.log(f"✅ Health check passed ({response_time:.2f}s)", "SUCCESS")
            else:
                self.log(f"❌ Health check failed: {response.status_code}", "ERROR")
                
        except Exception as e:
            result = {
                "test": "health_check", 
                "status": "failed",
                "error": str(e),
                "response_time": time.time() - start_time
            }
            self.log(f"❌ Health check error: {e}", "ERROR")
        
        self.test_results.append(result)
        return result
    
    def test_privacy_mask_generation(self):
        """Test Privacy Mask Generator with all ethnicity types"""
        self.log("🎭 Testing Privacy Mask Generator...")
        results = []
        
        # Test each ethnicity
        for ethnicity_key in ['african_face', 'asian_face', 'european_face', 'hispanic_face', 'middle_eastern_face']:
            if ethnicity_key not in self.test_images:
                continue
                
            self.log(f"  Testing {ethnicity_key.replace('_face', '')} ethnicity...")
            
            # Save test image
            test_image_path = self.save_temp_image(self.test_images[ethnicity_key], f"test_{ethnicity_key}")
            
            try:
                # Step 1: Analyze ethnicity
                start_time = time.time()
                with open(test_image_path, 'rb') as f:
                    files = {'file': f}
                    response = requests.post(f"{self.base_url}/api/mask/analyze", files=files, timeout=30)
                
                analyze_time = time.time() - start_time
                
                if response.status_code != 200:
                    results.append({
                        "test": f"mask_analysis_{ethnicity_key}",
                        "status": "failed",
                        "error": f"Analysis failed: {response.status_code}",
                        "response_time": analyze_time
                    })
                    continue
                
                analysis_result = response.json()
                
                if not analysis_result.get('success'):
                    results.append({
                        "test": f"mask_analysis_{ethnicity_key}",
                        "status": "failed", 
                        "error": analysis_result.get('message', 'Unknown error'),
                        "response_time": analyze_time
                    })
                    continue
                
                detected_ethnicity = analysis_result['ethnicity']
                
                # Step 2: Generate masks for each type
                for mask_type in ['blur', 'pixelate', 'synthetic']:
                    self.log(f"    Generating {mask_type} mask...")
                    
                    start_time = time.time()
                    with open(test_image_path, 'rb') as f:
                        files = {'file': f}
                        data = {
                            'mask_type': mask_type,
                            'ethnicity': json.dumps(detected_ethnicity)
                        }
                        response = requests.post(f"{self.base_url}/api/mask/generate", files=files, data=data, timeout=30)
                    
                    generation_time = time.time() - start_time
                    
                    result = {
                        "test": f"mask_generation_{ethnicity_key}_{mask_type}",
                        "ethnicity_detected": detected_ethnicity['primary'],
                        "confidence": detected_ethnicity['confidence'],
                        "mask_type": mask_type,
                        "response_time": generation_time,
                        "analyze_time": analyze_time
                    }
                    
                    if response.status_code == 200:
                        mask_result = response.json()
                        if mask_result.get('success'):
                            result["status"] = "success"
                            result["filename"] = mask_result.get('filename')
                            result["has_output"] = bool(mask_result.get('masked_image'))
                            self.log(f"    ✅ {mask_type} mask generated ({generation_time:.2f}s)", "SUCCESS")
                        else:
                            result["status"] = "failed"
                            result["error"] = mask_result.get('message', 'Generation failed')
                            self.log(f"    ❌ {mask_type} mask failed: {result['error']}", "ERROR")
                    else:
                        result["status"] = "failed"
                        result["error"] = f"HTTP {response.status_code}"
                        self.log(f"    ❌ {mask_type} mask failed: HTTP {response.status_code}", "ERROR")
                    
                    results.append(result)
                
            except Exception as e:
                results.append({
                    "test": f"mask_generation_{ethnicity_key}",
                    "status": "failed",
                    "error": str(e),
                    "traceback": traceback.format_exc()
                })
                self.log(f"  ❌ {ethnicity_key} test failed: {e}", "ERROR")
            finally:
                # Cleanup
                try:
                    os.unlink(test_image_path)
                except:
                    pass
        
        self.test_results.extend(results)
        return results
    
    def test_face_swap_functionality(self):
        """Test Face Swap Studio"""
        self.log("🔄 Testing Face Swap Studio...")
        results = []
        
        # Test with multi-face image
        if 'multi_face' not in self.test_images or 'target_face' not in self.test_images:
            self.log("❌ Missing test images for face swap", "ERROR")
            return []
        
        source_path = self.save_temp_image(self.test_images['multi_face'], "swap_source")
        target_path = self.save_temp_image(self.test_images['target_face'], "swap_target")
        
        try:
            # Step 1: Detect faces
            self.log("  Detecting faces in source image...")
            start_time = time.time()
            
            with open(source_path, 'rb') as f:
                files = {'file': f}
                response = requests.post(f"{self.base_url}/api/face-swap/detect", files=files, timeout=30)
            
            detect_time = time.time() - start_time
            
            if response.status_code != 200:
                results.append({
                    "test": "face_detection",
                    "status": "failed",
                    "error": f"Detection failed: {response.status_code}",
                    "response_time": detect_time
                })
                return results
            
            detection_result = response.json()
            
            if not detection_result.get('success'):
                results.append({
                    "test": "face_detection",
                    "status": "failed",
                    "error": detection_result.get('message', 'Detection failed'),
                    "response_time": detect_time
                })
                return results
            
            faces_detected = detection_result.get('faces', [])
            
            results.append({
                "test": "face_detection",
                "status": "success",
                "faces_count": len(faces_detected),
                "expected_faces": 3,
                "response_time": detect_time
            })
            
            self.log(f"  ✅ Detected {len(faces_detected)} faces ({detect_time:.2f}s)", "SUCCESS")
            
            # Step 2: Test face swapping on first face
            if faces_detected:
                self.log("  Testing face swap on first detected face...")
                
                first_face = faces_detected[0]
                start_time = time.time()
                
                with open(source_path, 'rb') as source_f, open(target_path, 'rb') as target_f:
                    files = {
                        'source_file': source_f,
                        'target_file': target_f
                    }
                    data = {
                        'face_data': json.dumps(first_face)
                    }
                    response = requests.post(f"{self.base_url}/api/face-swap/process", files=files, data=data, timeout=30)
                
                swap_time = time.time() - start_time
                
                result = {
                    "test": "face_swap_process",
                    "face_id": first_face['id'],
                    "response_time": swap_time
                }
                
                if response.status_code == 200:
                    swap_result = response.json()
                    if swap_result.get('success'):
                        result["status"] = "success"
                        result["has_output"] = bool(swap_result.get('result_image'))
                        self.log(f"  ✅ Face swap successful ({swap_time:.2f}s)", "SUCCESS")
                    else:
                        result["status"] = "failed"
                        result["error"] = swap_result.get('message', 'Swap failed')
                        self.log(f"  ❌ Face swap failed: {result['error']}", "ERROR")
                else:
                    result["status"] = "failed"
                    result["error"] = f"HTTP {response.status_code}"
                    self.log(f"  ❌ Face swap failed: HTTP {response.status_code}", "ERROR")
                
                results.append(result)
            
        except Exception as e:
            results.append({
                "test": "face_swap_functionality",
                "status": "failed",
                "error": str(e),
                "traceback": traceback.format_exc()
            })
            self.log(f"❌ Face swap test failed: {e}", "ERROR")
        finally:
            # Cleanup
            try:
                os.unlink(source_path)
                os.unlink(target_path)
            except:
                pass
        
        self.test_results.extend(results)
        return results
    
    def test_performance_benchmarks(self):
        """Test performance benchmarks"""
        self.log("⚡ Testing performance benchmarks...")
        results = []
        
        # Test response times for each endpoint
        endpoints = [
            ("/", "GET"),
            ("/face-swap", "GET"),
            ("/mask-generator", "GET"),
            ("/health", "GET")
        ]
        
        for endpoint, method in endpoints:
            self.log(f"  Testing {endpoint} response time...")
            
            times = []
            for i in range(3):  # Test 3 times for average
                start_time = time.time()
                try:
                    if method == "GET":
                        response = requests.get(f"{self.base_url}{endpoint}", timeout=10)
                    
                    response_time = time.time() - start_time
                    times.append(response_time)
                    
                except Exception as e:
                    times.append(float('inf'))
            
            avg_time = sum(t for t in times if t != float('inf')) / len([t for t in times if t != float('inf')]) if times else 0
            
            result = {
                "test": f"performance_{endpoint.replace('/', '_').strip('_') or 'home'}",
                "endpoint": endpoint,
                "method": method,
                "avg_response_time": avg_time,
                "all_times": times,
                "status": "success" if avg_time < 5.0 else "warning" if avg_time < 10.0 else "failed"
            }
            
            if avg_time < 2.0:
                self.log(f"  ✅ {endpoint} fast response ({avg_time:.2f}s avg)", "SUCCESS")
            elif avg_time < 5.0:
                self.log(f"  ⚠️  {endpoint} acceptable response ({avg_time:.2f}s avg)", "WARNING")  
            else:
                self.log(f"  ❌ {endpoint} slow response ({avg_time:.2f}s avg)", "ERROR")
            
            results.append(result)
        
        self.test_results.extend(results)
        return results
    
    def generate_test_report(self):
        """Generate comprehensive HTML test report"""
        self.log("📊 Generating test report...")
        
        # Calculate summary statistics
        total_tests = len(self.test_results)
        passed_tests = len([t for t in self.test_results if t.get('status') == 'success'])
        failed_tests = len([t for t in self.test_results if t.get('status') == 'failed'])
        warning_tests = len([t for t in self.test_results if t.get('status') == 'warning'])
        
        total_time = time.time() - self.start_time
        
        # Update report data
        self.report_data.update({
            "total_time": total_time,
            "tests": self.test_results,
            "summary": {
                "total": total_tests,
                "passed": passed_tests,
                "failed": failed_tests,
                "warnings": warning_tests,
                "success_rate": (passed_tests / total_tests * 100) if total_tests > 0 else 0
            }
        })
        
        # Generate HTML report
        html_report = self.create_html_report()
        
        # Save report
        report_filename = f"playalter_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        with open(report_filename, 'w', encoding='utf-8') as f:
            f.write(html_report)
        
        self.log(f"📋 Test report saved: {report_filename}", "SUCCESS")
        return report_filename
    
    def create_html_report(self):
        """Create detailed HTML report"""
        summary = self.report_data['summary']
        
        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PLAYALTER Test Report</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            color: white;
            padding: 20px;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        h1 {{ text-align: center; font-size: 2.5em; margin-bottom: 30px; }}
        .summary {{ 
            display: grid; 
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); 
            gap: 20px; 
            margin-bottom: 40px; 
        }}
        .summary-card {{ 
            background: rgba(255, 255, 255, 0.1); 
            padding: 20px; 
            border-radius: 10px; 
            text-align: center; 
        }}
        .summary-number {{ font-size: 2em; font-weight: bold; margin-bottom: 5px; }}
        .success {{ color: #4ade80; }}
        .failed {{ color: #ef4444; }}
        .warning {{ color: #f59e0b; }}
        
        .test-section {{ 
            background: rgba(255, 255, 255, 0.1); 
            margin-bottom: 30px; 
            border-radius: 15px; 
            padding: 25px; 
        }}
        .test-item {{ 
            background: rgba(255, 255, 255, 0.05); 
            margin: 10px 0; 
            padding: 15px; 
            border-radius: 8px; 
            border-left: 4px solid #4ade80;
        }}
        .test-item.failed {{ border-left-color: #ef4444; }}
        .test-item.warning {{ border-left-color: #f59e0b; }}
        
        .test-name {{ font-weight: bold; font-size: 1.1em; margin-bottom: 8px; }}
        .test-details {{ font-size: 0.9em; opacity: 0.8; }}
        .test-time {{ color: #4ade80; }}
        .error-details {{ 
            background: rgba(239, 68, 68, 0.2); 
            padding: 10px; 
            border-radius: 5px; 
            margin-top: 10px; 
            font-family: monospace;
            font-size: 0.8em;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🎭 PLAYALTER Test Report</h1>
        
        <div class="summary">
            <div class="summary-card">
                <div class="summary-number">{summary['total']}</div>
                <div>Total Tests</div>
            </div>
            <div class="summary-card">
                <div class="summary-number success">{summary['passed']}</div>
                <div>Passed</div>
            </div>
            <div class="summary-card">
                <div class="summary-number failed">{summary['failed']}</div>
                <div>Failed</div>
            </div>
            <div class="summary-card">
                <div class="summary-number warning">{summary['warnings']}</div>
                <div>Warnings</div>
            </div>
            <div class="summary-card">
                <div class="summary-number">{summary['success_rate']:.1f}%</div>
                <div>Success Rate</div>
            </div>
            <div class="summary-card">
                <div class="summary-number">{self.report_data['total_time']:.2f}s</div>
                <div>Total Time</div>
            </div>
        </div>
        
        <div class="test-section">
            <h2>📋 Test Results</h2>
        """
        
        # Group tests by category
        test_categories = {}
        for test in self.test_results:
            category = test['test'].split('_')[0] if '_' in test['test'] else 'general'
            if category not in test_categories:
                test_categories[category] = []
            test_categories[category].append(test)
        
        for category, tests in test_categories.items():
            html += f"<h3>📊 {category.title()} Tests</h3>"
            
            for test in tests:
                status_class = test.get('status', 'unknown')
                status_icon = {"success": "✅", "failed": "❌", "warning": "⚠️"}.get(status_class, "❓")
                
                html += f"""
                <div class="test-item {status_class}">
                    <div class="test-name">{status_icon} {test['test'].replace('_', ' ').title()}</div>
                    <div class="test-details">
                """
                
                if 'response_time' in test:
                    html += f'<span class="test-time">⏱️ {test["response_time"]:.3f}s</span> | '
                
                if 'faces_count' in test:
                    html += f'👥 {test["faces_count"]} faces detected | '
                
                if 'ethnicity_detected' in test:
                    html += f'🧬 {test["ethnicity_detected"]} detected | '
                
                html += f'Status: {test.get("status", "unknown")}'
                
                html += "</div>"
                
                if test.get('error'):
                    html += f'<div class="error-details">❌ Error: {test["error"]}</div>'
                
                html += "</div>"
        
        html += """
            </div>
            
            <div class="test-section">
                <h2>🔧 System Information</h2>
                <div class="test-item">
                    <div class="test-name">Test Configuration</div>
                    <div class="test-details">
                        <strong>Base URL:</strong> """ + self.report_data['base_url'] + """<br>
                        <strong>Timestamp:</strong> """ + self.report_data['timestamp'] + """<br>
                        <strong>Test Duration:</strong> """ + f"{self.report_data['total_time']:.2f}s" + """
                    </div>
                </div>
            </div>
        </div>
    </body>
    </html>
        """
        
        return html
    
    def run_all_tests(self):
        """Run the complete test suite"""
        self.log("🚀 Starting PLAYALTER Test Suite...", "SUCCESS")
        self.log(f"🎯 Testing: {self.base_url}")
        
        try:
            # Generate test images
            self.generate_test_images()
            
            # Run all tests
            self.test_health_check()
            self.test_privacy_mask_generation()
            self.test_face_swap_functionality() 
            self.test_performance_benchmarks()
            
            # Generate report
            report_file = self.generate_test_report()
            
            # Print summary
            self.print_summary()
            
            return {
                "success": True,
                "report_file": report_file,
                "summary": self.report_data['summary']
            }
            
        except Exception as e:
            self.log(f"❌ Test suite failed: {e}", "ERROR")
            return {"success": False, "error": str(e)}
    
    def print_summary(self):
        """Print test summary to console"""
        summary = self.report_data['summary']
        
        print("\n" + "="*60)
        print("🎭 PLAYALTER TEST SUMMARY")
        print("="*60)
        print(f"Total Tests: {summary['total']}")
        print(f"✅ Passed: {summary['passed']}")
        print(f"❌ Failed: {summary['failed']}")
        print(f"⚠️  Warnings: {summary['warnings']}")
        print(f"📊 Success Rate: {summary['success_rate']:.1f}%")
        print(f"⏱️  Total Time: {self.report_data['total_time']:.2f}s")
        print("="*60)
        
        if summary['failed'] == 0:
            print("🎉 ALL TESTS PASSED! PLAYALTER is working perfectly!")
        elif summary['success_rate'] >= 80:
            print("✨ Most tests passed! PLAYALTER is mostly functional.")
        else:
            print("⚠️  Some issues detected. Check the report for details.")
        
        print("="*60 + "\n")


def main():
    """Main test execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description='PLAYALTER Automated Test Suite')
    parser.add_argument('--url', default=None, help='Base URL for testing')
    parser.add_argument('--quick', action='store_true', help='Run quick tests only')
    
    args = parser.parse_args()
    
    # Initialize test suite
    test_suite = PlayalterTestSuite(args.url)
    
    # Run tests
    result = test_suite.run_all_tests()
    
    # Exit with appropriate code
    if result['success'] and result['summary']['failed'] == 0:
        sys.exit(0)  # All tests passed
    else:
        sys.exit(1)  # Some tests failed


if __name__ == "__main__":
    main()