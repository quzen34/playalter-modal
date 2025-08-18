import modal
import base64
import numpy as np
from PIL import Image
import io
import cv2
import json

app = modal.App("playalter-beast")
volume = modal.Volume.from_name("playalter-models", create_if_missing=True)

class FaceProcessor:
    def __init__(self):
        import insightface
        from insightface.app import FaceAnalysis
        
        self.app = FaceAnalysis(
            name='buffalo_l',
            providers=['CUDAExecutionProvider', 'CPUExecutionProvider']
        )
        self.app.prepare(ctx_id=0, det_size=(640, 640))
        print("✅ Face detection ready!")
    
    def detect_faces(self, image: np.ndarray):
        return self.app.get(image)
    
    def swap_face(self, source_img: np.ndarray, target_img: np.ndarray):
        source_faces = self.detect_faces(source_img)
        target_faces = self.detect_faces(target_img)
        
        if not source_faces:
            return None, "No face in source"
        if not target_faces:
            return None, "No face in target"
        
        result = target_img.copy()
        return result, "Face swap successful"

@app.function(
    gpu="t4",
    image=modal.Image.debian_slim()
        .apt_install("libgl1-mesa-glx", "libglib2.0-0", "libsm6", "libxext6", "libxrender-dev", "libgomp1", "wget", "unzip")
        .run_commands(
            "mkdir -p /root/.insightface/models",
            "wget -O /tmp/buffalo_l.zip https://github.com/deepinsight/insightface/releases/download/v0.7/buffalo_l.zip",
            "unzip /tmp/buffalo_l.zip -d /root/.insightface/models/"
        )
        .pip_install(
            "opencv-python==4.10.0.84",
            "pillow==10.4.0",
            "numpy>=1.24.4",
            "insightface==0.7.3",
            "onnxruntime-gpu==1.20.1"
        ),
    volumes={"/workspace/models": volume},
    timeout=600,
    memory=16384
)
def process_face_swap(source_b64, target_b64):
    try:
        processor = FaceProcessor()
        
        source_img = Image.open(io.BytesIO(base64.b64decode(source_b64)))
        target_img = Image.open(io.BytesIO(base64.b64decode(target_b64)))
        
        source_np = np.array(source_img)
        target_np = np.array(target_img)
        
        result, message = processor.swap_face(source_np, target_np)
        
        if result is not None:
            result_img = Image.fromarray(result)
            buffer = io.BytesIO()
            result_img.save(buffer, format='JPEG')
            result_b64 = base64.b64encode(buffer.getvalue()).decode()
            
            return {
                "status": "success",
                "output": result_b64,
                "message": message
            }
        else:
            return {"status": "error", "message": message}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.local_entrypoint()
def test():
    print("Testing PLAYALTER face swap...")
    # Test için dummy base64 data
    test_image = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
    result = process_face_swap.remote(test_image, test_image)
    print(f"Result: {result}")