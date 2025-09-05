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
            # InSwapper modelini indir
            "mkdir -p /root/.insightface/models/inswapper",
            "wget -q -O /root/.insightface/models/inswapper_128.onnx https://github.com/facefusion/facefusion-assets/releases/download/models/inswapper_128.onnx",
            "rm -f /tmp/buffalo_l.zip"
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
    """Enhanced face swap with InSwapper support"""
    try:
        import cv2
        import insightface
        from insightface.app import FaceAnalysis
        import os
        
        print("Initializing face swap engine...")
        
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
        
        # Initialize face analysis
        app = FaceAnalysis(
            name='buffalo_l',
            root='/root/.insightface',
            providers=['CUDAExecutionProvider', 'CPUExecutionProvider']
        )
        app.prepare(ctx_id=0, det_size=(640, 640))
        
        # Try to load InSwapper model
        swapper = None
        inswapper_path = '/root/.insightface/models/inswapper_128.onnx'
        if os.path.exists(inswapper_path):
            try:
                swapper = insightface.model_zoo.get_model(inswapper_path, providers=['CUDAExecutionProvider', 'CPUExecutionProvider'])
                print("InSwapper model loaded!")
            except:
                print("InSwapper load failed, using basic swap")
        
        # Detect faces
        source_faces = app.get(source_cv)
        target_faces = app.get(target_cv)
        
        print(f"Faces detected: Source={len(source_faces) if source_faces else 0}, Target={len(target_faces) if target_faces else 0}")
        
        # Perform swap
        result = target_cv.copy()
        
        if source_faces and target_faces:
            if swapper:
                # Use InSwapper for better quality
                try:
                    result = swapper.get(result, target_faces[0], source_faces[0], paste_back=True)
                    print("InSwapper swap applied!")
                except:
                    # Fallback to basic swap
                    print("InSwapper failed, using basic swap")
                    s_bbox = source_faces[0].bbox.astype(int)
                    t_bbox = target_faces[0].bbox.astype(int)
                    face = source_cv[s_bbox[1]:s_bbox[3], s_bbox[0]:s_bbox[2]]
                    if face.size > 0:
                        face_resized = cv2.resize(face, (t_bbox[2]-t_bbox[0], t_bbox[3]-t_bbox[1]))
                        # Blend edges for better result
                        mask = np.ones_like(face_resized, dtype=np.float32)
                        mask = cv2.GaussianBlur(mask, (21, 21), 10)
                        center = (t_bbox[0] + (t_bbox[2]-t_bbox[0])//2, t_bbox[1] + (t_bbox[3]-t_bbox[1])//2)
                        result = cv2.seamlessClone(face_resized, result, (mask * 255).astype(np.uint8)[:,:,0], center, cv2.NORMAL_CLONE)
                        print("Enhanced basic swap applied!")
            else:
                # Basic swap with seamless clone
                s_bbox = source_faces[0].bbox.astype(int)
                t_bbox = target_faces[0].bbox.astype(int)
                face = source_cv[s_bbox[1]:s_bbox[3], s_bbox[0]:s_bbox[2]]
                if face.size > 0:
                    face_resized = cv2.resize(face, (t_bbox[2]-t_bbox[0], t_bbox[3]-t_bbox[1]))
                    # Create mask for seamless cloning
                    mask = 255 * np.ones(face_resized.shape, dtype=np.uint8)
                    center = (t_bbox[0] + (t_bbox[2]-t_bbox[0])//2, t_bbox[1] + (t_bbox[3]-t_bbox[1])//2)
                    try:
                        result = cv2.seamlessClone(face_resized, result, mask, center, cv2.NORMAL_CLONE)
                        print("Seamless clone applied!")
                    except:
                        # Ultra fallback - direct paste
                        result[t_bbox[1]:t_bbox[3], t_bbox[0]:t_bbox[2]] = face_resized
                        print("Direct paste applied!")
        
        # Enhance quality
        result = cv2.bilateralFilter(result, 9, 75, 75)
        
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
    print("PLAYALTER ENHANCED FACE SWAP")
    print("="*60)
    
    # Real face images
    urls = {
        "person1": "https://raw.githubusercontent.com/ageitgey/face_recognition/master/examples/biden.jpg",
        "person2": "https://raw.githubusercontent.com/ageitgey/face_recognition/master/examples/obama.jpg"
    }
    
    print("Downloading test faces...")
    
    try:
        img1_data = requests.get(urls["person1"]).content
        img2_data = requests.get(urls["person2"]).content
        
        img1_b64 = base64.b64encode(img1_data).decode()
        img2_b64 = base64.b64encode(img2_data).decode()
        
        print("Processing face swap with enhancements...")
        result = process_face_swap.remote(img1_b64, img2_b64)
        
        print(f"Result: {result.get('message')}")
        
        if result.get("success") and result.get("output"):
            with open("enhanced_swap.jpg", "wb") as f:
                f.write(base64.b64decode(result['output']))
            print("✅ SAVED: enhanced_swap.jpg")
            
            msg = result.get('message', '')
            if 'Source faces: 0' in msg:
                print("⚠️ No faces detected")
            else:
                print("✅ FACE SWAP COMPLETE WITH ENHANCEMENTS!")
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    modal.runner.run(app)