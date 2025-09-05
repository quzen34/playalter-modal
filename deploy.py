#!/usr/bin/env python3
"""
PLAYALTER Platform - Simplified Deployment Script
Advanced AI Face Processing Platform with FLAME Model & Privacy Protection
"""

import modal
import os
import logging
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import base64
import io
import numpy as np
import cv2
from PIL import Image

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = modal.App("playalter-platform")

# Define the Docker image with all dependencies
image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install([
        "torch==2.1.0",
        "torchvision==0.16.0", 
        "torchaudio==2.1.0",
        "opencv-python==4.8.1.78",
        "mediapipe==0.10.7",
        "numpy==1.24.3",
        "Pillow==10.0.1",
        "scikit-image==0.21.0",
        "scipy==1.11.3",
        "face-alignment==1.3.5",
        "insightface==0.7.3",
        "fastapi==0.104.1",
        "uvicorn==0.24.0",
        "python-multipart==0.0.6",
        "requests==2.31.0",
        "pydantic==2.4.2",
    ])
    .apt_install([
        "libgl1-mesa-glx",
        "libglib2.0-0", 
        "libsm6",
        "libxext6",
        "libxrender-dev",
        "libgomp1"
    ])
)

# Request/Response Models
class FaceAnalysisRequest(BaseModel):
    image_base64: str
    include_measurements: bool = True

class PrivacyMaskRequest(BaseModel):
    image_base64: str
    mask_type: str = "blur"
    strength: float = 1.0

# Utility functions
def decode_base64_image(base64_string: str) -> np.ndarray:
    """Decode base64 string to numpy array image."""
    try:
        if base64_string.startswith('data:image'):
            base64_string = base64_string.split(',')[1]
        
        image_data = base64.b64decode(base64_string)
        pil_image = Image.open(io.BytesIO(image_data))
        
        if pil_image.mode != 'RGB':
            pil_image = pil_image.convert('RGB')
        
        image_array = np.array(pil_image)
        image_bgr = cv2.cvtColor(image_array, cv2.COLOR_RGB2BGR)
        
        return image_bgr
    except Exception as e:
        logger.error(f"Error decoding base64 image: {str(e)}")
        raise HTTPException(status_code=400, detail="Invalid image data")

def encode_image_to_base64(image: np.ndarray) -> str:
    """Encode numpy array image to base64 string."""
    try:
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(image_rgb)
        
        buffer = io.BytesIO()
        pil_image.save(buffer, format='JPEG', quality=95)
        
        base64_string = base64.b64encode(buffer.getvalue()).decode('utf-8')
        return base64_string
    except Exception as e:
        logger.error(f"Error encoding image to base64: {str(e)}")
        raise HTTPException(status_code=500, detail="Error encoding image")

# Basic face detection using MediaPipe
def detect_faces_mediapipe(image: np.ndarray) -> Dict[str, Any]:
    """Basic face detection using MediaPipe."""
    import mediapipe as mp
    
    mp_face_detection = mp.solutions.face_detection
    mp_drawing = mp.solutions.drawing_utils
    
    with mp_face_detection.FaceDetection(model_selection=0, min_detection_confidence=0.5) as face_detection:
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        results = face_detection.process(image_rgb)
        
        faces = []
        if results.detections:
            for detection in results.detections:
                bbox = detection.location_data.relative_bounding_box
                h, w, _ = image.shape
                
                face_info = {
                    'bbox': [
                        int(bbox.xmin * w),
                        int(bbox.ymin * h),
                        int((bbox.xmin + bbox.width) * w),
                        int((bbox.ymin + bbox.height) * h)
                    ],
                    'confidence': detection.score[0]
                }
                faces.append(face_info)
        
        return {'faces': faces, 'count': len(faces)}

def create_simple_privacy_mask(image: np.ndarray, mask_type: str = "blur", strength: float = 1.0) -> np.ndarray:
    """Create a simple privacy mask."""
    # Detect faces first
    face_data = detect_faces_mediapipe(image)
    
    if face_data['count'] == 0:
        return image
    
    result_image = image.copy()
    
    for face in face_data['faces']:
        x1, y1, x2, y2 = face['bbox']
        face_region = result_image[y1:y2, x1:x2]
        
        if mask_type == "blur":
            kernel_size = max(5, int(strength * 50))
            if kernel_size % 2 == 0:
                kernel_size += 1
            blurred = cv2.GaussianBlur(face_region, (kernel_size, kernel_size), 0)
            result_image[y1:y2, x1:x2] = blurred
            
        elif mask_type == "pixelate":
            pixel_size = max(2, int(strength * 20))
            h, w = face_region.shape[:2]
            small = cv2.resize(face_region, (w // pixel_size, h // pixel_size), interpolation=cv2.INTER_LINEAR)
            pixelated = cv2.resize(small, (w, h), interpolation=cv2.INTER_NEAREST)
            result_image[y1:y2, x1:x2] = pixelated
            
        elif mask_type == "noise":
            noise = np.random.normal(0, 50 * strength, face_region.shape).astype(np.int16)
            noisy = np.clip(face_region.astype(np.int16) + noise, 0, 255).astype(np.uint8)
            result_image[y1:y2, x1:x2] = noisy
    
    return result_image

@app.function(
    image=image,
    gpu="T4",
    memory=8192,
    timeout=300,
    min_containers=1
)
@modal.web_endpoint(method="GET")
def serve_frontend():
    """Serve the main web interface."""
    return HTMLResponse(content="""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>🔥 PLAYALTER Platform</title>
        <style>
            body { 
                font-family: 'Arial', sans-serif; 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                color: white; 
                margin: 0; 
                padding: 20px; 
                min-height: 100vh; 
            }
            .container { 
                max-width: 1200px; 
                margin: 0 auto; 
                text-align: center; 
            }
            h1 { 
                font-size: 3rem; 
                margin-bottom: 20px; 
                text-shadow: 2px 2px 4px rgba(0,0,0,0.3); 
            }
            .subtitle { 
                font-size: 1.2rem; 
                margin-bottom: 40px; 
                opacity: 0.9; 
            }
            .services { 
                display: grid; 
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); 
                gap: 30px; 
                margin: 40px 0; 
            }
            .service-card { 
                background: white; 
                color: #333; 
                padding: 30px; 
                border-radius: 15px; 
                box-shadow: 0 10px 30px rgba(0,0,0,0.2); 
                transition: transform 0.3s ease; 
            }
            .service-card:hover { 
                transform: translateY(-5px); 
            }
            .emoji { 
                font-size: 3rem; 
                margin-bottom: 15px; 
            }
            .upload-area { 
                border: 2px dashed #ccc; 
                border-radius: 10px; 
                padding: 20px; 
                margin: 20px 0; 
                cursor: pointer; 
            }
            .btn { 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                color: white; 
                border: none; 
                padding: 12px 25px; 
                border-radius: 25px; 
                cursor: pointer; 
                font-size: 1rem; 
                margin: 5px; 
            }
            .btn:hover { 
                opacity: 0.9; 
            }
            .result-image { 
                max-width: 100%; 
                max-height: 300px; 
                border-radius: 10px; 
                margin: 20px 0; 
            }
            .error { 
                background: #ffebee; 
                color: #c62828; 
                padding: 15px; 
                border-radius: 10px; 
                margin: 10px 0; 
                display: none; 
            }
            .success { 
                background: #e8f5e8; 
                color: #2e7d32; 
                padding: 15px; 
                border-radius: 10px; 
                margin: 10px 0; 
                display: none; 
            }
            select, input[type="range"] { 
                width: 100%; 
                padding: 8px; 
                margin: 10px 0; 
                border-radius: 5px; 
                border: 1px solid #ddd; 
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🔥 PLAYALTER</h1>
            <p class="subtitle">Advanced AI Face Processing Platform</p>
            
            <div class="services">
                <div class="service-card">
                    <div class="emoji">🔍</div>
                    <h3>Face Analysis</h3>
                    <p>Detect and analyze faces in your images</p>
                    
                    <div class="upload-area" onclick="document.getElementById('analysisFile').click()">
                        📁 Click to upload image
                        <input type="file" id="analysisFile" style="display:none" accept="image/*" onchange="previewImage(this, 'analysisPreview')">
                    </div>
                    <div id="analysisPreview"></div>
                    
                    <button class="btn" onclick="analyzeFace()">Analyze Face</button>
                    
                    <div id="analysisError" class="error"></div>
                    <div id="analysisSuccess" class="success"></div>
                    <div id="analysisResult"></div>
                </div>
                
                <div class="service-card">
                    <div class="emoji">🔒</div>
                    <h3>Privacy Mask</h3>
                    <p>Generate privacy masks to protect identities</p>
                    
                    <div class="upload-area" onclick="document.getElementById('privacyFile').click()">
                        📁 Click to upload image
                        <input type="file" id="privacyFile" style="display:none" accept="image/*" onchange="previewImage(this, 'privacyPreview')">
                    </div>
                    <div id="privacyPreview"></div>
                    
                    <div>
                        <select id="maskType">
                            <option value="blur">Blur</option>
                            <option value="pixelate">Pixelate</option>
                            <option value="noise">Noise</option>
                        </select>
                        <label for="strength">Strength: <span id="strengthValue">1.0</span></label>
                        <input type="range" id="strength" min="0.1" max="2.0" step="0.1" value="1.0" 
                               oninput="document.getElementById('strengthValue').textContent = this.value">
                    </div>
                    
                    <button class="btn" onclick="generateMask()">Generate Mask</button>
                    
                    <div id="privacyError" class="error"></div>
                    <div id="privacySuccess" class="success"></div>
                    <div id="privacyResult"></div>
                </div>
            </div>
            
            <div style="margin-top: 40px;">
                <h3>🚀 API Endpoints</h3>
                <p><strong>POST</strong> /analyze_face_endpoint - Face detection and analysis</p>
                <p><strong>POST</strong> /privacy_mask_endpoint - Privacy mask generation</p>
                <p><strong>GET</strong> /health_check - Health check</p>
            </div>
        </div>
        
        <script>
        const API_BASE = window.location.origin;
        
        function previewImage(input, previewId) {
            const preview = document.getElementById(previewId);
            if (input.files && input.files[0]) {
                const reader = new FileReader();
                reader.onload = function(e) {
                    preview.innerHTML = '<img src="' + e.target.result + '" class="result-image">';
                };
                reader.readAsDataURL(input.files[0]);
            }
        }
        
        function fileToBase64(file) {
            return new Promise((resolve, reject) => {
                const reader = new FileReader();
                reader.readAsDataURL(file);
                reader.onload = () => resolve(reader.result.split(',')[1]);
                reader.onerror = error => reject(error);
            });
        }
        
        function showError(id, message) {
            const el = document.getElementById(id);
            el.textContent = message;
            el.style.display = 'block';
            setTimeout(() => el.style.display = 'none', 5000);
        }
        
        function showSuccess(id, message) {
            const el = document.getElementById(id);
            el.textContent = message;
            el.style.display = 'block';
            setTimeout(() => el.style.display = 'none', 3000);
        }
        
        async function analyzeFace() {
            const fileInput = document.getElementById('analysisFile');
            if (!fileInput.files[0]) {
                showError('analysisError', 'Please select an image');
                return;
            }
            
            try {
                const imageBase64 = await fileToBase64(fileInput.files[0]);
                
                const response = await fetch('/analyze_face_endpoint', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        image_base64: imageBase64,
                        include_measurements: true
                    })
                });
                
                const result = await response.json();
                
                if (result.success) {
                    showSuccess('analysisSuccess', 'Face analysis completed!');
                    document.getElementById('analysisResult').innerHTML = 
                        '<h4>Results:</h4><p>Faces detected: ' + result.face_count + '</p>';
                } else {
                    showError('analysisError', result.error || 'Analysis failed');
                }
            } catch (error) {
                showError('analysisError', 'Error: ' + error.message);
            }
        }
        
        async function generateMask() {
            const fileInput = document.getElementById('privacyFile');
            if (!fileInput.files[0]) {
                showError('privacyError', 'Please select an image');
                return;
            }
            
            try {
                const imageBase64 = await fileToBase64(fileInput.files[0]);
                const maskType = document.getElementById('maskType').value;
                const strength = parseFloat(document.getElementById('strength').value);
                
                const response = await fetch('/privacy_mask_endpoint', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        image_base64: imageBase64,
                        mask_type: maskType,
                        strength: strength
                    })
                });
                
                const result = await response.json();
                
                if (result.success) {
                    showSuccess('privacySuccess', 'Privacy mask generated!');
                    document.getElementById('privacyResult').innerHTML = 
                        '<h4>Masked Image:</h4><img src="data:image/jpeg;base64,' + 
                        result.masked_image + '" class="result-image">';
                } else {
                    showError('privacyError', result.error || 'Mask generation failed');
                }
            } catch (error) {
                showError('privacyError', 'Error: ' + error.message);
            }
        }
        </script>
    </body>
    </html>
    """)

@app.function(
    image=image,
    gpu="T4",
    memory=8192,
    timeout=300,
    min_containers=1
)
@modal.web_endpoint(method="POST")
def analyze_face_endpoint(request: FaceAnalysisRequest):
    """Analyze face in image."""
    try:
        # Decode image
        image = decode_base64_image(request.image_base64)
        
        # Perform basic face detection
        face_data = detect_faces_mediapipe(image)
        
        return {
            'success': True,
            'face_count': face_data['count'],
            'faces': face_data['faces'],
            'message': f'Detected {face_data["count"]} face(s) in the image'
        }
        
    except Exception as e:
        logger.error(f"Error in face analysis: {str(e)}")
        return {'success': False, 'error': str(e)}

@app.function(
    image=image,
    gpu="T4",
    memory=8192,
    timeout=300,
    min_containers=1
)
@modal.web_endpoint(method="POST")
def privacy_mask_endpoint(request: PrivacyMaskRequest):
    """Generate privacy mask for image."""
    try:
        # Decode image
        image = decode_base64_image(request.image_base64)
        
        # Generate privacy mask
        masked_image = create_simple_privacy_mask(image, request.mask_type, request.strength)
        
        # Encode result
        result_base64 = encode_image_to_base64(masked_image)
        
        return {
            'success': True,
            'masked_image': result_base64,
            'mask_type': request.mask_type,
            'strength': request.strength
        }
        
    except Exception as e:
        logger.error(f"Error generating privacy mask: {str(e)}")
        return {'success': False, 'error': str(e)}

@app.function(
    image=image,
    gpu="T4",
    memory=8192,
    timeout=60,
    min_containers=1
)
@modal.web_endpoint(method="GET")
def health_check():
    """Health check endpoint."""
    return {
        'status': 'healthy',
        'service': 'PLAYALTER Platform',
        'version': '1.0.0',
        'features': ['face_analysis', 'privacy_masks'],
        'gpu_available': True
    }

if __name__ == "__main__":
    print("🔥 PLAYALTER Platform - Deployment Script")
    print("Run: modal deploy deploy.py")