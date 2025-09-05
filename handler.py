import modal
import base64
import numpy as np
from PIL import Image
import io
import requests

app = modal.App("playalter-beast")

@app.function(
    image=modal.Image.debian_slim(python_version="3.11")  # ← PYTHON 3.11 KULLAN!
        .apt_install(
            "libgl1-mesa-glx", 
            "libglib2.0-0", 
            "libsm6",
            "libxext6", 
            "libxrender-dev", 
            "libgomp1"
        )
        .pip_install(
            "opencv-python-headless==4.8.1.78",
            "pillow==10.1.0",
            "numpy==1.24.4",
            "requests==2.31.0"
        ),
    memory=4096,
    timeout=60
)
def process_face_swap(source_b64: str, target_b64: str) -> dict:
    """Simple working test"""
    try:
        # Decode images
        source_data = base64.b64decode(source_b64)
        target_data = base64.b64decode(target_b64)
        
        # Open images
        source_img = Image.open(io.BytesIO(source_data)).convert('RGB')
        target_img = Image.open(io.BytesIO(target_data)).convert('RGB')
        
        # Convert to numpy
        source_np = np.array(source_img)
        target_np = np.array(target_img)
        
        print(f"✅ Source shape: {source_np.shape}")
        print(f"✅ Target shape: {target_np.shape}")
        
        # Simple swap - return target for now
        result_img = target_img
        
        # Encode result
        buffer = io.BytesIO()
        result_img.save(buffer, format='JPEG')
        buffer.seek(0)
        result_b64 = base64.b64encode(buffer.getvalue()).decode()
        
        return {
            "success": True,
            "output": result_b64,
            "message": f"Test OK! Images processed: {source_np.shape} -> {target_np.shape}"
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error: {str(e)}"
        }

@app.local_entrypoint()
def test():
    print("="*60)
    print("🚀 PLAYALTER TEST v2 - FIXED VERSION")
    print("="*60)
    
    # Test with simple colored squares
    print("Creating test images...")
    
    # Create red square
    red_img = Image.new('RGB', (256, 256), color='red')
    red_buffer = io.BytesIO()
    red_img.save(red_buffer, format='PNG')
    red_b64 = base64.b64encode(red_buffer.getvalue()).decode()
    
    # Create blue square
    blue_img = Image.new('RGB', (256, 256), color='blue')
    blue_buffer = io.BytesIO()
    blue_img.save(blue_buffer, format='PNG')
    blue_b64 = base64.b64encode(blue_buffer.getvalue()).decode()
    
    print("🔄 Processing test swap...")
    result = process_face_swap.remote(red_b64, blue_b64)
    
    if result["success"]:
        print("✅ SUCCESS!")
        print(f"📝 {result['message']}")
    else:
        print(f"❌ Failed: {result['message']}")

if __name__ == "__main__":
    modal.runner.run(app)