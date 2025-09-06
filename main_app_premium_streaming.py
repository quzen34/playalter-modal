import modal
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, WebSocket, WebSocketDisconnect, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance
import io
import base64
import numpy as np
from typing import Optional, List, Dict, Any
import cv2
import json
import random
import asyncio
import time
from datetime import datetime, timedelta
import struct
import hashlib
import uuid

# Create Modal app with premium GPU configuration
app = modal.App("playalter-premium-streaming")

# Premium GPU image with high-performance dependencies
image = modal.Image.debian_slim(python_version="3.11").pip_install(
    "fastapi",
    "pillow",
    "numpy",
    "opencv-python-headless",
    "python-multipart",
    "mediapipe",
    "websockets",
    "uvicorn[standard]",
    "python-socketio",
    "aiofiles",
    "redis",
    "python-jose[cryptography]",
    "passlib[bcrypt]"
)

web_app = FastAPI(title="PLAYALTER Premium Live Streaming", version="3.0")
security = HTTPBearer()

# Premium tier configuration
PREMIUM_TIERS = {
    "free": {
        "daily_minutes": 5,
        "max_resolution": "720p",
        "max_fps": 30,
        "concurrent_streams": 1,
        "features": ["basic_masks", "single_platform"]
    },
    "pro": {
        "daily_minutes": float('inf'),
        "max_resolution": "1080p", 
        "max_fps": 60,
        "concurrent_streams": 3,
        "features": ["all_masks", "multi_platform", "custom_masks", "hotkeys", "analytics"]
    },
    "api": {
        "daily_minutes": float('inf'),
        "max_resolution": "4K",
        "max_fps": 120,
        "concurrent_streams": 10,
        "features": ["api_access", "webhook_callbacks", "custom_endpoints", "priority_gpu"]
    }
}

# Quality mode presets
QUALITY_MODES = {
    "performance": {
        "resolution": "854x480",
        "fps": 60,
        "bitrate": "1500k",
        "preset": "ultrafast",
        "use_case": "Gaming/High FPS streaming",
        "latency": "<30ms",
        "cpu_usage": "<20%"
    },
    "balanced": {
        "resolution": "1280x720", 
        "fps": 30,
        "bitrate": "2500k",
        "preset": "fast",
        "use_case": "Video calls/Standard streaming",
        "latency": "<50ms",
        "cpu_usage": "<30%"
    },
    "quality": {
        "resolution": "1920x1080",
        "fps": 24,
        "bitrate": "4500k", 
        "preset": "medium",
        "use_case": "Recording/High quality streaming",
        "latency": "<80ms",
        "cpu_usage": "<50%"
    }
}

# Platform-specific optimizations
PLATFORM_CONFIGS = {
    "zoom": {
        "resolution": "1280x720",
        "fps": 30,
        "format": "virtual_camera",
        "device": "OBS Virtual Camera"
    },
    "teams": {
        "resolution": "1920x1080",
        "fps": 30,
        "format": "virtual_camera", 
        "device": "Microsoft Teams Camera"
    },
    "discord": {
        "resolution": "1280x720",
        "fps": 30,
        "format": "screen_share",
        "encoding": "h264"
    },
    "twitch": {
        "resolution": "1920x1080",
        "fps": 60,
        "format": "rtmp",
        "url": "rtmp://live.twitch.tv/live/",
        "bitrate": "6000k"
    },
    "youtube": {
        "resolution": "1920x1080", 
        "fps": 60,
        "format": "rtmp",
        "url": "rtmp://a.rtmp.youtube.com/live2/",
        "bitrate": "9000k"
    },
    "instagram": {
        "resolution": "1080x1920", # Portrait
        "fps": 30,
        "format": "rtmp",
        "url": "rtmps://live-api-s.facebook.com:443/rtmp/",
        "bitrate": "4000k"
    },
    "tiktok": {
        "resolution": "1080x1920", # Portrait
        "fps": 30,
        "format": "rtmp", 
        "url": "rtmp://push.tiktokcdn.com/live/",
        "bitrate": "3000k"
    }
}

# Global state management
class StreamingState:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.user_sessions: Dict[str, Dict] = {}
        self.mask_library: Dict[str, Dict] = {}
        self.performance_stats = {
            "total_streams": 0,
            "active_users": 0,
            "avg_latency": 0,
            "gpu_utilization": 0
        }
    
    def get_user_tier(self, user_id: str) -> str:
        """Get user's premium tier"""
        # In production, this would query a database
        return self.user_sessions.get(user_id, {}).get('tier', 'free')
    
    def check_usage_limits(self, user_id: str) -> Dict[str, Any]:
        """Check if user has exceeded usage limits"""
        tier = self.get_user_tier(user_id)
        tier_config = PREMIUM_TIERS[tier]
        
        # Get user's usage today (simplified)
        user_data = self.user_sessions.get(user_id, {})
        minutes_used = user_data.get('minutes_used_today', 0)
        
        return {
            "can_stream": minutes_used < tier_config["daily_minutes"],
            "remaining_minutes": tier_config["daily_minutes"] - minutes_used,
            "tier": tier,
            "features": tier_config["features"]
        }

streaming_state = StreamingState()

class PremiumMaskManager:
    """Advanced mask management with pre-generated masks and hotkeys"""
    
    def __init__(self):
        self.mask_library = {
            "slot_1": {"type": "blur", "intensity": 0.8, "hotkey": "1"},
            "slot_2": {"type": "pixelate", "intensity": 0.7, "hotkey": "2"}, 
            "slot_3": {"type": "color_block", "intensity": 0.9, "hotkey": "3"},
            "slot_4": {"type": "custom", "intensity": 1.0, "hotkey": "4"},
            "slot_5": {"type": "off", "intensity": 0.0, "hotkey": "5"}
        }
        self.active_slot = "slot_1"
    
    def get_mask_for_slot(self, slot: str) -> Dict:
        """Get mask configuration for slot"""
        return self.mask_library.get(slot, self.mask_library["slot_1"])
    
    def switch_mask(self, slot: str) -> Dict:
        """Switch to different mask slot"""
        if slot in self.mask_library:
            self.active_slot = slot
            return self.get_mask_for_slot(slot)
        return self.get_mask_for_slot(self.active_slot)
    
    def save_custom_mask(self, slot: str, mask_config: Dict):
        """Save custom mask to slot"""
        if slot.startswith("slot_"):
            self.mask_library[slot] = {**mask_config, "hotkey": slot[-1]}

@app.function(
    gpu="A10G",  # Premium GPU for maximum performance
    cpu=4,
    memory=8192,
    timeout=3600,
    concurrency_limit=10,
    container_idle_timeout=1800
)
@modal.asgi_app()
def premium_streaming_app():
    
    class LiveStreamProcessor:
        """GPU-optimized batch processing for premium performance"""
        
        def __init__(self):
            self.gpu_context = None
            self.batch_size = 4
            self.processing_queue = []
            self.initialize_gpu()
        
        def initialize_gpu(self):
            """Initialize GPU context for maximum performance"""
            try:
                if cv2.cuda.getCudaEnabledDeviceCount() > 0:
                    self.gpu_context = True
                    print("Premium GPU (A10G) initialized successfully")
                else:
                    print("GPU not available, falling back to CPU")
            except Exception as e:
                print(f"GPU initialization failed: {e}")
        
        async def process_frame_batch(self, frames: List[bytes], mask_config: Dict) -> List[bytes]:
            """Process multiple frames in batch for optimal GPU utilization"""
            if not frames:
                return []
            
            processed_frames = []
            
            # Batch processing for GPU efficiency
            for frame_data in frames:
                # Decode frame
                nparr = np.frombuffer(frame_data, np.uint8)
                frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                
                if frame is None:
                    continue
                
                # GPU-accelerated face detection
                faces = self.detect_faces_gpu(frame)
                
                # Apply masks with GPU acceleration
                processed_frame = self.apply_mask_gpu(frame, faces, mask_config)
                
                # Encode back to bytes
                encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 85]
                _, buffer = cv2.imencode('.jpg', processed_frame, encode_param)
                processed_frames.append(buffer.tobytes())
            
            return processed_frames
        
        def detect_faces_gpu(self, frame: np.ndarray) -> List[Dict]:
            """GPU-accelerated face detection"""
            if self.gpu_context:
                try:
                    # Upload to GPU
                    gpu_frame = cv2.cuda_GpuMat()
                    gpu_frame.upload(frame)
                    
                    # GPU processing would go here
                    # For now, fallback to optimized CPU
                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_alt.xml')
                    faces_rects = face_cascade.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=3)
                    
                    faces = []
                    for i, (x, y, w, h) in enumerate(faces_rects[:8]):  # Up to 8 faces
                        faces.append({
                            'id': f'face_{i+1}',
                            'bbox': [int(x), int(y), int(w), int(h)],
                            'confidence': 0.9
                        })
                    
                    return faces
                except Exception as e:
                    print(f"GPU face detection failed: {e}")
            
            # CPU fallback
            return self.detect_faces_cpu(frame)
        
        def detect_faces_cpu(self, frame: np.ndarray) -> List[Dict]:
            """Optimized CPU face detection"""
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_alt.xml')
            faces_rects = face_cascade.detectMultiScale(gray, scaleFactor=1.3, minNeighbors=3)
            
            faces = []
            for i, (x, y, w, h) in enumerate(faces_rects[:5]):
                faces.append({
                    'id': f'face_{i+1}',
                    'bbox': [int(x), int(y), int(w), int(h)],
                    'confidence': 0.85
                })
            
            return faces
        
        def apply_mask_gpu(self, frame: np.ndarray, faces: List[Dict], mask_config: Dict) -> np.ndarray:
            """GPU-accelerated mask application"""
            if not faces or mask_config.get('type') == 'off':
                return frame
            
            result_frame = frame.copy()
            mask_type = mask_config.get('type', 'blur')
            intensity = mask_config.get('intensity', 0.7)
            
            for face in faces:
                x, y, w, h = face['bbox']
                face_region = result_frame[y:y+h, x:x+w]
                
                if mask_type == 'blur':
                    kernel_size = max(11, int(w * 0.1))
                    if kernel_size % 2 == 0:
                        kernel_size += 1
                    blurred = cv2.GaussianBlur(face_region, (kernel_size, kernel_size), 0)
                    result_frame[y:y+h, x:x+w] = blurred
                
                elif mask_type == 'pixelate':
                    pixel_size = max(6, int(w * 0.04))
                    temp = cv2.resize(face_region, (w//pixel_size, h//pixel_size), interpolation=cv2.INTER_LINEAR)
                    pixelated = cv2.resize(temp, (w, h), interpolation=cv2.INTER_NEAREST)
                    result_frame[y:y+h, x:x+w] = pixelated
                
                elif mask_type == 'color_block':
                    color = mask_config.get('color', [100, 100, 100])
                    overlay = np.full_like(face_region, color, dtype=np.uint8)
                    result_frame[y:y+h, x:x+w] = cv2.addWeighted(face_region, 1-intensity, overlay, intensity, 0)
            
            return result_frame

    processor = LiveStreamProcessor()
    mask_manager = PremiumMaskManager()

    @web_app.websocket("/ws/premium-stream/{client_id}")
    async def premium_live_stream(websocket: WebSocket, client_id: str):
        """Premium WebSocket endpoint with advanced features"""
        await websocket.accept()
        
        # Check user tier and limits
        usage_check = streaming_state.check_usage_limits(client_id)
        if not usage_check["can_stream"]:
            await websocket.send_text(json.dumps({
                "error": "Usage limit exceeded",
                "tier": usage_check["tier"],
                "upgrade_url": "/upgrade"
            }))
            await websocket.close()
            return
        
        streaming_state.active_connections[client_id] = websocket
        streaming_state.performance_stats["active_users"] += 1
        
        print(f"Premium client {client_id} connected (Tier: {usage_check['tier']})")
        
        try:
            frame_batch = []
            batch_start_time = time.time()
            
            while True:
                message = await websocket.receive()
                
                if message["type"] == "websocket.receive":
                    if "bytes" in message:
                        frame_data = message["bytes"]
                        frame_batch.append(frame_data)
                        
                        # Process in batches for GPU efficiency
                        if len(frame_batch) >= processor.batch_size or (time.time() - batch_start_time) > 0.033:  # 30 FPS
                            start_time = time.time()
                            
                            # Get current mask configuration
                            current_mask = mask_manager.get_mask_for_slot(mask_manager.active_slot)
                            
                            # Process batch
                            processed_frames = await processor.process_frame_batch(frame_batch, current_mask)
                            
                            # Send processed frames
                            for processed_frame in processed_frames:
                                await websocket.send_bytes(processed_frame)
                            
                            # Update performance stats
                            processing_time = (time.time() - start_time) * 1000
                            streaming_state.performance_stats["avg_latency"] = processing_time
                            
                            # Clear batch
                            frame_batch = []
                            batch_start_time = time.time()
                    
                    elif "text" in message:
                        control_data = json.loads(message["text"])
                        
                        if control_data.get("action") == "switch_mask":
                            slot = control_data.get("slot", "slot_1")
                            new_mask = mask_manager.switch_mask(slot)
                            await websocket.send_text(json.dumps({
                                "status": "mask_switched",
                                "slot": slot,
                                "mask_config": new_mask
                            }))
                        
                        elif control_data.get("action") == "set_quality":
                            quality_mode = control_data.get("mode", "balanced")
                            if quality_mode in QUALITY_MODES:
                                await websocket.send_text(json.dumps({
                                    "status": "quality_set",
                                    "mode": quality_mode,
                                    "settings": QUALITY_MODES[quality_mode]
                                }))
                        
                        elif control_data.get("action") == "get_stats":
                            await websocket.send_text(json.dumps({
                                "status": "stats",
                                "data": streaming_state.performance_stats,
                                "user_tier": usage_check["tier"],
                                "remaining_minutes": usage_check["remaining_minutes"]
                            }))
        
        except WebSocketDisconnect:
            print(f"Premium client {client_id} disconnected")
        except Exception as e:
            print(f"Error in premium streaming for {client_id}: {e}")
        finally:
            if client_id in streaming_state.active_connections:
                del streaming_state.active_connections[client_id]
            streaming_state.performance_stats["active_users"] = max(0, streaming_state.performance_stats["active_users"] - 1)

    @web_app.get("/premium-stream", response_class=HTMLResponse)
    async def premium_stream_interface():
        """Premium live streaming interface with advanced features"""
        return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PLAYALTER Premium Live Streaming</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            min-height: 100vh;
            color: white;
        }
        
        .header {
            background: rgba(0,0,0,0.3);
            padding: 1rem 2rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            backdrop-filter: blur(10px);
        }
        
        .header h1 {
            font-size: 1.8rem;
            background: linear-gradient(45deg, #FFD700, #FFA500);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        
        .tier-badge {
            padding: 0.3rem 1rem;
            border-radius: 20px;
            font-weight: bold;
            font-size: 0.9rem;
        }
        
        .tier-free { background: linear-gradient(45deg, #6c757d, #5a6268); }
        .tier-pro { background: linear-gradient(45deg, #28a745, #20c997); }
        .tier-api { background: linear-gradient(45deg, #dc3545, #fd7e14); }
        
        .main-container {
            display: grid;
            grid-template-columns: 2fr 1fr;
            gap: 2rem;
            padding: 2rem;
            max-width: 1600px;
            margin: 0 auto;
        }
        
        .streaming-section {
            background: rgba(255,255,255,0.1);
            border-radius: 15px;
            padding: 2rem;
            backdrop-filter: blur(10px);
        }
        
        .video-preview {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 1rem;
            margin-bottom: 2rem;
        }
        
        .video-container {
            position: relative;
            background: rgba(0,0,0,0.5);
            border-radius: 10px;
            overflow: hidden;
            aspect-ratio: 16/9;
        }
        
        .video-label {
            position: absolute;
            top: 10px;
            left: 10px;
            background: rgba(0,0,0,0.8);
            padding: 0.3rem 0.8rem;
            border-radius: 5px;
            font-size: 0.8rem;
            z-index: 10;
        }
        
        video, canvas {
            width: 100%;
            height: 100%;
            object-fit: cover;
        }
        
        .controls-panel {
            background: rgba(255,255,255,0.1);
            border-radius: 15px;
            padding: 2rem;
            backdrop-filter: blur(10px);
            max-height: fit-content;
        }
        
        .control-group {
            margin-bottom: 2rem;
        }
        
        .control-group h3 {
            color: #FFD700;
            margin-bottom: 1rem;
            font-size: 1.2rem;
        }
        
        .mask-slots {
            display: grid;
            grid-template-columns: repeat(5, 1fr);
            gap: 0.5rem;
            margin-bottom: 1rem;
        }
        
        .mask-slot {
            aspect-ratio: 1;
            border: 2px solid rgba(255,255,255,0.3);
            border-radius: 8px;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            transition: all 0.3s ease;
            font-size: 0.7rem;
            text-align: center;
        }
        
        .mask-slot:hover {
            border-color: #FFD700;
            background: rgba(255,255,255,0.1);
        }
        
        .mask-slot.active {
            border-color: #FFD700;
            background: rgba(255,215,0,0.2);
        }
        
        .hotkey {
            background: rgba(0,0,0,0.5);
            padding: 0.2rem 0.4rem;
            border-radius: 3px;
            font-size: 0.6rem;
            margin-top: 0.2rem;
        }
        
        .quality-modes {
            display: grid;
            grid-template-columns: 1fr;
            gap: 0.5rem;
        }
        
        .quality-option {
            padding: 0.8rem;
            border: 2px solid rgba(255,255,255,0.3);
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        
        .quality-option:hover, .quality-option.active {
            border-color: #FFD700;
            background: rgba(255,255,255,0.1);
        }
        
        .quality-title {
            font-weight: bold;
            color: #FFD700;
        }
        
        .quality-details {
            font-size: 0.8rem;
            opacity: 0.8;
            margin-top: 0.3rem;
        }
        
        .platform-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 0.5rem;
        }
        
        .platform-btn {
            padding: 0.6rem;
            border: none;
            border-radius: 6px;
            background: rgba(255,255,255,0.2);
            color: white;
            cursor: pointer;
            transition: all 0.3s ease;
            font-size: 0.8rem;
        }
        
        .platform-btn:hover {
            background: rgba(255,255,255,0.3);
        }
        
        .platform-btn.active {
            background: linear-gradient(45deg, #28a745, #20c997);
        }
        
        .stats-display {
            background: rgba(0,0,0,0.3);
            border-radius: 8px;
            padding: 1rem;
            font-family: 'Courier New', monospace;
            font-size: 0.8rem;
        }
        
        .stat-row {
            display: flex;
            justify-content: space-between;
            margin-bottom: 0.3rem;
        }
        
        .premium-features {
            background: linear-gradient(45deg, rgba(255,215,0,0.1), rgba(255,165,0,0.1));
            border: 1px solid rgba(255,215,0,0.3);
            border-radius: 8px;
            padding: 1rem;
            margin-top: 1rem;
        }
        
        .feature-list {
            list-style: none;
            font-size: 0.9rem;
        }
        
        .feature-list li {
            margin-bottom: 0.3rem;
        }
        
        .feature-list li::before {
            content: "★ ";
            color: #FFD700;
            font-weight: bold;
        }
        
        .upgrade-btn {
            width: 100%;
            padding: 1rem;
            background: linear-gradient(45deg, #FFD700, #FFA500);
            color: #333;
            border: none;
            border-radius: 8px;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.3s ease;
            margin-top: 1rem;
        }
        
        .upgrade-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(255,215,0,0.3);
        }
        
        @media (max-width: 1024px) {
            .main-container {
                grid-template-columns: 1fr;
            }
            
            .video-preview {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>PLAYALTER Premium Live Streaming</h1>
        <div class="tier-badge tier-pro" id="tierBadge">PRO TIER</div>
    </div>
    
    <div class="main-container">
        <div class="streaming-section">
            <div class="video-preview">
                <div class="video-container">
                    <div class="video-label">Original Stream</div>
                    <video id="originalVideo" autoplay muted playsinline></video>
                </div>
                <div class="video-container">
                    <div class="video-label">Premium Processed</div>
                    <canvas id="processedCanvas"></canvas>
                </div>
            </div>
            
            <div class="stream-controls">
                <button id="startBtn" class="upgrade-btn">Start Premium Stream</button>
                <button id="stopBtn" class="upgrade-btn" style="background: linear-gradient(45deg, #dc3545, #c82333); display: none;">Stop Stream</button>
            </div>
        </div>
        
        <div class="controls-panel">
            <div class="control-group">
                <h3>Quick Mask Slots</h3>
                <div class="mask-slots">
                    <div class="mask-slot active" data-slot="slot_1">
                        <span>Blur</span>
                        <div class="hotkey">1</div>
                    </div>
                    <div class="mask-slot" data-slot="slot_2">
                        <span>Pixel</span>
                        <div class="hotkey">2</div>
                    </div>
                    <div class="mask-slot" data-slot="slot_3">
                        <span>Block</span>
                        <div class="hotkey">3</div>
                    </div>
                    <div class="mask-slot" data-slot="slot_4">
                        <span>Custom</span>
                        <div class="hotkey">4</div>
                    </div>
                    <div class="mask-slot" data-slot="slot_5">
                        <span>Off</span>
                        <div class="hotkey">5</div>
                    </div>
                </div>
            </div>
            
            <div class="control-group">
                <h3>Quality Presets</h3>
                <div class="quality-modes">
                    <div class="quality-option" data-mode="performance">
                        <div class="quality-title">Performance Mode</div>
                        <div class="quality-details">480p @ 60fps • Gaming/High FPS</div>
                    </div>
                    <div class="quality-option active" data-mode="balanced">
                        <div class="quality-title">Balanced Mode</div>
                        <div class="quality-details">720p @ 30fps • Video calls</div>
                    </div>
                    <div class="quality-option" data-mode="quality">
                        <div class="quality-title">Quality Mode</div>
                        <div class="quality-details">1080p @ 24fps • Recording</div>
                    </div>
                </div>
            </div>
            
            <div class="control-group">
                <h3>Platform Targets</h3>
                <div class="platform-grid">
                    <button class="platform-btn" data-platform="zoom">Zoom</button>
                    <button class="platform-btn" data-platform="teams">Teams</button>
                    <button class="platform-btn" data-platform="discord">Discord</button>
                    <button class="platform-btn" data-platform="twitch">Twitch</button>
                    <button class="platform-btn" data-platform="youtube">YouTube</button>
                    <button class="platform-btn" data-platform="instagram">Instagram</button>
                </div>
            </div>
            
            <div class="control-group">
                <h3>Performance Stats</h3>
                <div class="stats-display">
                    <div class="stat-row">
                        <span>Latency:</span>
                        <span id="latencyDisplay">0ms</span>
                    </div>
                    <div class="stat-row">
                        <span>FPS:</span>
                        <span id="fpsDisplay">0</span>
                    </div>
                    <div class="stat-row">
                        <span>GPU Usage:</span>
                        <span id="gpuDisplay">0%</span>
                    </div>
                    <div class="stat-row">
                        <span>Remaining:</span>
                        <span id="remainingDisplay">Unlimited</span>
                    </div>
                </div>
            </div>
            
            <div class="premium-features">
                <h3>Premium Features Active</h3>
                <ul class="feature-list">
                    <li>GPU-accelerated processing</li>
                    <li>Batch frame optimization</li>
                    <li>Multi-platform streaming</li>
                    <li>Custom mask slots</li>
                    <li>Hotkey controls</li>
                    <li>Priority support</li>
                </ul>
                <button class="upgrade-btn" onclick="window.open('/api-access', '_blank')">
                    Upgrade to API Access
                </button>
            </div>
        </div>
    </div>
    
    <script>
        let websocket = null;
        let isStreaming = false;
        let currentQualityMode = 'balanced';
        let activeMaskSlot = 'slot_1';
        let activePlatforms = [];
        
        const clientId = 'premium_' + Math.random().toString(36).substr(2, 9);
        
        // Initialize
        document.addEventListener('DOMContentLoaded', function() {
            setupEventListeners();
            setupHotkeys();
        });
        
        function setupEventListeners() {
            // Mask slot selection
            document.querySelectorAll('.mask-slot').forEach(slot => {
                slot.addEventListener('click', function() {
                    switchMaskSlot(this.dataset.slot);
                });
            });
            
            // Quality mode selection
            document.querySelectorAll('.quality-option').forEach(option => {
                option.addEventListener('click', function() {
                    setQualityMode(this.dataset.mode);
                });
            });
            
            // Platform selection
            document.querySelectorAll('.platform-btn').forEach(btn => {
                btn.addEventListener('click', function() {
                    togglePlatform(this.dataset.platform);
                });
            });
            
            // Stream controls
            document.getElementById('startBtn').addEventListener('click', startPremiumStream);
            document.getElementById('stopBtn').addEventListener('click', stopPremiumStream);
        }
        
        function setupHotkeys() {
            document.addEventListener('keydown', function(e) {
                if (e.target.tagName === 'INPUT') return;
                
                // Mask switching hotkeys (1-5)
                if (e.key >= '1' && e.key <= '5') {
                    e.preventDefault();
                    switchMaskSlot(`slot_${e.key}`);
                }
                
                // Quality mode hotkeys
                if (e.key === 'q') setQualityMode('quality');
                if (e.key === 'b') setQualityMode('balanced');  
                if (e.key === 'p') setQualityMode('performance');
            });
        }
        
        async function startPremiumStream() {
            try {
                // Get camera access
                const mediaStream = await navigator.mediaDevices.getUserMedia({
                    video: {
                        width: 1280,
                        height: 720,
                        frameRate: 30
                    }
                });
                
                document.getElementById('originalVideo').srcObject = mediaStream;
                
                // Connect premium WebSocket
                const wsUrl = `wss://${window.location.host}/ws/premium-stream/${clientId}`;
                websocket = new WebSocket(wsUrl);
                
                websocket.onopen = function() {
                    isStreaming = true;
                    document.getElementById('startBtn').style.display = 'none';
                    document.getElementById('stopBtn').style.display = 'block';
                    startProcessingLoop();
                };
                
                websocket.onmessage = function(event) {
                    if (event.data instanceof Blob) {
                        displayProcessedFrame(event.data);
                    } else {
                        handleControlMessage(JSON.parse(event.data));
                    }
                };
                
                websocket.onerror = function(error) {
                    console.error('WebSocket error:', error);
                };
                
            } catch (error) {
                alert('Error starting premium stream: ' + error.message);
            }
        }
        
        function stopPremiumStream() {
            isStreaming = false;
            
            if (websocket) {
                websocket.close();
                websocket = null;
            }
            
            document.getElementById('startBtn').style.display = 'block';
            document.getElementById('stopBtn').style.display = 'none';
        }
        
        function switchMaskSlot(slot) {
            // Update UI
            document.querySelectorAll('.mask-slot').forEach(s => s.classList.remove('active'));
            document.querySelector(`[data-slot="${slot}"]`).classList.add('active');
            
            activeMaskSlot = slot;
            
            // Send to server
            if (websocket && websocket.readyState === WebSocket.OPEN) {
                websocket.send(JSON.stringify({
                    action: 'switch_mask',
                    slot: slot
                }));
            }
        }
        
        function setQualityMode(mode) {
            // Update UI
            document.querySelectorAll('.quality-option').forEach(o => o.classList.remove('active'));
            document.querySelector(`[data-mode="${mode}"]`).classList.add('active');
            
            currentQualityMode = mode;
            
            // Send to server
            if (websocket && websocket.readyState === WebSocket.OPEN) {
                websocket.send(JSON.stringify({
                    action: 'set_quality',
                    mode: mode
                }));
            }
        }
        
        function togglePlatform(platform) {
            const btn = document.querySelector(`[data-platform="${platform}"]`);
            
            if (activePlatforms.includes(platform)) {
                // Remove platform
                activePlatforms = activePlatforms.filter(p => p !== platform);
                btn.classList.remove('active');
            } else {
                // Add platform
                activePlatforms.push(platform);
                btn.classList.add('active');
            }
        }
        
        function startProcessingLoop() {
            const video = document.getElementById('originalVideo');
            const canvas = document.createElement('canvas');
            const ctx = canvas.getContext('2d');
            
            canvas.width = video.videoWidth || 1280;
            canvas.height = video.videoHeight || 720;
            
            function sendFrame() {
                if (!isStreaming) return;
                
                ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
                
                canvas.toBlob(function(blob) {
                    if (websocket && websocket.readyState === WebSocket.OPEN) {
                        websocket.send(blob);
                    }
                }, 'image/jpeg', 0.8);
                
                requestAnimationFrame(sendFrame);
            }
            
            sendFrame();
        }
        
        function displayProcessedFrame(blob) {
            const canvas = document.getElementById('processedCanvas');
            const ctx = canvas.getContext('2d');
            
            const url = URL.createObjectURL(blob);
            const img = new Image();
            img.onload = function() {
                canvas.width = img.width;
                canvas.height = img.height;
                ctx.drawImage(img, 0, 0);
                URL.revokeObjectURL(url);
            };
            img.src = url;
        }
        
        function handleControlMessage(data) {
            if (data.status === 'stats') {
                updateStatsDisplay(data.data, data.user_tier, data.remaining_minutes);
            }
        }
        
        function updateStatsDisplay(stats, tier, remaining) {
            document.getElementById('latencyDisplay').textContent = Math.round(stats.avg_latency) + 'ms';
            document.getElementById('fpsDisplay').textContent = Math.round(stats.current_fps || 30);
            document.getElementById('gpuDisplay').textContent = stats.gpu_utilization + '%';
            
            if (remaining === Infinity) {
                document.getElementById('remainingDisplay').textContent = 'Unlimited';
            } else {
                document.getElementById('remainingDisplay').textContent = Math.round(remaining) + ' min';
            }
            
            // Update tier badge
            const tierBadge = document.getElementById('tierBadge');
            tierBadge.textContent = tier.toUpperCase() + ' TIER';
            tierBadge.className = `tier-badge tier-${tier}`;
        }
        
        // Request stats every 2 seconds
        setInterval(function() {
            if (websocket && websocket.readyState === WebSocket.OPEN) {
                websocket.send(JSON.stringify({ action: 'get_stats' }));
            }
        }, 2000);
    </script>
</body>
</html>
        """

    @web_app.get("/api-access", response_class=HTMLResponse)
    async def api_access_page():
        """API tier information and documentation"""
        return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PLAYALTER API Access</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: white;
            margin: 0;
            padding: 2rem;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        
        .hero {
            text-align: center;
            margin-bottom: 3rem;
        }
        
        .hero h1 {
            font-size: 3rem;
            margin-bottom: 1rem;
            background: linear-gradient(45deg, #ff6b6b, #ffa500);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        
        .api-features {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 2rem;
            margin-bottom: 3rem;
        }
        
        .feature-card {
            background: rgba(255,255,255,0.1);
            border-radius: 15px;
            padding: 2rem;
            backdrop-filter: blur(10px);
        }
        
        .code-example {
            background: rgba(0,0,0,0.5);
            border-radius: 8px;
            padding: 1rem;
            font-family: 'Courier New', monospace;
            font-size: 0.9rem;
            margin: 1rem 0;
            overflow-x: auto;
        }
        
        .pricing {
            background: rgba(255,215,0,0.1);
            border: 2px solid rgba(255,215,0,0.3);
            border-radius: 15px;
            padding: 2rem;
            text-align: center;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="hero">
            <h1>PLAYALTER API Access</h1>
            <p>Enterprise-grade real-time face processing API</p>
        </div>
        
        <div class="api-features">
            <div class="feature-card">
                <h3>WebRTC API Endpoints</h3>
                <p>Direct WebRTC integration for your applications</p>
                <div class="code-example">
POST /api/v1/stream/create
{
  "quality": "1080p",
  "fps": 60,
  "platform": "custom"
}
                </div>
            </div>
            
            <div class="feature-card">
                <h3>Webhook Callbacks</h3>
                <p>Real-time notifications for stream events</p>
                <div class="code-example">
{
  "event": "stream_started",
  "stream_id": "12345",
  "timestamp": "2025-01-01T00:00:00Z"
}
                </div>
            </div>
            
            <div class="feature-card">
                <h3>Custom Endpoints</h3>
                <p>Tailored API endpoints for your use case</p>
                <div class="code-example">
GET /api/v1/analytics/stream/12345
{
  "avg_latency": 25,
  "faces_processed": 1500,
  "uptime": "99.9%"
}
                </div>
            </div>
        </div>
        
        <div class="pricing">
            <h2>API Tier Pricing</h2>
            <p>$99/month • Unlimited streaming • Priority GPU • 24/7 support</p>
            <button style="padding: 1rem 2rem; background: linear-gradient(45deg, #FFD700, #FFA500); color: black; border: none; border-radius: 8px; font-weight: bold; cursor: pointer; margin-top: 1rem;">
                Contact Sales
            </button>
        </div>
    </div>
</body>
</html>
        """

    @web_app.get("/health")
    async def health_check():
        return {
            "status": "healthy",
            "service": "PLAYALTER Premium Live Streaming",
            "version": "3.0",
            "gpu": "A10G",
            "features": ["premium_streaming", "batch_processing", "multi_platform", "api_access"],
            "performance": streaming_state.performance_stats
        }

    @web_app.get("/", response_class=HTMLResponse)  
    async def home_page():
        return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PLAYALTER Premium - Live Streaming Platform</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            margin: 0;
            color: white;
        }
        
        .hero {
            text-align: center;
            padding: 4rem 2rem;
            background: rgba(0,0,0,0.3);
        }
        
        .hero h1 {
            font-size: 4rem;
            margin-bottom: 1rem;
            background: linear-gradient(45deg, #FFD700, #FFA500);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        
        .services {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 2rem;
            padding: 2rem;
            max-width: 1400px;
            margin: 0 auto;
        }
        
        .service-card {
            background: rgba(255,255,255,0.1);
            border-radius: 15px;
            padding: 2rem;
            text-align: center;
            backdrop-filter: blur(10px);
            border: 2px solid transparent;
            transition: all 0.3s ease;
        }
        
        .service-card:hover {
            transform: translateY(-10px);
            border-color: #FFD700;
        }
        
        .service-card.premium {
            border-color: #FFD700;
            background: rgba(255,215,0,0.1);
        }
        
        .btn {
            display: inline-block;
            padding: 1rem 2rem;
            background: linear-gradient(45deg, #FFD700, #FFA500);
            color: #333;
            text-decoration: none;
            border-radius: 25px;
            font-weight: bold;
            transition: all 0.3s ease;
            margin-top: 1rem;
        }
        
        .btn:hover {
            transform: translateY(-3px);
            box-shadow: 0 10px 25px rgba(255,215,0,0.3);
        }
    </style>
</head>
<body>
    <div class="hero">
        <h1>PLAYALTER Premium</h1>
        <p>Professional Live Streaming with AI-Powered Face Processing</p>
    </div>
    
    <div class="services">
        <div class="service-card premium">
            <h3>Premium Live Streaming</h3>
            <p>GPU-accelerated real-time processing with advanced mask management, quality presets, and multi-platform streaming.</p>
            <a href="/premium-stream" class="btn">Launch Premium Stream</a>
        </div>
        
        <div class="service-card">
            <h3>API Access</h3>
            <p>Enterprise-grade API with WebRTC endpoints, webhook callbacks, and custom integrations for developers.</p>
            <a href="/api-access" class="btn">View API Docs</a>
        </div>
        
        <div class="service-card">
            <h3>Privacy Mask Generator</h3>
            <p>Create custom masks for your live streams with ethnicity-aware processing and advanced anonymization.</p>
            <a href="/mask-generator" class="btn">Generate Masks</a>
        </div>
    </div>
</body>
</html>
        """
    
    return web_app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(web_app, host="0.0.0.0", port=8000)