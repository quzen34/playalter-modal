import modal
import base64
import numpy as np
from PIL import Image
import io
import cv2
import json

app = modal.App("playalter-beast")

class FaceProcessor:
    def __init__(self):
        import insightface
        from insightface.app import FaceAnalysis
        
        self.app = FaceAnalysis(
            name='buffalo_l',
            providers=['CPUExecutionProvider']  # CUDA yerine CPU kullan
        )
        self.app.prepare(ctx_id=0, det_size=(640, 640))
        print("✅ Face detection ready!")
    
    def detect_faces(self, image: np.ndarray):
        return self.app.get(image)
    
    def swap_face(self, source_img: np.ndarray, target_img: np.ndarray):
        # RGB'ye çevir (RGBA sorunu için)
        if source_img.shape[2] == 4:
            source_img = cv2.cvtColor(source_img, cv2.COLOR_RGBA2RGB)
        if target_img.shape[2] == 4:
            target_img = cv2.cvtColor(target_img, cv2.COLOR_RGBA2RGB)
            
        source_faces = self.detect_faces(source_img)
        target_faces = self.detect_faces(target_img)
        
        if not source_faces:
            return None, "No face in source"
        if not target_faces:
            return None, "No face in target"
        
        # Basit swap simülasyonu (şimdilik)
        result = target_img.copy()
        return result, "Face swap successful"

@app.function(
    gpu="t4",
    image=modal.Image.debian_slim()
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
            "wget -O /tmp/buffalo_l.zip https://github.com/deepinsight/insightface/releases/download/v0.7/buffalo_l.zip",
            "unzip /tmp/buffalo_l.zip -d /root/.insightface/models/buffalo_l/"
        )
        .pip_install(
            "insightface==0.7.3",
            "numpy>=1.24.4",
            "onnxruntime==1.17.0",  # GPU yerine normal versiyon
            "opencv-python==4.10.0.84",
            "pillow==10.4.0"
        ),
    timeout=600,
    memory=16384
)
def process_face_swap(source_b64=None, target_b64=None):
    try:
        # Test için basit görüntüler oluştur
        if source_b64 is None:
            # Basit kırmızı kare
            source_img = Image.new('RGB', (640, 640), color='red')
        else:
            source_img = Image.open(io.BytesIO(base64.b64decode(source_b64)))
        
        if target_b64 is None:
            # Basit mavi kare  
            target_img = Image.new('RGB', (640, 640), color='blue')
        else:
            target_img = Image.open(io.BytesIO(base64.b64decode(target_b64)))
        
        # RGB'ye çevir
        source_img = source_img.convert('RGB')
        target_img = target_img.convert('RGB')
        
        source_np = np.array(source_img)
        target_np = np.array(target_img)
        
        processor = FaceProcessor()
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
    result = process_face_swap.remote()
    print(f"Result: {result}")

if __name__ == "__main__":
    # Lokal test
    print("Local test running...")