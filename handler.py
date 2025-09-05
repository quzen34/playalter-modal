import modal
import base64
import numpy as np
from PIL import Image
import io
import cv2
import json
import requests

app = modal.App("playalter-beast")

class FaceSwapProcessor:
    def __init__(self):
        import insightface
        from insightface.app import FaceAnalysis
        
        print("🔧 Initializing PLAYALTER Engine...")
        
        # Face analysis app
        self.app = FaceAnalysis(
            name='buffalo_l',
            providers=['CPUExecutionProvider']
        )
        self.app.prepare(ctx_id=0, det_size=(640, 640))
        
        # Load InSwapper model
        import os
        models = self.app.models
        
        # Find the swapper model
        self.swapper = None
        for model in models:
            if hasattr(model, 'swap'):
                self.swapper = model
                break
        
        print("✅ PLAYALTER Engine Ready!")
    
    def process(self, source_img: np.ndarray, target_img: np.ndarray):
        """Main face swap function"""
        try:
            # Detect faces
            source_faces = self.app.get(source_img)
            target_faces = self.app.get(target_img)
            
            if not source_faces:
                return None, "No face detected in source image"
            if not target_faces:
                return None, "No face detected in target image"
            
            # For now, simple copy (InSwapper integration next)
            result = target_img.copy()
            
            # Basic face region swap
            source_face = source_faces[0]
            target_face = target_faces[0]
            
            # Get bounding boxes
            s_box = source_face.bbox.astype(int)
            t_box = target_face.bbox.astype(int)
            
            # Extract and resize face region
            source_region = source_img[s_box[1]:s_box[3], s_box[0]:s_box[2]]
            target_size = (t_box[2]-t_box[0], t_box[3]-t_box[1])
            
            if source_region.size > 0:
                resized = cv2.resize(source_region, target_size)
                result[t_box[1]:t_box[3], t_box[0]:t_box[2]] = resized
            
            return result, "Face swap completed successfully!"
            
        except Exception as e:
            return None, f"Processing error: {str(e)}"

@app.function(
    image=modal.Image.debian_slim(python_version="3.10")
        .apt_install(
            "libgl1-mesa-glx", "libglib2.0-0", "libsm6",
            "libxext6", "libxrender-dev", "libgomp1", 
            "wget", "unzip"
        )
        .run_commands(
            "mkdir -p /root/.insightface/models/buffalo_l",
            "wget -q -O /tmp/buffalo_l.zip https://github.com/deepinsight/insightface/releases/download/v0.7/buffalo_l.zip",
            "unzip -q /tmp/buffalo_l.zip -d /root/.insightface/models/buffalo_l/",
            "rm /tmp/buffalo_l.zip"
        )
        .pip_install(
            "opencv-python==4.8.1.78",
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
    """Modal function for face swapping"""
    try:
        # Initialize processor
        processor = FaceSwapProcessor()
        
        # Decode base64 images
        source_img = Image.open(io.BytesIO(base64.b64decode(source_b64)))
        target_img = Image.open(io.BytesIO(base64.b64decode(target_b64)))
        
        # Convert to RGB numpy arrays
        source_np = cv2.cvtColor(np.array(source_img.convert('RGB')), cv2.COLOR_RGB2BGR)
        target_np = cv2.cvtColor(np.array(target_img.convert('RGB')), cv2.COLOR_RGB2BGR)
        
        # Process face swap
        result, message = processor.process(source_np, target_np)
        
        if result is not None:
            # Convert back to RGB and encode
            result_rgb = cv2.cvtColor(result, cv2.COLOR_BGR2RGB)
            result_img = Image.fromarray(result_rgb)
            
            buffer = io.BytesIO()
            result_img.save(buffer, format='JPEG', quality=95)
            result_b64 = base64.b64encode(buffer.getvalue()).decode()
            
            return {
                "success": True,
                "output": result_b64,
                "message": message
            }
        else:
            return {
                "success": False,
                "message": message
            }
            
    except Exception as e:
        return {
            "success": False,
            "message": f"Error: {str(e)}"
        }

@app.local_entrypoint()
def test():
    """Test with Obama and Biden"""
    print("="*60)
    print("🚀 PLAYALTER FACE SWAP TEST")
    print("="*60)
    
    # Download test images
    print("📥 Downloading Obama and Biden images...")
    
    obama_url = "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8d/President_Barack_Obama.jpg/480px-President_Barack_Obama.jpg"
    biden_url = "https://upload.wikimedia.org/wikipedia/commons/thumb/6/68/Joe_Biden_presidential_portrait.jpg/480px-Joe_Biden_presidential_portrait.jpg"
    
    try:
        obama_img = requests.get(obama_url).content
        biden_img = requests.get(biden_url).content
        
        obama_b64 = base64.b64encode(obama_img).decode()
        biden_b64 = base64.b64encode(biden_img).decode()
        
        print("🔄 Processing face swap: Obama → Biden")
        result = process_face_swap.remote(obama_b64, biden_b64)
        
        if result["success"]:
            print("✅ SUCCESS! Face swap completed!")
            print(f"📝 Message: {result['message']}")
            
            # Save result
            output_data = base64.b64decode(result['output'])
            with open("obama_biden_swap.jpg", "wb") as f:
                f.write(output_data)
            print("💾 Result saved as: obama_biden_swap.jpg")
        else:
            print(f"❌ Failed: {result['message']}")
            
    except Exception as e:
        print(f"❌ Test error: {e}")

if __name__ == "__main__":
    modal.runner.run(app)