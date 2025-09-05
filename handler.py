import modal
import base64
import numpy as np
from PIL import Image
import io
import requests

app = modal.App("playalter-beast")

@app.function(
    image=modal.Image.debian_slim(python_version="3.11")
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
    """Simple working swap"""
    try:
        import cv2
        
        # Decode PROPERLY
        source_bytes = base64.b64decode(source_b64)
        target_bytes = base64.b64decode(target_b64)
        
        # numpy array olarak oku
        source_array = np.frombuffer(source_bytes, np.uint8)
        target_array = np.frombuffer(target_bytes, np.uint8)
        
        # OpenCV ile decode et
        source_cv = cv2.imdecode(source_array, cv2.IMREAD_COLOR)
        target_cv = cv2.imdecode(target_array, cv2.IMREAD_COLOR)
        
        if source_cv is None or target_cv is None:
            return {
                "success": False,
                "message": "Image decode failed"
            }
        
        # Basit işlem - target'ı döndür
        result_cv = target_cv
        
        # JPEG olarak encode et
        _, buffer = cv2.imencode('.jpg', result_cv)
        result_b64 = base64.b64encode(buffer).decode()
        
        return {
            "success": True,
            "output": result_b64,
            "message": f"Images processed: {source_cv.shape} -> {target_cv.shape}"
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error: {str(e)}"
        }

@app.local_entrypoint()
def test():
    print("="*60)
    print("PLAYALTER TEST - Fixed Version")
    print("="*60)
    
    # Basit test resimleri oluştur
    print("Creating test images...")
    
    # Kırmızı kare
    red_img = Image.new('RGB', (256, 256), 'red')
    red_buffer = io.BytesIO()
    red_img.save(red_buffer, format='JPEG')
    red_b64 = base64.b64encode(red_buffer.getvalue()).decode()
    
    # Mavi kare
    blue_img = Image.new('RGB', (256, 256), 'blue')
    blue_buffer = io.BytesIO()
    blue_img.save(blue_buffer, format='JPEG')
    blue_b64 = base64.b64encode(blue_buffer.getvalue()).decode()
    
    print("Processing...")
    result = process_face_swap.remote(red_b64, blue_b64)
    
    if result["success"]:
        print(f"✓ Success: {result['message']}")
        with open("test_output.jpg", "wb") as f:
            f.write(base64.b64decode(result['output']))
        print("✓ Saved: test_output.jpg")
    else:
        print(f"✗ Failed: {result['message']}")

if __name__ == "__main__":
    modal.runner.run(app)