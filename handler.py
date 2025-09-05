import modal
import base64
import numpy as np
from PIL import Image
import io
import cv2
import requests

app = modal.App("playalter-beast")

@app.function(
    image=modal.Image.debian_slim()
        .apt_install(
            "libgl1-mesa-glx", "libglib2.0-0", "libsm6",
            "libxext6", "libxrender-dev", "libgomp1"
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
    """Simple face swap for testing"""
    try:
        # Decode images PROPERLY
        source_data = base64.b64decode(source_b64)
        target_data = base64.b64decode(target_b64)
        
        # Open with PIL
        source_img = Image.open(io.BytesIO(source_data)).convert('RGB')
        target_img = Image.open(io.BytesIO(target_data)).convert('RGB')
        
        # Simple processing - just return target for now
        result_img = target_img
        
        # Encode result
        buffer = io.BytesIO()
        result_img.save(buffer, format='JPEG')
        buffer.seek(0)
        result_b64 = base64.b64encode(buffer.getvalue()).decode()
        
        return {
            "success": True,
            "output": result_b64,
            "message": "Test successful - returning target image"
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error: {str(e)}"
        }

@app.local_entrypoint()
def test():
    print("🚀 PLAYALTER TEST - Obama & Biden")
    
    # Working image URLs
    urls = {
        "obama": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8d/President_Barack_Obama.jpg/320px-President_Barack_Obama.jpg",
        "biden": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/68/Joe_Biden_presidential_portrait.jpg/320px-Joe_Biden_presidential_portrait.jpg"
    }
    
    print("📥 Downloading images...")
    
    try:
        # Download images
        obama_response = requests.get(urls["obama"])
        biden_response = requests.get(urls["biden"])
        
        if obama_response.status_code != 200 or biden_response.status_code != 200:
            print("❌ Download failed")
            return
        
        # Convert to base64
        obama_b64 = base64.b64encode(obama_response.content).decode('utf-8')
        biden_b64 = base64.b64encode(biden_response.content).decode('utf-8')
        
        print(f"✅ Images downloaded (Obama: {len(obama_b64)}, Biden: {len(biden_b64)} chars)")
        
        # Test swap
        print("🔄 Processing...")
        result = process_face_swap.remote(obama_b64, biden_b64)
        
        if result["success"]:
            print("✅ SUCCESS!")
            print(f"📝 {result['message']}")
            
            # Save result
            with open("test_output.jpg", "wb") as f:
                f.write(base64.b64decode(result['output']))
            print("💾 Saved as test_output.jpg")
        else:
            print(f"❌ Failed: {result['message']}")
            
    except Exception as e:
        print(f"❌ Error: {e}")