import modal
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from PIL import Image, ImageDraw, ImageFilter
import io
import base64
import numpy as np
from typing import Optional
import cv2
import tempfile
import os

# Create Modal app
app = modal.App("playalter-platform")

# Define the image with required dependencies
image = modal.Image.debian_slim(python_version="3.11").pip_install(
    "fastapi",
    "pillow",
    "numpy",
    "opencv-python-headless",
    "python-multipart"
)

# Create FastAPI instance
web_app = FastAPI()

# Mock face swap processing
def mock_face_swap(source_image: Image.Image, target_image: Image.Image) -> Image.Image:
    """Mock face swap - blends two images with effects"""
    # Resize target to match source dimensions
    target_resized = target_image.resize(source_image.size, Image.Resampling.LANCZOS)
    
    # Create a simple blend with color effects
    blended = Image.blend(source_image, target_resized, alpha=0.3)
    
    # Add some effects to make it look processed
    blended = blended.filter(ImageFilter.SMOOTH_MORE)
    blended = blended.filter(ImageFilter.EDGE_ENHANCE)
    
    # Add a watermark to indicate processing
    draw = ImageDraw.Draw(blended)
    draw.text((10, 10), "PLAYALTER - Face Swapped", fill=(255, 255, 255, 128))
    
    return blended

# Privacy mask generator
def generate_privacy_mask(image: Image.Image, mask_type: str = "blur") -> Image.Image:
    """Generate privacy mask on image"""
    img_copy = image.copy()
    width, height = img_copy.size
    
    if mask_type == "blur":
        # Apply heavy blur to center region (simulating face area)
        mask = Image.new('L', (width, height), 0)
        draw = ImageDraw.Draw(mask)
        # Create elliptical mask in center
        center_x, center_y = width // 2, height // 3
        draw.ellipse([center_x - width//6, center_y - height//6, 
                     center_x + width//6, center_y + height//6], fill=255)
        
        blurred = img_copy.filter(ImageFilter.GaussianBlur(radius=20))
        img_copy.paste(blurred, mask=mask)
        
    elif mask_type == "pixelate":
        # Pixelate center region
        center_x, center_y = width // 2, height // 3
        box = (center_x - width//6, center_y - height//6,
               center_x + width//6, center_y + height//6)
        
        region = img_copy.crop(box)
        # Pixelate by resizing down and up
        small = region.resize((20, 20), Image.Resampling.NEAREST)
        pixelated = small.resize(region.size, Image.Resampling.NEAREST)
        img_copy.paste(pixelated, box)
        
    elif mask_type == "blackbar":
        # Add black bar over eyes area
        draw = ImageDraw.Draw(img_copy)
        eye_y = height // 3
        draw.rectangle([0, eye_y - height//12, width, eye_y + height//12], fill="black")
    
    # Add watermark
    draw = ImageDraw.Draw(img_copy)
    draw.text((10, height - 30), "PLAYALTER - Privacy Protected", fill=(255, 255, 255, 128))
    
    return img_copy

# Mock video processing
def process_video_frames(video_bytes: bytes, process_type: str) -> bytes:
    """Process video frames (mock implementation)"""
    # For demo, we'll just return a processed single frame as image
    # In real implementation, this would process all frames
    
    # Create a sample processed frame
    img = Image.new('RGB', (640, 480), color='navy')
    draw = ImageDraw.Draw(img)
    draw.text((50, 200), f"Video Processing: {process_type}", fill="white")
    draw.text((50, 250), "Frames: 30/30 processed", fill="cyan")
    draw.text((50, 300), "PLAYALTER Platform", fill="yellow")
    
    # Convert to bytes
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='PNG')
    return img_byte_arr.getvalue()

# Backend processing function
@app.function(image=image)
def process_media(file_bytes: bytes, service_type: str, file_type: str, 
                  target_bytes: Optional[bytes] = None) -> dict:
    """Process uploaded media based on service type"""
    
    try:
        if file_type in ["image/jpeg", "image/png", "image/jpg"]:
            # Process image
            image = Image.open(io.BytesIO(file_bytes)).convert("RGB")
            
            if service_type == "face_swap" and target_bytes:
                target_image = Image.open(io.BytesIO(target_bytes)).convert("RGB")
                processed = mock_face_swap(image, target_image)
            elif service_type == "privacy_blur":
                processed = generate_privacy_mask(image, "blur")
            elif service_type == "privacy_pixelate":
                processed = generate_privacy_mask(image, "pixelate")
            elif service_type == "privacy_blackbar":
                processed = generate_privacy_mask(image, "blackbar")
            else:
                processed = image
            
            # Convert to base64
            buffered = io.BytesIO()
            processed.save(buffered, format="PNG")
            img_base64 = base64.b64encode(buffered.getvalue()).decode()
            
            return {
                "success": True,
                "result_type": "image",
                "data": img_base64,
                "message": f"Processing complete: {service_type}"
            }
            
        elif file_type in ["video/mp4", "video/avi", "video/mov"]:
            # Process video (mock)
            result_bytes = process_video_frames(file_bytes, service_type)
            result_base64 = base64.b64encode(result_bytes).decode()
            
            return {
                "success": True,
                "result_type": "video_frame",
                "data": result_base64,
                "message": f"Video processing complete: {service_type}"
            }
            
        else:
            return {
                "success": False,
                "message": f"Unsupported file type: {file_type}"
            }
            
    except Exception as e:
        return {
            "success": False,
            "message": f"Processing error: {str(e)}"
        }

# Web interface HTML
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PLAYALTER Platform</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 20px;
            color: white;
        }
        
        .container {
            width: 100%;
            max-width: 1200px;
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 40px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
        }
        
        h1 {
            text-align: center;
            font-size: 3em;
            margin-bottom: 10px;
            background: linear-gradient(45deg, #fff, #f0f0f0);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.2);
        }
        
        .subtitle {
            text-align: center;
            font-size: 1.2em;
            margin-bottom: 40px;
            opacity: 0.9;
        }
        
        .upload-section {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .upload-box {
            background: rgba(255, 255, 255, 0.1);
            border: 2px dashed rgba(255, 255, 255, 0.5);
            border-radius: 15px;
            padding: 40px;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s ease;
            position: relative;
        }
        
        .upload-box:hover {
            background: rgba(255, 255, 255, 0.2);
            border-color: white;
            transform: translateY(-2px);
        }
        
        .upload-box.dragover {
            background: rgba(255, 255, 255, 0.3);
            border-color: #4ade80;
        }
        
        .upload-box input[type="file"] {
            display: none;
        }
        
        .upload-icon {
            font-size: 3em;
            margin-bottom: 15px;
        }
        
        .upload-text {
            font-size: 1.1em;
            margin-bottom: 10px;
        }
        
        .upload-hint {
            font-size: 0.9em;
            opacity: 0.7;
        }
        
        .file-name {
            margin-top: 15px;
            padding: 10px;
            background: rgba(255, 255, 255, 0.2);
            border-radius: 8px;
            font-size: 0.9em;
            word-break: break-all;
        }
        
        .service-selector {
            margin-bottom: 30px;
        }
        
        .service-label {
            display: block;
            margin-bottom: 10px;
            font-size: 1.1em;
        }
        
        .service-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
        }
        
        .service-option {
            background: rgba(255, 255, 255, 0.1);
            border: 2px solid transparent;
            border-radius: 10px;
            padding: 15px;
            cursor: pointer;
            transition: all 0.3s ease;
            text-align: center;
        }
        
        .service-option:hover {
            background: rgba(255, 255, 255, 0.2);
        }
        
        .service-option.selected {
            background: rgba(255, 255, 255, 0.3);
            border-color: white;
        }
        
        .service-option input[type="radio"] {
            display: none;
        }
        
        .service-icon {
            font-size: 2em;
            margin-bottom: 10px;
        }
        
        .process-btn {
            display: block;
            width: 100%;
            padding: 20px;
            background: linear-gradient(45deg, #4ade80, #22c55e);
            color: white;
            border: none;
            border-radius: 10px;
            font-size: 1.2em;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.3s ease;
            margin-bottom: 30px;
        }
        
        .process-btn:hover:not(:disabled) {
            transform: translateY(-2px);
            box-shadow: 0 10px 30px rgba(74, 222, 128, 0.4);
        }
        
        .process-btn:disabled {
            background: rgba(255, 255, 255, 0.2);
            cursor: not-allowed;
            opacity: 0.5;
        }
        
        .result-section {
            background: rgba(255, 255, 255, 0.1);
            border-radius: 15px;
            padding: 30px;
            min-height: 200px;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
        }
        
        .result-placeholder {
            text-align: center;
            opacity: 0.7;
        }
        
        .result-image {
            max-width: 100%;
            max-height: 600px;
            border-radius: 10px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
        }
        
        .loading {
            display: none;
            text-align: center;
        }
        
        .loading.active {
            display: block;
        }
        
        .spinner {
            border: 4px solid rgba(255, 255, 255, 0.3);
            border-top: 4px solid white;
            border-radius: 50%;
            width: 50px;
            height: 50px;
            animation: spin 1s linear infinite;
            margin: 0 auto 20px;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .error-message {
            background: rgba(239, 68, 68, 0.2);
            border: 1px solid #ef4444;
            color: #fca5a5;
            padding: 15px;
            border-radius: 8px;
            margin-top: 20px;
        }
        
        .success-message {
            background: rgba(34, 197, 94, 0.2);
            border: 1px solid #22c55e;
            color: #86efac;
            padding: 15px;
            border-radius: 8px;
            margin-top: 20px;
        }

        @media (max-width: 768px) {
            .upload-section {
                grid-template-columns: 1fr;
            }
            
            h1 {
                font-size: 2em;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎭 PLAYALTER Platform</h1>
        <p class="subtitle">AI-Powered Media Processing & Privacy Protection</p>
        
        <div class="upload-section">
            <div class="upload-box" id="sourceUpload">
                <input type="file" id="sourceFile" accept="image/*,video/*">
                <div class="upload-icon">📁</div>
                <div class="upload-text">Upload Source Media</div>
                <div class="upload-hint">Drag & drop or click to browse</div>
                <div class="file-name" id="sourceFileName" style="display: none;"></div>
            </div>
            
            <div class="upload-box" id="targetUpload">
                <input type="file" id="targetFile" accept="image/*">
                <div class="upload-icon">🎯</div>
                <div class="upload-text">Upload Target (Face Swap)</div>
                <div class="upload-hint">Optional - Only for face swap</div>
                <div class="file-name" id="targetFileName" style="display: none;"></div>
            </div>
        </div>
        
        <div class="service-selector">
            <label class="service-label">Select Service:</label>
            <div class="service-grid">
                <label class="service-option">
                    <input type="radio" name="service" value="privacy_blur" checked>
                    <div class="service-icon">🔐</div>
                    <div>Privacy Blur</div>
                </label>
                <label class="service-option">
                    <input type="radio" name="service" value="privacy_pixelate">
                    <div class="service-icon">🔲</div>
                    <div>Pixelate Face</div>
                </label>
                <label class="service-option">
                    <input type="radio" name="service" value="privacy_blackbar">
                    <div class="service-icon">◼</div>
                    <div>Black Bar</div>
                </label>
                <label class="service-option">
                    <input type="radio" name="service" value="face_swap">
                    <div class="service-icon">🔄</div>
                    <div>Face Swap</div>
                </label>
                <label class="service-option">
                    <input type="radio" name="service" value="video_process">
                    <div class="service-icon">🎬</div>
                    <div>Video Process</div>
                </label>
            </div>
        </div>
        
        <button class="process-btn" id="processBtn" disabled>
            Process Media
        </button>
        
        <div class="result-section">
            <div class="result-placeholder" id="resultPlaceholder">
                <div style="font-size: 3em; margin-bottom: 20px;">✨</div>
                <div>Your processed media will appear here</div>
            </div>
            <div class="loading" id="loading">
                <div class="spinner"></div>
                <div>Processing your media...</div>
            </div>
            <div id="resultContainer" style="display: none; width: 100%;"></div>
        </div>
        
        <div id="messageContainer"></div>
    </div>
    
    <script>
        let sourceFile = null;
        let targetFile = null;
        
        // Setup upload boxes
        function setupUploadBox(boxId, inputId, fileNameId, fileVar) {
            const box = document.getElementById(boxId);
            const input = document.getElementById(inputId);
            const fileName = document.getElementById(fileNameId);
            
            box.addEventListener('click', () => input.click());
            
            box.addEventListener('dragover', (e) => {
                e.preventDefault();
                box.classList.add('dragover');
            });
            
            box.addEventListener('dragleave', () => {
                box.classList.remove('dragover');
            });
            
            box.addEventListener('drop', (e) => {
                e.preventDefault();
                box.classList.remove('dragover');
                
                const files = e.dataTransfer.files;
                if (files.length > 0) {
                    handleFileSelect(files[0], fileName, fileVar === 'source');
                }
            });
            
            input.addEventListener('change', (e) => {
                if (e.target.files.length > 0) {
                    handleFileSelect(e.target.files[0], fileName, fileVar === 'source');
                }
            });
        }
        
        function handleFileSelect(file, fileNameEl, isSource) {
            if (isSource) {
                sourceFile = file;
            } else {
                targetFile = file;
            }
            
            fileNameEl.textContent = file.name;
            fileNameEl.style.display = 'block';
            
            updateProcessButton();
        }
        
        function updateProcessButton() {
            const btn = document.getElementById('processBtn');
            const service = document.querySelector('input[name="service"]:checked').value;
            
            if (service === 'face_swap') {
                btn.disabled = !sourceFile || !targetFile;
            } else {
                btn.disabled = !sourceFile;
            }
        }
        
        // Setup service options
        document.querySelectorAll('.service-option').forEach(option => {
            option.addEventListener('click', () => {
                document.querySelectorAll('.service-option').forEach(o => o.classList.remove('selected'));
                option.classList.add('selected');
                updateProcessButton();
            });
        });
        
        // Initialize first selected
        document.querySelector('.service-option').classList.add('selected');
        
        // Setup upload boxes
        setupUploadBox('sourceUpload', 'sourceFile', 'sourceFileName', 'source');
        setupUploadBox('targetUpload', 'targetFile', 'targetFileName', 'target');
        
        // Process button
        document.getElementById('processBtn').addEventListener('click', async () => {
            if (!sourceFile) return;
            
            const service = document.querySelector('input[name="service"]:checked').value;
            const formData = new FormData();
            
            formData.append('source_file', sourceFile);
            formData.append('service_type', service);
            
            if (targetFile && service === 'face_swap') {
                formData.append('target_file', targetFile);
            }
            
            // Show loading
            document.getElementById('loading').classList.add('active');
            document.getElementById('resultPlaceholder').style.display = 'none';
            document.getElementById('resultContainer').style.display = 'none';
            document.getElementById('messageContainer').innerHTML = '';
            
            try {
                const response = await fetch('/process', {
                    method: 'POST',
                    body: formData
                });
                
                const result = await response.json();
                
                document.getElementById('loading').classList.remove('active');
                
                if (result.success) {
                    // Show result
                    const container = document.getElementById('resultContainer');
                    container.innerHTML = `
                        <img src="data:image/png;base64,${result.data}" class="result-image" alt="Processed result">
                    `;
                    container.style.display = 'block';
                    
                    // Show success message
                    document.getElementById('messageContainer').innerHTML = `
                        <div class="success-message">${result.message}</div>
                    `;
                } else {
                    // Show error
                    document.getElementById('resultPlaceholder').style.display = 'block';
                    document.getElementById('messageContainer').innerHTML = `
                        <div class="error-message">Error: ${result.message}</div>
                    `;
                }
            } catch (error) {
                document.getElementById('loading').classList.remove('active');
                document.getElementById('resultPlaceholder').style.display = 'block';
                document.getElementById('messageContainer').innerHTML = `
                    <div class="error-message">Error: ${error.message}</div>
                `;
            }
        });
    </script>
</body>
</html>
"""

# FastAPI routes
@web_app.get("/", response_class=HTMLResponse)
async def home():
    """Serve the main web interface"""
    return HTML_TEMPLATE

@web_app.post("/process")
async def process_upload(
    source_file: UploadFile = File(...),
    service_type: str = Form(...),
    target_file: Optional[UploadFile] = File(None)
):
    """Handle file upload and processing"""
    
    # Read source file
    source_bytes = await source_file.read()
    source_type = source_file.content_type
    
    # Read target file if provided
    target_bytes = None
    if target_file:
        target_bytes = await target_file.read()
    
    # Call Modal function for processing
    process_fn = modal.Function.lookup("playalter-platform", "process_media")
    result = process_fn.remote(
        file_bytes=source_bytes,
        service_type=service_type,
        file_type=source_type,
        target_bytes=target_bytes
    )
    
    return JSONResponse(content=result)

# Modal ASGI app
@app.function(image=image)
@modal.asgi_app()
def fastapi_app():
    """Serve the FastAPI app through Modal"""
    return web_app

# Test endpoint
@web_app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "platform": "PLAYALTER", "version": "1.0.0"}

if __name__ == "__main__":
    print("PLAYALTER Platform ready for deployment!")
    print("Deploy with: modal deploy main_app.py")