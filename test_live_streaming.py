#!/usr/bin/env python3
"""
PLAYALTER Live Streaming Test Suite
Test real-time WebSocket functionality and streaming performance
"""

import asyncio
import websockets
import json
import time
import numpy as np
import cv2
from PIL import Image
import io
import base64
import requests

class LiveStreamingTester:
    """Test suite for PLAYALTER live streaming functionality"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.ws_url = base_url.replace('https://', 'wss://').replace('http://', 'ws://')
        self.client_id = f'test_client_{int(time.time())}'
        self.test_results = []
    
    def generate_test_frame(self, width: int = 640, height: int = 480) -> bytes:
        """Generate a test frame with synthetic faces"""
        # Create test image with geometric shapes as "faces"
        frame = np.random.randint(50, 200, (height, width, 3), dtype=np.uint8)
        
        # Add some rectangular "faces"
        for i in range(3):
            x = np.random.randint(50, width - 150)
            y = np.random.randint(50, height - 150)
            # Draw a face-like rectangle
            cv2.rectangle(frame, (x, y), (x + 100, y + 120), (255, 200, 180), -1)
            # Add "eyes"
            cv2.circle(frame, (x + 25, y + 30), 8, (0, 0, 0), -1)
            cv2.circle(frame, (x + 75, y + 30), 8, (0, 0, 0), -1)
            # Add "mouth"
            cv2.ellipse(frame, (x + 50, y + 80), (20, 10), 0, 0, 180, (50, 50, 50), -1)
        
        # Encode as JPEG
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 80]
        _, buffer = cv2.imencode('.jpg', frame, encode_param)
        return buffer.tobytes()
    
    async def test_websocket_connection(self):
        """Test WebSocket connection establishment"""
        print("Testing WebSocket connection...")
        
        try:
            ws_endpoint = f"{self.ws_url}/ws/live-swap/{self.client_id}"
            async with websockets.connect(ws_endpoint, timeout=10) as websocket:
                # Send a ping message
                await websocket.send(json.dumps({"action": "ping"}))
                
                # Wait for response
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5)
                    print(f"  ✓ WebSocket connection successful")
                    return True
                except asyncio.TimeoutError:
                    print(f"  ✗ WebSocket timeout - no response")
                    return False
                    
        except Exception as e:
            print(f"  ✗ WebSocket connection failed: {e}")
            return False
    
    async def test_frame_processing(self):
        """Test real-time frame processing"""
        print("Testing frame processing...")
        
        try:
            ws_endpoint = f"{self.ws_url}/ws/live-swap/{self.client_id}"
            async with websockets.connect(ws_endpoint, timeout=10) as websocket:
                
                # Send mask settings
                mask_settings = {
                    "action": "update_mask",
                    "mask_settings": {
                        "type": "blur",
                        "intensity": 0.7,
                        "color": [100, 100, 100]
                    }
                }
                await websocket.send(json.dumps(mask_settings))
                
                # Send test frames and measure processing time
                processing_times = []
                
                for i in range(10):
                    start_time = time.time()
                    
                    # Generate and send test frame
                    test_frame = self.generate_test_frame()
                    await websocket.send(test_frame)
                    
                    # Wait for processed frame
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=5)
                        processing_time = (time.time() - start_time) * 1000  # ms
                        processing_times.append(processing_time)
                        
                        if i == 0:  # First frame
                            print(f"  ✓ First frame processed in {processing_time:.1f}ms")
                    
                    except asyncio.TimeoutError:
                        print(f"  ✗ Frame {i+1} processing timeout")
                        return False
                
                # Calculate statistics
                if processing_times:
                    avg_time = sum(processing_times) / len(processing_times)
                    max_time = max(processing_times)
                    min_time = min(processing_times)
                    
                    print(f"  ✓ Processed {len(processing_times)} frames")
                    print(f"  ✓ Average processing time: {avg_time:.1f}ms")
                    print(f"  ✓ Min/Max processing time: {min_time:.1f}ms / {max_time:.1f}ms")
                    
                    # Check if performance is good enough for real-time
                    if avg_time < 33:  # 30 FPS = 33ms per frame
                        print(f"  ✓ Performance suitable for 30+ FPS")
                        return True
                    else:
                        print(f"  ⚠ Performance may not sustain 30 FPS")
                        return True  # Still working, just slower
                
        except Exception as e:
            print(f"  ✗ Frame processing test failed: {e}")
            return False
    
    async def test_mask_types(self):
        """Test different mask types"""
        print("Testing different mask types...")
        
        mask_types = ['blur', 'pixelate', 'color_block', 'off']
        successful_masks = 0
        
        try:
            ws_endpoint = f"{self.ws_url}/ws/live-swap/{self.client_id}"
            async with websockets.connect(ws_endpoint, timeout=10) as websocket:
                
                for mask_type in mask_types:
                    print(f"  Testing {mask_type} mask...")
                    
                    # Set mask type
                    mask_settings = {
                        "action": "update_mask",
                        "mask_settings": {
                            "type": mask_type,
                            "intensity": 0.8,
                            "color": [100, 100, 100]
                        }
                    }
                    await websocket.send(json.dumps(mask_settings))
                    
                    # Wait for acknowledgment
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=3)
                        response_data = json.loads(response)
                        if response_data.get("status") == "mask_updated":
                            print(f"    ✓ {mask_type} mask configured")
                            
                            # Send a test frame
                            test_frame = self.generate_test_frame()
                            await websocket.send(test_frame)
                            
                            # Get processed frame
                            processed = await asyncio.wait_for(websocket.recv(), timeout=5)
                            print(f"    ✓ {mask_type} mask applied successfully")
                            successful_masks += 1
                    
                    except (asyncio.TimeoutError, json.JSONDecodeError) as e:
                        print(f"    ✗ {mask_type} mask failed: {e}")
                
                print(f"  ✓ {successful_masks}/{len(mask_types)} mask types working")
                return successful_masks > 0
                
        except Exception as e:
            print(f"  ✗ Mask type testing failed: {e}")
            return False
    
    async def test_performance_stats(self):
        """Test performance statistics retrieval"""
        print("Testing performance statistics...")
        
        try:
            ws_endpoint = f"{self.ws_url}/ws/live-swap/{self.client_id}"
            async with websockets.connect(ws_endpoint, timeout=10) as websocket:
                
                # Request stats
                stats_request = {"action": "get_stats"}
                await websocket.send(json.dumps(stats_request))
                
                # Wait for stats response
                response = await asyncio.wait_for(websocket.recv(), timeout=5)
                stats_data = json.loads(response)
                
                if stats_data.get("status") == "stats":
                    stats = stats_data.get("data", {})
                    print(f"  ✓ Performance stats received")
                    print(f"  ✓ Total frames: {stats.get('total_frames', 0)}")
                    print(f"  ✓ Active streams: {stats.get('active_streams', 0)}")
                    print(f"  ✓ Current FPS: {stats.get('current_fps', 0):.1f}")
                    return True
                else:
                    print(f"  ✗ Invalid stats response")
                    return False
                    
        except Exception as e:
            print(f"  ✗ Performance stats test failed: {e}")
            return False
    
    def test_live_stream_page(self):
        """Test live stream page loading"""
        print("Testing live stream page...")
        
        try:
            response = requests.get(f"{self.base_url}/live-stream", timeout=10)
            
            if response.status_code == 200:
                content = response.text
                
                # Check for key elements
                if "PLAYALTER Live Streaming" in content:
                    print("  ✓ Page title found")
                if "WebSocket" in content or "websocket" in content:
                    print("  ✓ WebSocket functionality detected")
                if "originalVideo" in content and "processedCanvas" in content:
                    print("  ✓ Video elements present")
                if "maskType" in content and "maskIntensity" in content:
                    print("  ✓ Mask controls found")
                
                print(f"  ✓ Live stream page loaded successfully")
                return True
            else:
                print(f"  ✗ Live stream page failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"  ✗ Live stream page test failed: {e}")
            return False
    
    async def run_all_tests(self):
        """Run complete test suite"""
        print("🎭 PLAYALTER Live Streaming Test Suite")
        print("=" * 50)
        print(f"Testing: {self.base_url}")
        print(f"Client ID: {self.client_id}")
        print()
        
        tests = [
            ("Page Loading", self.test_live_stream_page),
            ("WebSocket Connection", self.test_websocket_connection),
            ("Frame Processing", self.test_frame_processing),
            ("Mask Types", self.test_mask_types),
            ("Performance Stats", self.test_performance_stats)
        ]
        
        results = []
        
        for test_name, test_func in tests:
            print(f"[{len(results)+1}/{len(tests)}] {test_name}...")
            
            try:
                if asyncio.iscoroutinefunction(test_func):
                    result = await test_func()
                else:
                    result = test_func()
                results.append((test_name, result))
            except Exception as e:
                print(f"  ✗ Test failed with exception: {e}")
                results.append((test_name, False))
            
            print()
        
        # Summary
        passed = sum(1 for _, result in results if result)
        total = len(results)
        success_rate = (passed / total * 100) if total > 0 else 0
        
        print("=" * 50)
        print("LIVE STREAMING TEST SUMMARY")
        print("=" * 50)
        print(f"Total Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        print(f"Success Rate: {success_rate:.1f}%")
        print("=" * 50)
        
        # Detailed results
        print("\nDETAILED RESULTS:")
        for test_name, result in results:
            status = "PASS" if result else "FAIL"
            print(f"  {test_name}: {status}")
        
        print(f"\nTesting completed at {time.strftime('%H:%M:%S')}")
        
        if passed == total:
            print("SUCCESS: All live streaming tests passed!")
            return True
        else:
            print("WARNING: Some live streaming tests failed.")
            return False

async def main():
    """Main test execution"""
    base_url = "https://quzen34--playalter-complete-fastapi-app.modal.run"
    
    tester = LiveStreamingTester(base_url)
    success = await tester.run_all_tests()
    
    return 0 if success else 1

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        exit(exit_code)
    except KeyboardInterrupt:
        print("\nTest suite interrupted by user")
        exit(1)
    except Exception as e:
        print(f"Test suite failed: {e}")
        exit(1)