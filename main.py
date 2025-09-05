#!/usr/bin/env python3
"""
PLAYALTER Platform - Main Deployment Script
Advanced AI Face Processing Platform with FLAME Model & Privacy Protection
"""

import modal
import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse

# Import our modules
from config.settings import get_settings, get_config
from utils.logging_config import setup_default_logging
from auth.security import security_manager, create_demo_users
from api.endpoints import (
    health_check, analyze_face_endpoint, create_privacy_mask_endpoint,
    face_swap_endpoint, face_compatibility_endpoint, batch_process_endpoint,
    services_status, initialize_services_endpoint
)

# Initialize logging
setup_default_logging()
logger = logging.getLogger(__name__)

# Get configuration
settings = get_settings()

# Create Modal app
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
        "trimesh==3.23.5",
        "pytorch3d==0.7.5",
        "face-alignment==1.3.5",
        "insightface==0.7.3",
        "onnxruntime-gpu==1.16.0",
        "fastapi==0.104.1",
        "uvicorn==0.24.0",
        "python-multipart==0.0.6",
        "aiofiles==23.2.1",
        "requests==2.31.0",
        "pydantic==2.4.2",
        "jinja2==3.1.2",
        "python-jose[cryptography]==3.3.0",
        "passlib[bcrypt]==1.7.4",
        "python-dotenv==1.0.0"
    ])
    .apt_install([
        "libgl1-mesa-glx",
        "libglib2.0-0", 
        "libsm6",
        "libxext6",
        "libxrender-dev",
        "libgomp1",
        "libgoogle-perftools4",
        "libtcmalloc-minimal4"
    ])
    .pip_install([
        "flame-pytorch @ git+https://github.com/soubhiksanyal/FLAME_PyTorch.git"
    ])
)

@app.function(
    image=image,
    gpu=settings.gpu_type,
    memory=settings.memory_mb,
    timeout=settings.timeout_seconds,
    keep_warm=settings.keep_warm,
    allow_concurrent_inputs=settings.max_concurrent_inputs
)
@modal.web_endpoint(method="GET", path="/")
def serve_frontend():
    """Serve the main web interface."""
    try:
        with open("web/index.html", "r") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="""
        <!DOCTYPE html>
        <html>
        <head><title>PLAYALTER Platform</title></head>
        <body>
            <h1>🚀 PLAYALTER Platform</h1>
            <p>Advanced AI Face Processing Platform</p>
            <h2>Available Services:</h2>
            <ul>
                <li><a href="/api/services/status">Service Status</a></li>
                <li><a href="/api/services/initialize">Initialize Services</a></li>
            </ul>
            <h2>API Endpoints:</h2>
            <ul>
                <li>POST /api/face/analyze - Face Analysis with FLAME</li>
                <li>POST /api/privacy/mask - Privacy Mask Generation</li>
                <li>POST /api/face/swap - Face Swapping</li>
                <li>POST /api/face/compatibility - Face Compatibility Check</li>
                <li>POST /api/batch/process - Batch Processing</li>
            </ul>
        </body>
        </html>
        """)

@app.function(
    image=image,
    gpu=settings.gpu_type,
    memory=settings.memory_mb,
    timeout=settings.timeout_seconds,
    keep_warm=settings.keep_warm,
    allow_concurrent_inputs=settings.max_concurrent_inputs
)
@modal.web_endpoint(method="GET", path="/docs")
def api_documentation():
    """Serve API documentation."""
    return HTMLResponse(content="""
    <!DOCTYPE html>
    <html>
    <head>
        <title>PLAYALTER API Documentation</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            .endpoint { background: #f5f5f5; padding: 20px; margin: 10px 0; border-radius: 5px; }
            .method { color: #fff; padding: 5px 10px; border-radius: 3px; font-weight: bold; }
            .post { background: #49cc90; }
            .get { background: #61affe; }
            code { background: #f0f0f0; padding: 2px 5px; border-radius: 3px; }
        </style>
    </head>
    <body>
        <h1>🔥 PLAYALTER API Documentation</h1>
        
        <h2>Authentication</h2>
        <p>Include your API key in the Authorization header: <code>Authorization: Bearer your_api_key</code></p>
        
        <h2>Endpoints</h2>
        
        <div class="endpoint">
            <h3><span class="method get">GET</span> /api/services/status</h3>
            <p>Get the status of all services and available operations.</p>
        </div>
        
        <div class="endpoint">
            <h3><span class="method post">POST</span> /api/face/analyze</h3>
            <p>Analyze face using FLAME model for detailed measurements.</p>
            <strong>Request Body:</strong>
            <pre><code>{
    "image_base64": "base64_encoded_image",
    "include_measurements": true,
    "include_3d_mesh": false
}</code></pre>
        </div>
        
        <div class="endpoint">
            <h3><span class="method post">POST</span> /api/privacy/mask</h3>
            <p>Generate adaptive privacy masks based on face measurements.</p>
            <strong>Request Body:</strong>
            <pre><code>{
    "image_base64": "base64_encoded_image",
    "mask_type": "blur",
    "strength": 1.0,
    "create_levels": false
}</code></pre>
            <p>Mask types: <code>blur</code>, <code>pixelate</code>, <code>noise</code>, <code>synthetic</code></p>
        </div>
        
        <div class="endpoint">
            <h3><span class="method post">POST</span> /api/face/swap</h3>
            <p>Perform high-quality face swapping using InSwapper model.</p>
            <strong>Request Body:</strong>
            <pre><code>{
    "source_image_base64": "base64_encoded_source",
    "target_image_base64": "base64_encoded_target",
    "source_face_index": 0,
    "target_face_index": 0
}</code></pre>
        </div>
        
        <div class="endpoint">
            <h3><span class="method post">POST</span> /api/batch/process</h3>
            <p>Process multiple images in batch.</p>
            <strong>Request Body:</strong>
            <pre><code>{
    "images_base64": ["image1_base64", "image2_base64"],
    "operation": "privacy_mask",
    "parameters": {"mask_type": "blur", "strength": 1.0}
}</code></pre>
        </div>
        
        <h2>Rate Limits</h2>
        <ul>
            <li>Basic tier: 100 requests per hour</li>
            <li>Premium tier: 500 requests per hour</li>
            <li>Enterprise tier: 2000 requests per hour</li>
        </ul>
        
        <h2>File Limits</h2>
        <ul>
            <li>Maximum file size: 10MB</li>
            <li>Maximum batch size: 10 images</li>
            <li>Supported formats: JPEG, PNG, BMP, TIFF, WebP</li>
        </ul>
    </body>
    </html>
    """)

# Register all API endpoints with the Modal app
# Health and status endpoints
app.function(
    image=image,
    gpu=settings.gpu_type,
    memory=settings.memory_mb,
    timeout=settings.timeout_seconds,
    keep_warm=settings.keep_warm,
    allow_concurrent_inputs=10
)(modal.web_endpoint(method="GET", path="/health")(health_check))

app.function(
    image=image,
    gpu=settings.gpu_type,
    memory=settings.memory_mb,
    timeout=settings.timeout_seconds,
    keep_warm=settings.keep_warm,
    allow_concurrent_inputs=10
)(modal.web_endpoint(method="GET", path="/api/services/status")(services_status))

app.function(
    image=image,
    gpu=settings.gpu_type,
    memory=settings.memory_mb,
    timeout=settings.timeout_seconds,
    keep_warm=settings.keep_warm,
    allow_concurrent_inputs=10
)(modal.web_endpoint(method="POST", path="/api/services/initialize")(initialize_services_endpoint))

# Core API endpoints
app.function(
    image=image,
    gpu=settings.gpu_type,
    memory=settings.memory_mb,
    timeout=settings.timeout_seconds,
    keep_warm=settings.keep_warm,
    allow_concurrent_inputs=5
)(modal.web_endpoint(method="POST", path="/api/face/analyze")(analyze_face_endpoint))

app.function(
    image=image,
    gpu=settings.gpu_type,
    memory=settings.memory_mb,
    timeout=settings.timeout_seconds,
    keep_warm=settings.keep_warm,
    allow_concurrent_inputs=5
)(modal.web_endpoint(method="POST", path="/api/privacy/mask")(create_privacy_mask_endpoint))

app.function(
    image=image,
    gpu=settings.gpu_type,
    memory=settings.memory_mb,
    timeout=settings.timeout_seconds,
    keep_warm=settings.keep_warm,
    allow_concurrent_inputs=3
)(modal.web_endpoint(method="POST", path="/api/face/swap")(face_swap_endpoint))

app.function(
    image=image,
    gpu=settings.gpu_type,
    memory=settings.memory_mb,
    timeout=settings.timeout_seconds,
    keep_warm=settings.keep_warm,
    allow_concurrent_inputs=3
)(modal.web_endpoint(method="POST", path="/api/face/compatibility")(face_compatibility_endpoint))

app.function(
    image=image,
    gpu=settings.gpu_type,
    memory=24576,  # Extra memory for batch processing
    timeout=7200,   # Extended timeout for batch jobs
    allow_concurrent_inputs=2
)(modal.web_endpoint(method="POST", path="/api/batch/process")(batch_process_endpoint))

@app.function(
    image=image,
    gpu=settings.gpu_type,
    memory=settings.memory_mb,
    timeout=settings.timeout_seconds
)
def setup_demo_environment():
    """Setup demo users and environment for testing."""
    logger.info("Setting up demo environment...")
    
    try:
        demo_users = create_demo_users()
        
        return {
            "success": True,
            "message": "Demo environment setup complete",
            "demo_users": {
                "basic_user": {
                    "username": "demo_basic",
                    "password": "demo123",
                    "api_key": demo_users['basic_user']['api_key']
                },
                "premium_user": {
                    "username": "demo_premium", 
                    "password": "demo123",
                    "api_key": demo_users['premium_user']['api_key']
                }
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to setup demo environment: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

def local_test():
    """Test the platform locally (for development)."""
    print("🚀 PLAYALTER Platform - Local Test")
    print("=" * 50)
    
    # Test configuration
    print(f"Environment: {settings.environment}")
    print(f"Debug mode: {settings.debug}")
    print(f"GPU type: {settings.gpu_type}")
    print(f"Memory: {settings.memory_mb}MB")
    print(f"Upload directory: {settings.upload_dir}")
    print(f"Log directory: {settings.log_dir}")
    
    # Test logging
    logger.info("Platform initialized successfully")
    logger.debug("Debug logging is working")
    
    # Test configuration validation
    issues = settings.validate_config() if hasattr(settings, 'validate_config') else []
    if issues:
        print("\n⚠️  Configuration Issues:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("\n✅ Configuration validation passed")
    
    print("\n📋 Available Features:")
    features = [
        ("Face Analysis with FLAME", settings.enable_face_analysis),
        ("Privacy Mask Generation", settings.enable_privacy_masks),
        ("Face Swapping", settings.enable_face_swap),
        ("Batch Processing", settings.enable_batch_processing),
        ("3D Mesh Export", settings.enable_3d_mesh_export),
        ("Video Processing", settings.enable_video_processing)
    ]
    
    for feature, enabled in features:
        status = "✅" if enabled else "❌"
        print(f"  {status} {feature}")
    
    print(f"\n🔗 Web Interface: http://localhost:{settings.port}")
    print(f"📚 API Documentation: http://localhost:{settings.port}/docs")
    print(f"❤️  Health Check: http://localhost:{settings.port}/health")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "test":
            local_test()
        elif command == "deploy":
            print("Deploying to Modal...")
            app.deploy("playalter-platform")
        elif command == "serve":
            print("Starting local development server...")
            import uvicorn
            uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
        else:
            print(f"Unknown command: {command}")
            print("Available commands: test, deploy, serve")
    else:
        print("🎉 PLAYALTER Platform Ready!")
        print("Commands:")
        print("  python main.py test    - Run local tests")
        print("  python main.py deploy  - Deploy to Modal")
        print("  python main.py serve   - Start local server")
        print("\n🚀 To deploy: modal deploy main.py")