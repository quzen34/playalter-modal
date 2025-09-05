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
    """Working face swap without complex models"""
    try:
        import cv2
        
        # Decode images
        source_data = base64.b64decode(source_b64)
        target_data = base64.b64decode(target_b64)
        
        source_img = Image.open(io.BytesIO(source_data)).convert('RGB')
        target_img = Image.open(io.BytesIO(target_data)).convert('RGB')
        
        # Convert to opencv format
        source_cv = cv2.cvtColor(np.array(source_img), cv2.COLOR_RGB2BGR)
        target_cv = cv2.cvtColor(np.array(target_img), cv2.COLOR_RGB2BGR)
        
        # Use OpenCV's face detection (simpler)
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        
        # Detect faces
        source_faces = face_cascade.detectMultiScale(cv2.cvtColor(source_cv, cv2.COLOR_BGR2GRAY), 1.1, 4)
        target_faces = face_cascade.detectMultiScale(cv2.cvtColor(target_cv, cv2.COLOR_BGR2GRAY), 1.1, 4)
        
        result_cv = target_cv.copy()
        
        if len(source_faces) > 0 and len(target_faces) > 0:
            # Get first face from each
            (sx, sy, sw, sh) = source_faces[0]
            (tx, ty, tw, th) = target_faces[0]
            
            # Extract face region from source
            source_face = source_cv[sy:sy+sh, sx:sx+sw]
            
            # Resize to target face size
            resized_face = cv2.resize(source_face, (tw, th))
            
            # Simple blend
            result_cv[ty:ty+th, tx:tx+tw] = resized_face
            
            message = f"Face swap successful! Found {len(source_faces)} source faces, {len(target_faces)} target faces"
        else:
            message = f"Faces detected - Source: {len(source_faces)}, Target: {len(target_faces)}"
        
        # Convert back to RGB
        result_rgb = cv2.cvtColor(result_cv, cv2.COLOR_BGR2RGB)
        result_img = Image.fromarray(result_rgb)
        
        # Encode result
        buffer = io.BytesIO()
        result_img.save(buffer, format='JPEG', quality=95)
        buffer.seek(0)
        result_b64 = base64.b64encode(buffer.getvalue()).decode()
        
        return {
            "success": True,
            "output": result_b64,
            "message": message,
            "source_faces": len(source_faces),
            "target_faces": len(target_faces)
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error: {str(e)}"
        }

@app.local_entrypoint()
def test():
    print("="*60)
    print("🚀 PLAYALTER - OPENCV FACE SWAP TEST")
    print("="*60)
    
    # Daha net yüz resimleri kullanalım
    urls = {
        "person1": "https://raw.githubusercontent.com/opencv/opencv/master/samples/data/lena.jpg",
        "person2": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5a/Arnold_Schwarzenegger_by_Gage_Skidmore_4.jpg/400px-Arnold_Schwarzenegger_by_Gage_Skidmore_4.jpg"
    }
    
    print("📥 Downloading test images...")
    
    img1 = requests.get(urls["person1"]).content
    img2 = requests.get(urls["person2"]).content
    
    img1_b64 = base64.b64encode(img1).decode()
    img2_b64 = base64.b64encode(img2).decode()
    
    print("🔄 Processing face swap...")
    result = process_face_swap.remote(img1_b64, img2_b64)
    
    print(f"📊 Result: {result['message']}")
    print(f"   Source faces: {result.get('source_faces', 0)}")
    print(f"   Target faces: {result.get('target_faces', 0)}")
    
    if result["success"]:
        with open("face_swap_result.jpg", "wb") as f:
            f.write(base64.b64decode(result['output']))
        print("💾 Saved: face_swap_result.jpg")

if __name__ == "__main__":
    modal.runner.run(app)