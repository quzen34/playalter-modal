from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Form
from fastapi.responses import JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import modal
import cv2
import numpy as np
from typing import List, Optional, Dict, Any
import io
import base64
from PIL import Image
import logging
import asyncio
from pydantic import BaseModel

from services.flame_model import FLAMEModelService
from services.privacy_mask import PrivacyMaskGenerator
from services.face_swap import FaceSwapService

logger = logging.getLogger(__name__)

app = modal.App("playalter-api")

# Image configuration with all dependencies
image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install([
        "torch==2.1.0",
        "torchvision==0.16.0", 
        "torchaudio==2.1.0",
        "opencv-python==4.8.1.78",
        "mediapipe==0.10.7",
        "numpy==1.24.3",
        "Pillow==10.0.1",
        "scikit-image==0.21.0",
        "scipy==1.11.3",
        "trimesh==3.23.5",
        "pytorch3d==0.7.5",
        "face-alignment==1.3.5",
        "insightface==0.7.3",
        "onnxruntime-gpu==1.16.0",
        "fastapi==0.104.1",
        "uvicorn==0.24.0",
        "python-multipart==0.0.6",
        "aiofiles==23.2.1",
        "requests==2.31.0",
        "pydantic==2.4.2",
        "jinja2==3.1.2",
        "python-jose[cryptography]==3.3.0",
        "passlib[bcrypt]==1.7.4",
        "python-dotenv==1.0.0"
    ])
    .apt_install([
        "libgl1-mesa-glx",
        "libglib2.0-0", 
        "libsm6",
        "libxext6",
        "libxrender-dev",
        "libgomp1",
        "libgoogle-perftools4",
        "libtcmalloc-minimal4"
    ])
    .pip_install([
        "flame-pytorch @ git+https://github.com/soubhiksanyal/FLAME_PyTorch.git"
    ])
)

# Global services (initialized once)
flame_service = None
privacy_service = None
face_swap_service = None

# Pydantic models for request/response
class FaceAnalysisRequest(BaseModel):
    image_base64: str
    include_measurements: bool = True
    include_3d_mesh: bool = False

class PrivacyMaskRequest(BaseModel):
    image_base64: str
    mask_type: str = "blur"
    strength: float = 1.0
    create_levels: bool = False

class FaceSwapRequest(BaseModel):
    source_image_base64: str
    target_image_base64: str
    source_face_index: int = 0
    target_face_index: int = 0
    enhance_result: bool = True

class BatchProcessRequest(BaseModel):
    images_base64: List[str]
    operation: str  # "privacy_mask", "face_analysis", etc.
    parameters: Dict[str, Any] = {}

def initialize_services():
    """Initialize all services."""
    global flame_service, privacy_service, face_swap_service
    
    try:
        flame_service = FLAMEModelService()
        privacy_service = PrivacyMaskGenerator(flame_service)
        face_swap_service = FaceSwapService()
        logger.info("All services initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing services: {str(e)}")
        raise

def decode_base64_image(base64_string: str) -> np.ndarray:
    """Decode base64 string to numpy array image."""
    try:
        # Remove data URL prefix if present
        if base64_string.startswith('data:image'):
            base64_string = base64_string.split(',')[1]
        
        # Decode base64
        image_data = base64.b64decode(base64_string)
        
        # Convert to PIL Image
        pil_image = Image.open(io.BytesIO(image_data))
        
        # Convert to RGB if necessary
        if pil_image.mode != 'RGB':
            pil_image = pil_image.convert('RGB')
        
        # Convert to numpy array
        image_array = np.array(pil_image)
        
        # Convert RGB to BGR for OpenCV
        image_bgr = cv2.cvtColor(image_array, cv2.COLOR_RGB2BGR)
        
        return image_bgr
    except Exception as e:
        logger.error(f"Error decoding base64 image: {str(e)}")
        raise HTTPException(status_code=400, detail="Invalid image data")

def encode_image_to_base64(image: np.ndarray) -> str:
    """Encode numpy array image to base64 string."""
    try:
        # Convert BGR to RGB
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # Convert to PIL Image
        pil_image = Image.fromarray(image_rgb)
        
        # Encode to base64
        buffer = io.BytesIO()
        pil_image.save(buffer, format='JPEG', quality=95)
        
        base64_string = base64.b64encode(buffer.getvalue()).decode('utf-8')
        return base64_string
    except Exception as e:
        logger.error(f"Error encoding image to base64: {str(e)}")
        raise HTTPException(status_code=500, detail="Error encoding image")

@app.function(
    image=image,
    gpu="T4",
    memory=16384,
    timeout=3600,
    keep_warm=1,
    allow_concurrent_inputs=10
)
@modal.web_endpoint(method="GET", path="/")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "PLAYALTER Platform", "version": "1.0.0"}

@app.function(
    image=image,
    gpu="T4",
    memory=16384,
    timeout=3600,
    allow_concurrent_inputs=5
)
@modal.web_endpoint(method="POST", path="/api/face/analyze")
async def analyze_face_endpoint(request: FaceAnalysisRequest):
    """Analyze face using FLAME model."""
    try:
        global flame_service
        if flame_service is None:
            initialize_services()
        
        # Decode image
        image = decode_base64_image(request.image_base64)
        
        # Perform analysis
        analysis_result = flame_service.analyze_face(image)
        
        if not analysis_result.get('success', False):
            raise HTTPException(status_code=400, detail=analysis_result.get('error', 'Analysis failed'))
        
        response_data = {
            'success': True,
            'landmarks': analysis_result['landmarks'],
            'flame_parameters': analysis_result['flame_parameters']
        }
        
        if request.include_measurements:
            response_data['measurements'] = analysis_result['measurements']
        
        if request.include_3d_mesh:
            mesh_data = flame_service.create_3d_mesh(analysis_result['flame_parameters'])
            response_data['3d_mesh'] = mesh_data
        
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in face analysis endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.function(
    image=image,
    gpu="T4",
    memory=16384,
    timeout=3600,
    allow_concurrent_inputs=5
)
@modal.web_endpoint(method="POST", path="/api/privacy/mask")
async def create_privacy_mask_endpoint(request: PrivacyMaskRequest):
    """Create privacy mask for image."""
    try:
        global privacy_service
        if privacy_service is None:
            initialize_services()
        
        # Decode image
        image = decode_base64_image(request.image_base64)
        
        if request.create_levels:
            # Create multiple privacy levels
            result = privacy_service.create_privacy_levels(image)
            
            if not result.get('success', False):
                raise HTTPException(status_code=400, detail=result.get('error', 'Privacy mask creation failed'))
            
            # Encode all privacy levels
            encoded_levels = {}
            for level, level_image in result['privacy_levels'].items():
                encoded_levels[level] = encode_image_to_base64(level_image)
            
            return {
                'success': True,
                'privacy_levels': encoded_levels,
                'available_levels': list(encoded_levels.keys())
            }
        else:
            # Create single privacy mask
            result = privacy_service.generate_adaptive_mask(
                image, request.mask_type, request.strength
            )
            
            if not result.get('success', False):
                raise HTTPException(status_code=400, detail=result.get('error', 'Privacy mask creation failed'))
            
            return {
                'success': True,
                'masked_image': encode_image_to_base64(result['masked_image']),
                'measurements': result['measurements'],
                'mask_type': request.mask_type,
                'strength': request.strength
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in privacy mask endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.function(
    image=image,
    gpu="T4",
    memory=16384,
    timeout=3600,
    allow_concurrent_inputs=3
)
@modal.web_endpoint(method="POST", path="/api/face/swap")
async def face_swap_endpoint(request: FaceSwapRequest):
    """Perform face swap between two images."""
    try:
        global face_swap_service
        if face_swap_service is None:
            initialize_services()
        
        # Decode images
        source_image = decode_base64_image(request.source_image_base64)
        target_image = decode_base64_image(request.target_image_base64)
        
        # Perform face swap
        swap_result = face_swap_service.swap_faces(
            source_image, target_image,
            request.source_face_index, request.target_face_index
        )
        
        if not swap_result.get('success', False):
            raise HTTPException(status_code=400, detail=swap_result.get('error', 'Face swap failed'))
        
        return {
            'success': True,
            'result_image': encode_image_to_base64(swap_result['result_image']),
            'source_face_count': swap_result['source_face_count'],
            'target_face_count': swap_result['target_face_count']
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in face swap endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.function(
    image=image,
    gpu="T4",
    memory=16384,
    timeout=3600,
    allow_concurrent_inputs=3
)
@modal.web_endpoint(method="POST", path="/api/face/compatibility")
async def face_compatibility_endpoint(source_image_base64: str = Form(...), target_image_base64: str = Form(...)):
    """Analyze compatibility between source and target faces."""
    try:
        global face_swap_service
        if face_swap_service is None:
            initialize_services()
        
        # Decode images
        source_image = decode_base64_image(source_image_base64)
        target_image = decode_base64_image(target_image_base64)
        
        # Analyze compatibility
        compatibility_result = face_swap_service.analyze_face_compatibility(source_image, target_image)
        
        if not compatibility_result.get('success', False):
            raise HTTPException(status_code=400, detail=compatibility_result.get('error', 'Compatibility analysis failed'))
        
        return compatibility_result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in face compatibility endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.function(
    image=image,
    gpu="T4",
    memory=24576,
    timeout=7200,
    allow_concurrent_inputs=2
)
@modal.web_endpoint(method="POST", path="/api/batch/process")
async def batch_process_endpoint(request: BatchProcessRequest):
    """Process multiple images in batch."""
    try:
        if len(request.images_base64) == 0:
            raise HTTPException(status_code=400, detail="No images provided")
        
        if len(request.images_base64) > 10:
            raise HTTPException(status_code=400, detail="Maximum 10 images allowed per batch")
        
        global privacy_service, face_swap_service, flame_service
        if privacy_service is None:
            initialize_services()
        
        results = []
        
        for i, image_base64 in enumerate(request.images_base64):
            try:
                image = decode_base64_image(image_base64)
                
                if request.operation == "privacy_mask":
                    mask_type = request.parameters.get('mask_type', 'blur')
                    strength = request.parameters.get('strength', 1.0)
                    result = privacy_service.generate_adaptive_mask(image, mask_type, strength)
                    
                    if result.get('success', False):
                        results.append({
                            'index': i,
                            'success': True,
                            'result_image': encode_image_to_base64(result['masked_image']),
                            'measurements': result['measurements']
                        })
                    else:
                        results.append({
                            'index': i,
                            'success': False,
                            'error': result.get('error', 'Unknown error')
                        })
                
                elif request.operation == "face_analysis":
                    result = flame_service.analyze_face(image)
                    
                    if result.get('success', False):
                        results.append({
                            'index': i,
                            'success': True,
                            'landmarks': result['landmarks'],
                            'measurements': result['measurements'],
                            'flame_parameters': result['flame_parameters']
                        })
                    else:
                        results.append({
                            'index': i,
                            'success': False,
                            'error': result.get('error', 'Unknown error')
                        })
                
                else:
                    results.append({
                        'index': i,
                        'success': False,
                        'error': f'Unsupported operation: {request.operation}'
                    })
                    
            except Exception as e:
                results.append({
                    'index': i,
                    'success': False,
                    'error': str(e)
                })
        
        successful_results = [r for r in results if r['success']]
        
        return {
            'success': True,
            'total_processed': len(request.images_base64),
            'successful_count': len(successful_results),
            'failed_count': len(results) - len(successful_results),
            'results': results
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in batch process endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.function(
    image=image,
    gpu="T4",
    memory=16384,
    timeout=3600,
    allow_concurrent_inputs=10
)
@modal.web_endpoint(method="GET", path="/api/services/status")
async def services_status():
    """Get status of all services."""
    try:
        status = {
            'flame_service': 'initialized' if flame_service else 'not_initialized',
            'privacy_service': 'initialized' if privacy_service else 'not_initialized',
            'face_swap_service': 'initialized' if face_swap_service else 'not_initialized',
            'gpu_available': torch.cuda.is_available() if 'torch' in globals() else False,
            'supported_operations': [
                'face_analysis',
                'privacy_mask',
                'face_swap',
                'batch_process',
                'face_compatibility'
            ],
            'supported_mask_types': ['blur', 'pixelate', 'noise', 'synthetic']
        }
        
        return status
        
    except Exception as e:
        logger.error(f"Error getting services status: {str(e)}")
        return {'error': str(e)}

@app.function(
    image=image,
    gpu="T4",
    memory=16384,
    timeout=3600,
    allow_concurrent_inputs=10
)
@modal.web_endpoint(method="POST", path="/api/services/initialize")
async def initialize_services_endpoint():
    """Force initialization of all services."""
    try:
        initialize_services()
        return {
            'success': True,
            'message': 'All services initialized successfully',
            'services': {
                'flame_service': 'ready',
                'privacy_service': 'ready', 
                'face_swap_service': 'ready'
            }
        }
    except Exception as e:
        logger.error(f"Error initializing services: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Service initialization failed: {str(e)}")

if __name__ == "__main__":
    app.deploy("playalter-api")