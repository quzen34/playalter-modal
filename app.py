import modal
import os
from typing import Optional, Dict, Any
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = modal.App("playalter-platform")

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
    gpu="T4",
    memory=16384,
    timeout=3600,
    keep_warm=1,
    allow_concurrent_inputs=10
)
@modal.web_endpoint(method="GET", path="/")
async def health_check():
    return {"status": "healthy", "service": "PLAYALTER Platform"}

if __name__ == "__main__":
    app.deploy("playalter-platform")