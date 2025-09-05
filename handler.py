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
            "cd /root/.insightface/models && unzip -q /tmp/buffalo_l.zip"
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
    """Real face swap with InsightFace"""
    try:
        import cv2
        import insightface
        from insightface.app import FaceAnalysis
        
        # Decode images
        source_bytes = base64.b64decode(source_b64)
        target_bytes = base64.b64decode(target_b64)
        
        source_array = np.frombuffer(source_bytes, np.uint8)
        target_array = np.frombuffer(target_bytes, np.uint8)
        
        source_cv = cv2.imdecode(source_array, cv2.IMREAD_COLOR)
        target_cv = cv2.imdecode(target_array, cv2.IMREAD_COLOR)
        
        # Initialize face analysis
        app = FaceAnalysis(name='buffalo_l', providers=['CUDAExecutionProvider', 'CPUExecutionProvider'])
        app.prepare(ctx_id=0, det_size=(640, 640))
        
        # Detect faces
        source_faces = app.get(source_cv)
        target_faces = app.get(target_cv)
        
        if not source_faces:
            # If no face, return original
            _, buffer = cv2.imencode('.jpg', target_cv)
            return {
                "success": False,
                "output": base64.b64encode(buffer).decode(),
                "message": "No face detected in source"
            }
            
        if not target_faces:
            _, buffer = cv2.imencode('.jpg', target_cv)
            return {
                "success": False,
                "output": base64.b64encode(buffer).decode(),
                "message": "No face detected in target"
            }
        
        # Simple face region swap
        result = target_cv.copy()
        
        # Get bounding boxes
        s_bbox = source_faces[0].bbox.astype(int)
        t_bbox = target_faces[0].bbox.astype(int)
        
        # Extract face from source
        face = source_cv[s_bbox[1]:s_bbox[3], s_bbox[0]:s_bbox[2]]
        
        # Resize to target size
        if face.size > 0:
            face_resized = cv2.resize(face, (t_bbox[2]-t_bbox[0], t_bbox[3]-t_bbox[1]))
            # Paste onto target
            result[t_bbox[1]:t_bbox[3], t_bbox[0]:t_bbox[2]] = face_resized
        
        # Encode result
        _, buffer = cv2.imencode('.jpg', result, [cv2.IMWRITE_JPEG_QUALITY, 95])
        result_b64 = base64.b64encode(buffer).decode()
        
        return {
            "success": True,
            "output": result_b64,
            "message": f"Face swap successful! Detected {len(source_faces)} source, {len(target_faces)} target faces"
        }
        
    except Exception as e:
        import traceback
        return {
            "success": False,
            "message": str(e),
            "trace": traceback.format_exc()
        }

@app.local_entrypoint()
def test():
    print("="*60)
    print("PLAYALTER FACE SWAP - REAL TEST")
    print("="*60)
    
    # Obama ve Biden URL'leri
    urls = {
        "obama": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8d/President_Barack_Obama.jpg/480px-President_Barack_Obama.jpg",
        "biden": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/68/Joe_Biden_presidential_portrait.jpg/480px-Joe_Biden_presidential_portrait.jpg"
    }
    
    print("Downloading Obama and Biden...")
    
    obama = requests.get(urls["obama"]).content
    biden = requests.get(urls["biden"]).content
    
    obama_b64 = base64.b64encode(obama).decode()
    biden_b64 = base64.b64encode(biden).decode()
    
    print("Processing face swap...")
    result = process_face_swap.remote(obama_b64, biden_b64)
    
    print(f"Result: {result['message']}")
    
    if result["success"]:
        with open("obama_biden_swap.jpg", "wb") as f:
            f.write(base64.b64decode(result['output']))
        print("Saved: obama_biden_swap.jpg")
    else:
        if "trace" in result:
            print("Error trace:", result["trace"])
        # Save original anyway
        with open("output_original.jpg", "wb") as f:
            f.write(base64.b64decode(result['output']))
        print("Saved original: output_original.jpg")

if __name__ == "__main__":
    modal.runner.run(app)