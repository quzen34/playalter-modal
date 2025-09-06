"""
PLAYALTER Streaming Platform Integrations
Support for Twitch, YouTube, Discord, and OBS Virtual Camera
"""

import asyncio
import subprocess
import json
import tempfile
import os
from typing import Dict, Optional, Any
import numpy as np
import cv2

class StreamingIntegration:
    """Base class for streaming platform integrations"""
    
    def __init__(self):
        self.is_active = False
        self.process = None
        self.stream_key = None
        
    async def start_stream(self, stream_key: str, **kwargs):
        """Start streaming to platform"""
        raise NotImplementedError
        
    async def stop_stream(self):
        """Stop streaming"""
        if self.process and self.process.poll() is None:
            self.process.terminate()
            await asyncio.sleep(1)
            if self.process.poll() is None:
                self.process.kill()
        self.is_active = False
        
    def send_frame(self, frame: np.ndarray):
        """Send frame to stream"""
        raise NotImplementedError

class TwitchIntegration(StreamingIntegration):
    """Twitch RTMP streaming integration"""
    
    def __init__(self):
        super().__init__()
        self.rtmp_url = "rtmp://live.twitch.tv/live/"
        
    async def start_stream(self, stream_key: str, width: int = 1280, height: int = 720, fps: int = 30, bitrate: str = "2500k"):
        """Start RTMP stream to Twitch"""
        self.stream_key = stream_key
        
        # FFmpeg command for Twitch streaming
        ffmpeg_cmd = [
            'ffmpeg',
            '-f', 'rawvideo',
            '-vcodec', 'rawvideo',
            '-pix_fmt', 'bgr24',
            '-s', f'{width}x{height}',
            '-r', str(fps),
            '-i', '-',
            '-c:v', 'libx264',
            '-pix_fmt', 'yuv420p',
            '-preset', 'ultrafast',
            '-tune', 'zerolatency',
            '-b:v', bitrate,
            '-maxrate', bitrate,
            '-bufsize', str(int(bitrate[:-1]) * 2) + 'k',
            '-g', str(fps * 2),
            '-keyint_min', str(fps),
            '-sc_threshold', '0',
            '-f', 'flv',
            f'{self.rtmp_url}{stream_key}'
        ]
        
        try:
            self.process = subprocess.Popen(
                ffmpeg_cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            self.is_active = True
            return True
        except Exception as e:
            print(f"Error starting Twitch stream: {e}")
            return False
    
    def send_frame(self, frame: np.ndarray):
        """Send frame to Twitch stream"""
        if self.is_active and self.process and self.process.stdin:
            try:
                self.process.stdin.write(frame.tobytes())
                self.process.stdin.flush()
            except Exception as e:
                print(f"Error sending frame to Twitch: {e}")
                self.is_active = False

class YouTubeIntegration(StreamingIntegration):
    """YouTube Live RTMP streaming integration"""
    
    def __init__(self):
        super().__init__()
        self.rtmp_url = "rtmp://a.rtmp.youtube.com/live2/"
        
    async def start_stream(self, stream_key: str, width: int = 1280, height: int = 720, fps: int = 30, bitrate: str = "4500k"):
        """Start RTMP stream to YouTube Live"""
        self.stream_key = stream_key
        
        # FFmpeg command for YouTube streaming (higher quality)
        ffmpeg_cmd = [
            'ffmpeg',
            '-f', 'rawvideo',
            '-vcodec', 'rawvideo',
            '-pix_fmt', 'bgr24',
            '-s', f'{width}x{height}',
            '-r', str(fps),
            '-i', '-',
            '-c:v', 'libx264',
            '-pix_fmt', 'yuv420p',
            '-preset', 'medium',
            '-tune', 'zerolatency',
            '-b:v', bitrate,
            '-maxrate', bitrate,
            '-bufsize', str(int(bitrate[:-1]) * 2) + 'k',
            '-g', str(fps * 2),
            '-keyint_min', str(fps),
            '-sc_threshold', '0',
            '-f', 'flv',
            f'{self.rtmp_url}{stream_key}'
        ]
        
        try:
            self.process = subprocess.Popen(
                ffmpeg_cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            self.is_active = True
            return True
        except Exception as e:
            print(f"Error starting YouTube stream: {e}")
            return False
    
    def send_frame(self, frame: np.ndarray):
        """Send frame to YouTube stream"""
        if self.is_active and self.process and self.process.stdin:
            try:
                self.process.stdin.write(frame.tobytes())
                self.process.stdin.flush()
            except Exception as e:
                print(f"Error sending frame to YouTube: {e}")
                self.is_active = False

class DiscordIntegration(StreamingIntegration):
    """Discord screen share integration via virtual camera"""
    
    def __init__(self):
        super().__init__()
        self.virtual_cam_device = None
        
    async def start_stream(self, width: int = 1280, height: int = 720, fps: int = 30):
        """Start virtual camera for Discord"""
        
        # Try to create virtual camera device
        # This would require platform-specific virtual camera drivers
        # For Windows: OBS Virtual Camera
        # For Linux: v4l2loopback
        # For macOS: CamTwist or similar
        
        try:
            if os.name == 'nt':  # Windows
                # Use OBS Virtual Camera if available
                self.virtual_cam_device = "OBS Virtual Camera"
            else:  # Linux/macOS
                # Use v4l2loopback or similar
                self.virtual_cam_device = "/dev/video10"
            
            # FFmpeg command for virtual camera
            ffmpeg_cmd = [
                'ffmpeg',
                '-f', 'rawvideo',
                '-vcodec', 'rawvideo',
                '-pix_fmt', 'bgr24',
                '-s', f'{width}x{height}',
                '-r', str(fps),
                '-i', '-',
                '-pix_fmt', 'yuv420p',
                '-f', 'v4l2' if os.name != 'nt' else 'dshow',
                self.virtual_cam_device
            ]
            
            self.process = subprocess.Popen(
                ffmpeg_cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            self.is_active = True
            return True
        except Exception as e:
            print(f"Error starting Discord virtual camera: {e}")
            return False
    
    def send_frame(self, frame: np.ndarray):
        """Send frame to virtual camera"""
        if self.is_active and self.process and self.process.stdin:
            try:
                self.process.stdin.write(frame.tobytes())
                self.process.stdin.flush()
            except Exception as e:
                print(f"Error sending frame to Discord: {e}")
                self.is_active = False

class OBSIntegration(StreamingIntegration):
    """OBS Virtual Camera integration"""
    
    def __init__(self):
        super().__init__()
        self.obs_websocket = None
        
    async def start_stream(self, width: int = 1280, height: int = 720, fps: int = 30):
        """Start OBS Virtual Camera"""
        
        # This would integrate with OBS WebSocket API
        # For now, we'll use the virtual camera approach
        
        try:
            # Create named pipe or shared memory for OBS
            pipe_name = "playalter_obs_feed"
            
            # FFmpeg command to create virtual camera feed
            ffmpeg_cmd = [
                'ffmpeg',
                '-f', 'rawvideo',
                '-vcodec', 'rawvideo',
                '-pix_fmt', 'bgr24',
                '-s', f'{width}x{height}',
                '-r', str(fps),
                '-i', '-',
                '-pix_fmt', 'yuv420p',
                '-f', 'rawvideo',
                f'pipe:{pipe_name}'
            ]
            
            self.process = subprocess.Popen(
                ffmpeg_cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            self.is_active = True
            return True
        except Exception as e:
            print(f"Error starting OBS integration: {e}")
            return False
    
    def send_frame(self, frame: np.ndarray):
        """Send frame to OBS"""
        if self.is_active and self.process and self.process.stdin:
            try:
                self.process.stdin.write(frame.tobytes())
                self.process.stdin.flush()
            except Exception as e:
                print(f"Error sending frame to OBS: {e}")
                self.is_active = False

class StreamingManager:
    """Manage multiple streaming integrations"""
    
    def __init__(self):
        self.integrations = {
            'twitch': TwitchIntegration(),
            'youtube': YouTubeIntegration(),
            'discord': DiscordIntegration(),
            'obs': OBSIntegration()
        }
        self.active_streams = {}
        
    async def start_streaming(self, platform: str, **kwargs):
        """Start streaming to specified platform"""
        if platform not in self.integrations:
            return {"success": False, "error": f"Unknown platform: {platform}"}
        
        integration = self.integrations[platform]
        
        if platform in ['twitch', 'youtube']:
            stream_key = kwargs.get('stream_key')
            if not stream_key:
                return {"success": False, "error": "Stream key required"}
            
            success = await integration.start_stream(
                stream_key=stream_key,
                width=kwargs.get('width', 1280),
                height=kwargs.get('height', 720),
                fps=kwargs.get('fps', 30),
                bitrate=kwargs.get('bitrate', '2500k' if platform == 'twitch' else '4500k')
            )
        else:
            success = await integration.start_stream(
                width=kwargs.get('width', 1280),
                height=kwargs.get('height', 720),
                fps=kwargs.get('fps', 30)
            )
        
        if success:
            self.active_streams[platform] = integration
            return {"success": True, "message": f"Started streaming to {platform}"}
        else:
            return {"success": False, "error": f"Failed to start {platform} stream"}
    
    async def stop_streaming(self, platform: str):
        """Stop streaming to specified platform"""
        if platform in self.active_streams:
            await self.active_streams[platform].stop_stream()
            del self.active_streams[platform]
            return {"success": True, "message": f"Stopped streaming to {platform}"}
        else:
            return {"success": False, "error": f"No active stream to {platform}"}
    
    def send_frame_to_all(self, frame: np.ndarray):
        """Send frame to all active streams"""
        for platform, integration in self.active_streams.items():
            try:
                integration.send_frame(frame)
            except Exception as e:
                print(f"Error sending frame to {platform}: {e}")
    
    def get_active_streams(self):
        """Get list of active streaming platforms"""
        return list(self.active_streams.keys())
    
    async def stop_all_streams(self):
        """Stop all active streams"""
        for platform in list(self.active_streams.keys()):
            await self.stop_streaming(platform)

# Utility functions for stream optimization
def optimize_frame_for_streaming(frame: np.ndarray, target_fps: int = 30) -> np.ndarray:
    """Optimize frame for streaming performance"""
    
    # Resize if too large
    height, width = frame.shape[:2]
    if width > 1920 or height > 1080:
        # Scale down maintaining aspect ratio
        scale = min(1920/width, 1080/height)
        new_width = int(width * scale)
        new_height = int(height * scale)
        frame = cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_LINEAR)
    
    # Apply sharpening filter for better encoding
    kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
    frame = cv2.filter2D(frame, -1, kernel * 0.1)
    
    # Ensure frame is in correct format
    if len(frame.shape) == 3 and frame.shape[2] == 3:
        # Convert RGB to BGR if needed
        if frame.dtype != np.uint8:
            frame = frame.astype(np.uint8)
    
    return frame

def get_optimal_streaming_settings(platform: str, resolution: str = "720p") -> Dict[str, Any]:
    """Get optimal streaming settings for each platform"""
    
    settings = {
        'twitch': {
            '480p': {'width': 854, 'height': 480, 'bitrate': '1000k', 'fps': 30},
            '720p': {'width': 1280, 'height': 720, 'bitrate': '2500k', 'fps': 30},
            '1080p': {'width': 1920, 'height': 1080, 'bitrate': '6000k', 'fps': 60}
        },
        'youtube': {
            '480p': {'width': 854, 'height': 480, 'bitrate': '1500k', 'fps': 30},
            '720p': {'width': 1280, 'height': 720, 'bitrate': '4500k', 'fps': 60},
            '1080p': {'width': 1920, 'height': 1080, 'bitrate': '9000k', 'fps': 60}
        },
        'discord': {
            '480p': {'width': 854, 'height': 480, 'fps': 30},
            '720p': {'width': 1280, 'height': 720, 'fps': 30},
            '1080p': {'width': 1920, 'height': 1080, 'fps': 30}
        },
        'obs': {
            '480p': {'width': 854, 'height': 480, 'fps': 30},
            '720p': {'width': 1280, 'height': 720, 'fps': 60},
            '1080p': {'width': 1920, 'height': 1080, 'fps': 60}
        }
    }
    
    return settings.get(platform, {}).get(resolution, settings[platform]['720p'])

# Example usage
async def example_streaming_usage():
    """Example of how to use the streaming integrations"""
    
    manager = StreamingManager()
    
    # Start streaming to Twitch
    result = await manager.start_streaming('twitch', 
                                         stream_key='your_twitch_key',
                                         width=1280, height=720, fps=30)
    print(result)
    
    # Start virtual camera for Discord
    result = await manager.start_streaming('discord', 
                                         width=1280, height=720, fps=30)
    print(result)
    
    # Simulate sending frames
    dummy_frame = np.random.randint(0, 255, (720, 1280, 3), dtype=np.uint8)
    for i in range(100):
        optimized_frame = optimize_frame_for_streaming(dummy_frame)
        manager.send_frame_to_all(optimized_frame)
        await asyncio.sleep(1/30)  # 30 FPS
    
    # Stop all streams
    await manager.stop_all_streams()

if __name__ == "__main__":
    # Test the streaming integrations
    asyncio.run(example_streaming_usage())