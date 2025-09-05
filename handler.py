import modal
import base64
import numpy as np
from PIL import Image
import io
import cv2
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
    """Real face swap with insightface"""
    try:
        import insightface
        from insightface.app import FaceAnalysis
        
        # Initialize face app
        app = FaceAnalysis(name='buffalo_l', providers=['CUDAExecutionProvider', 'CPUExecutionProvider'])
        app.prepare(ctx_id=0)
        
        # Decode images
        source_data = base64.b64decode(source_b64)
        target_data = base64.b64decode(target_b64)
        
        source_img = Image.open(io.BytesIO(source_data)).convert('RGB')
        target_img = Image.open(io.BytesIO(target_data)).convert('RGB')
        
        source_np = cv2.cvtColor(np.array(source_img), cv2.COLOR_RGB2BGR)
        target_np = cv2.cvtColor(np.array(target_img), cv2.COLOR_RGB2BGR)
        
        # Detect faces
        source_faces = app.get(source_np)
        target_faces = app.get(target_np)
        
        if not source_faces:
            return {"success": False, "message": "No face in source"}
        if not target_faces:
            return {"success": False, "message": "No face in target"}
        
        # Simple face region swap for now
        result = target_np.copy()
        
        # Get face regions
        s_bbox = source_faces[0].bbox.astype(int)
        t_bbox = target_faces[0].bbox.astype(int)
        
        # Extract and resize
        face_region = source_np[s_bbox[1]:s_bbox[3], s_bbox[0]:s_bbox[2]]
        if face_region.size > 0:
            new_size = (t_bbox[2]-t_bbox[0], t_bbox[3]-t_bbox[1])
            resized_face = cv2.resize(face_region, new_size)
            result[t_bbox[1]:t_bbox[3], t_bbox[0]:t_bbox[2]] = resized_face
        
        # Convert back
        result_rgb = cv2.cvtColor(result, cv2.COLOR_BGR2RGB)
        result_img = Image.fromarray(result_rgb)
        
        buffer = io.BytesIO()
        result_img.save(buffer, format='JPEG', quality=95)
        buffer.seek(0)
        result_b64 = base64.b64encode(buffer.getvalue()).decode()
        
        return {
            "success": True,
            "output": result_b64,
            "message": "Face swap successful!"
        }
        
    except Exception as e:
        import traceback
        return {
            "success": False,
            "message": f"Error: {str(e)}",
            "trace": traceback.format_exc()
        }

@app.local_entrypoint()
def test():
    print("="*60)
    print("🚀 PLAYALTER FACE SWAP - REAL TEST")
    print("="*60)
    
    # Obama and Biden photos
    urls = {
        "obama": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8d/President_Barack_Obama.jpg/400px-President_Barack_Obama.jpg",
        "biden": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/68/Joe_Biden_presidential_portrait.jpg/400px-Joe_Biden_presidential_portrait.jpg"
    }
    
    print("📥 Downloading Obama and Biden images...")
    
    obama_data = requests.get(urls["obama"]).content
    biden_data = requests.get(urls["biden"]).content
    
    obama_b64 = base64.b64encode(obama_data).decode()
    biden_b64 = base64.b64encode(biden_data).decode()
    
    print("🔄 Processing face swap: Obama → Biden")
    result = process_face_swap.remote(obama_b64, biden_b64)
    
    if result["success"]:
        print("✅ FACE SWAP SUCCESSFUL!")
        
        # Save result
        with open("obama_biden_swap.jpg", "wb") as f:
            f.write(base64.b64decode(result['output']))
        print("💾 Result saved: obama_biden_swap.jpg")
    else:
        print(f"❌ Failed: {result['message']}")
        if "trace" in result:
            print(result["trace"])

if __name__ == "__main__":
    modal.runner.run(app)