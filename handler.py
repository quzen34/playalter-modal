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
            "libgomp1",
            "wget",
            "unzip"
        )
        .run_commands(
            "mkdir -p /root/.insightface/models",
            "wget -q -O /tmp/buffalo_l.zip https://github.com/deepinsight/insightface/releases/download/v0.7/buffalo_l.zip",
            "cd /root/.insightface/models && unzip -q /tmp/buffalo_l.zip",
            "rm /tmp/buffalo_l.zip"
        )
        .pip_install(
            "opencv-python-headless==4.8.1.78",
            "pillow==10.1.0",
            "numpy==1.24.4",
            "insightface==0.7.3",
            "onnxruntime==1.16.3",
            "requests==2.31.0"
        ),
    gpu="t4",
    memory=8192,
    timeout=300
)
def process_face_swap(source_b64: str, target_b64: str) -> dict:
    """Face swap with fixed paths"""
    try:
        import cv2
        import insightface
        from insightface.app import FaceAnalysis
        import os
        
        # Debug: Check what's in the models folder
        print("Checking models directory...")
        models_path = "/root/.insightface/models"
        for root, dirs, files in os.walk(models_path):
            print(f"Dir: {root}")
            for f in files[:5]:  # First 5 files
                print(f"  File: {f}")
        
        # Decode images
        source_bytes = base64.b64decode(source_b64)
        target_bytes = base64.b64decode(target_b64)
        
        source_array = np.frombuffer(source_bytes, np.uint8)
        target_array = np.frombuffer(target_bytes, np.uint8)
        
        source_cv = cv2.imdecode(source_array, cv2.IMREAD_COLOR)
        target_cv = cv2.imdecode(target_array, cv2.IMREAD_COLOR)
        
        if source_cv is None or target_cv is None:
            return {
                "success": False,
                "message": "Failed to decode images"
            }
        
        print(f"Images decoded: Source {source_cv.shape}, Target {target_cv.shape}")
        
        # Initialize face analysis with correct path
        app = FaceAnalysis(
            name='buffalo_l',
            root='/root/.insightface',
            providers=['CPUExecutionProvider']  # CPU for now
        )
        app.prepare(ctx_id=0, det_size=(640, 640))
        print("FaceAnalysis initialized")
        
        # Detect faces
        source_faces = app.get(source_cv)
        target_faces = app.get(target_cv)
        
        print(f"Faces detected: Source={len(source_faces) if source_faces else 0}, Target={len(target_faces) if target_faces else 0}")
        
        # Simple swap if faces found
        result = target_cv.copy()
        
        if source_faces and target_faces:
            # Get bounding boxes
            s_bbox = source_faces[0].bbox.astype(int)
            t_bbox = target_faces[0].bbox.astype(int)
            
            # Extract face from source
            face = source_cv[s_bbox[1]:s_bbox[3], s_bbox[0]:s_bbox[2]]
            
            # Resize and paste
            if face.size > 0:
                face_resized = cv2.resize(face, (t_bbox[2]-t_bbox[0], t_bbox[3]-t_bbox[1]))
                result[t_bbox[1]:t_bbox[3], t_bbox[0]:t_bbox[2]] = face_resized
                print("Face swap applied!")
        
        # Encode result
        _, buffer = cv2.imencode('.jpg', result, [cv2.IMWRITE_JPEG_QUALITY, 95])
        result_b64 = base64.b64encode(buffer).decode()
        
        message = f"Processed! Source faces: {len(source_faces) if source_faces else 0}, Target faces: {len(target_faces) if target_faces else 0}"
        
        return {
            "success": True,
            "output": result_b64,
            "message": message
        }
        
    except Exception as e:
        import traceback
        print(f"ERROR: {e}")
        print(traceback.format_exc())
        
        # Return original image on error
        try:
            target_bytes = base64.b64decode(target_b64)
            return {
                "success": False,
                "output": target_b64,
                "message": f"Error: {str(e)}"
            }
        except:
            return {
                "success": False,
                "message": f"Error: {str(e)}"
            }

@app.local_entrypoint()
def test():
    print("="*60)
    print("PLAYALTER - REAL FACE TEST")
    print("="*60)
    
    # GERÇEK YÜZ RESİMLERİ
    urls = {
        "person1": "https://raw.githubusercontent.com/ageitgey/face_recognition/master/examples/biden.jpg",
        "person2": "https://raw.githubusercontent.com/ageitgey/face_recognition/master/examples/obama.jpg"
    }
    
    print("Downloading real face images...")
    
    try:
        img1_data = requests.get(urls["person1"]).content
        img2_data = requests.get(urls["person2"]).content
        
        img1_b64 = base64.b64encode(img1_data).decode()
        img2_b64 = base64.b64encode(img2_data).decode()
        
        print("Processing real faces...")
        result = process_face_swap.remote(img1_b64, img2_b64)
        
        print(f"Result: {result.get('message')}")
        
        if result.get("success") and result.get("output"):
            with open("biden_obama_result.jpg", "wb") as f:
                f.write(base64.b64decode(result['output']))
            print("✅ SAVED: biden_obama_result.jpg")
            
            # Parse message to check face count
            msg = result.get('message', '')
            if 'Source faces: 0' in msg:
                print("⚠️ No faces detected - check image URLs")
            else:
                print("✅ FACES DETECTED AND SWAPPED!")
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    modal.runner.run(app)