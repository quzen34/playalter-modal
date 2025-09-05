import cv2
import numpy as np
import torch
import onnxruntime as ort
from typing import Dict, Optional, Tuple, List
import logging
from pathlib import Path
import insightface
from insightface.app import FaceAnalysis
from insightface.model_zoo import get_model
import requests
import os

logger = logging.getLogger(__name__)

class FaceSwapService:
    """Advanced face swap service using InSwapper model."""
    
    def __init__(self, model_path: Optional[str] = None):
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.face_analyzer = None
        self.face_swapper = None
        self.face_enhancer = None
        self.model_path = model_path or "/tmp/inswapper_models"
        
        self._setup_models()
    
    def _setup_models(self):
        """Initialize face analysis and swapping models."""
        try:
            # Initialize face analyzer
            self.face_analyzer = FaceAnalysis(name='buffalo_l')
            self.face_analyzer.prepare(ctx_id=0 if self.device == 'cuda' else -1, det_size=(640, 640))
            
            # Download and setup InSwapper model
            inswapper_model_path = self._download_inswapper_model()
            if inswapper_model_path and os.path.exists(inswapper_model_path):
                self.face_swapper = insightface.model_zoo.get_model(inswapper_model_path)
            
            logger.info("Face swap models initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing face swap models: {str(e)}")
            raise
    
    def _download_inswapper_model(self) -> Optional[str]:
        """Download InSwapper model if not present."""
        try:
            model_dir = Path(self.model_path)
            model_dir.mkdir(parents=True, exist_ok=True)
            
            model_file = model_dir / "inswapper_128.onnx"
            
            if not model_file.exists():
                logger.info("Downloading InSwapper model...")
                # Note: In production, you would download from the official repository
                # This is a placeholder for the actual download URL
                model_url = "https://github.com/deepinsight/insightface/releases/download/v0.7/inswapper_128.onnx"
                
                try:
                    response = requests.get(model_url, stream=True)
                    if response.status_code == 200:
                        with open(model_file, 'wb') as f:
                            for chunk in response.iter_content(chunk_size=8192):
                                f.write(chunk)
                        logger.info("InSwapper model downloaded successfully")
                    else:
                        logger.warning("Could not download InSwapper model, using fallback")
                        return None
                except Exception as e:
                    logger.warning(f"Download failed: {str(e)}, using fallback")
                    return None
            
            return str(model_file)
            
        except Exception as e:
            logger.error(f"Error setting up InSwapper model: {str(e)}")
            return None
    
    def extract_face_embedding(self, image: np.ndarray) -> Optional[Dict[str, any]]:
        """Extract face embedding from image."""
        try:
            faces = self.face_analyzer.get(image)
            if len(faces) == 0:
                return None
            
            # Use the largest face
            face = max(faces, key=lambda x: (x.bbox[2] - x.bbox[0]) * (x.bbox[3] - x.bbox[1]))
            
            return {
                'embedding': face.embedding,
                'bbox': face.bbox,
                'kps': face.kps,
                'det_score': face.det_score
            }
            
        except Exception as e:
            logger.error(f"Error extracting face embedding: {str(e)}")
            return None
    
    def swap_faces(self, source_image: np.ndarray, target_image: np.ndarray,
                   source_face_index: int = 0, target_face_index: int = 0) -> Dict[str, any]:
        """Perform face swap between source and target images."""
        try:
            # Extract faces from both images
            source_faces = self.face_analyzer.get(source_image)
            target_faces = self.face_analyzer.get(target_image)
            
            if len(source_faces) == 0:
                return {'error': 'No face detected in source image', 'success': False}
            
            if len(target_faces) == 0:
                return {'error': 'No face detected in target image', 'success': False}
            
            # Select faces to swap
            source_face = source_faces[min(source_face_index, len(source_faces) - 1)]
            target_face = target_faces[min(target_face_index, len(target_faces) - 1)]
            
            # Perform face swap
            if self.face_swapper is not None:
                result_image = self.face_swapper.get(target_image, target_face, source_face, paste_back=True)
            else:
                # Fallback implementation
                result_image = self._manual_face_swap(source_image, target_image, source_face, target_face)
            
            # Post-process for better blending
            result_image = self._enhance_swap_result(result_image, target_image, target_face)
            
            return {
                'result_image': result_image,
                'source_face_count': len(source_faces),
                'target_face_count': len(target_faces),
                'success': True
            }
            
        except Exception as e:
            logger.error(f"Error in face swap: {str(e)}")
            return {'error': str(e), 'success': False}
    
    def _manual_face_swap(self, source_image: np.ndarray, target_image: np.ndarray,
                         source_face: any, target_face: any) -> np.ndarray:
        """Manual face swap implementation as fallback."""
        try:
            result_image = target_image.copy()
            
            # Extract face regions
            source_bbox = source_face.bbox.astype(int)
            target_bbox = target_face.bbox.astype(int)
            
            # Extract source face
            sx1, sy1, sx2, sy2 = source_bbox
            source_face_region = source_image[sy1:sy2, sx1:sx2]
            
            # Resize to target face size
            tx1, ty1, tx2, ty2 = target_bbox
            target_width = tx2 - tx1
            target_height = ty2 - ty1
            
            resized_source_face = cv2.resize(source_face_region, (target_width, target_height))
            
            # Create mask for blending
            mask = np.ones((target_height, target_width), dtype=np.uint8) * 255
            
            # Apply Gaussian blur to mask for smooth blending
            mask_blurred = cv2.GaussianBlur(mask, (15, 15), 0)
            mask_normalized = mask_blurred.astype(np.float32) / 255.0
            
            # Blend faces
            target_region = result_image[ty1:ty2, tx1:tx2]
            
            for c in range(3):
                result_image[ty1:ty2, tx1:tx2, c] = (
                    resized_source_face[:, :, c] * mask_normalized +
                    target_region[:, :, c] * (1 - mask_normalized)
                ).astype(np.uint8)
            
            return result_image
            
        except Exception as e:
            logger.error(f"Error in manual face swap: {str(e)}")
            return target_image
    
    def _enhance_swap_result(self, swapped_image: np.ndarray, original_image: np.ndarray,
                           target_face: any) -> np.ndarray:
        """Enhance the face swap result for better quality."""
        try:
            # Apply color correction
            corrected = self._apply_color_correction(swapped_image, original_image, target_face)
            
            # Apply sharpening
            enhanced = self._apply_sharpening(corrected)
            
            # Apply noise reduction
            denoised = self._apply_noise_reduction(enhanced)
            
            return denoised
            
        except Exception as e:
            logger.error(f"Error enhancing swap result: {str(e)}")
            return swapped_image
    
    def _apply_color_correction(self, swapped_image: np.ndarray, original_image: np.ndarray,
                              target_face: any) -> np.ndarray:
        """Apply color correction to match lighting conditions."""
        try:
            bbox = target_face.bbox.astype(int)
            x1, y1, x2, y2 = bbox
            
            # Get face regions
            swapped_face = swapped_image[y1:y2, x1:x2]
            original_face = original_image[y1:y2, x1:x2]
            
            # Calculate color statistics
            swapped_mean = np.mean(swapped_face, axis=(0, 1))
            original_mean = np.mean(original_face, axis=(0, 1))
            
            swapped_std = np.std(swapped_face, axis=(0, 1))
            original_std = np.std(original_face, axis=(0, 1))
            
            # Apply color transfer
            corrected_face = swapped_face.copy().astype(np.float32)
            for c in range(3):
                if swapped_std[c] > 0:
                    corrected_face[:, :, c] = (
                        (corrected_face[:, :, c] - swapped_mean[c]) * 
                        (original_std[c] / swapped_std[c]) + original_mean[c]
                    )
            
            corrected_face = np.clip(corrected_face, 0, 255).astype(np.uint8)
            
            # Apply correction to result
            result = swapped_image.copy()
            result[y1:y2, x1:x2] = corrected_face
            
            return result
            
        except Exception as e:
            logger.error(f"Error in color correction: {str(e)}")
            return swapped_image
    
    def _apply_sharpening(self, image: np.ndarray) -> np.ndarray:
        """Apply sharpening filter."""
        try:
            kernel = np.array([[-1, -1, -1],
                              [-1,  9, -1],
                              [-1, -1, -1]])
            sharpened = cv2.filter2D(image, -1, kernel)
            
            # Blend with original for subtle effect
            alpha = 0.3
            result = cv2.addWeighted(image, 1 - alpha, sharpened, alpha, 0)
            
            return result
            
        except Exception as e:
            logger.error(f"Error in sharpening: {str(e)}")
            return image
    
    def _apply_noise_reduction(self, image: np.ndarray) -> np.ndarray:
        """Apply noise reduction."""
        try:
            # Apply bilateral filter for noise reduction while preserving edges
            denoised = cv2.bilateralFilter(image, 9, 75, 75)
            return denoised
            
        except Exception as e:
            logger.error(f"Error in noise reduction: {str(e)}")
            return image
    
    def multi_face_swap(self, source_images: List[np.ndarray], target_image: np.ndarray) -> Dict[str, any]:
        """Perform multi-face swap with multiple source faces."""
        try:
            target_faces = self.face_analyzer.get(target_image)
            
            if len(target_faces) == 0:
                return {'error': 'No faces detected in target image', 'success': False}
            
            result_image = target_image.copy()
            swapped_faces = 0
            
            for i, source_image in enumerate(source_images):
                if i >= len(target_faces):
                    break
                
                source_faces = self.face_analyzer.get(source_image)
                if len(source_faces) > 0:
                    source_face = source_faces[0]  # Use first face from source
                    target_face = target_faces[i]  # Use corresponding target face
                    
                    if self.face_swapper is not None:
                        result_image = self.face_swapper.get(result_image, target_face, source_face, paste_back=True)
                    else:
                        result_image = self._manual_face_swap(source_image, result_image, source_face, target_face)
                    
                    swapped_faces += 1
            
            # Enhance final result
            result_image = self._enhance_swap_result(result_image, target_image, target_faces[0])
            
            return {
                'result_image': result_image,
                'swapped_faces': swapped_faces,
                'total_target_faces': len(target_faces),
                'success': True
            }
            
        except Exception as e:
            logger.error(f"Error in multi-face swap: {str(e)}")
            return {'error': str(e), 'success': False}
    
    def analyze_face_compatibility(self, source_image: np.ndarray, target_image: np.ndarray) -> Dict[str, any]:
        """Analyze compatibility between source and target faces."""
        try:
            source_face_data = self.extract_face_embedding(source_image)
            target_face_data = self.extract_face_embedding(target_image)
            
            if not source_face_data or not target_face_data:
                return {'error': 'Could not detect faces in one or both images', 'success': False}
            
            # Calculate similarity
            source_embedding = source_face_data['embedding']
            target_embedding = target_face_data['embedding']
            
            # Cosine similarity
            similarity = np.dot(source_embedding, target_embedding) / (
                np.linalg.norm(source_embedding) * np.linalg.norm(target_embedding)
            )
            
            # Calculate face size compatibility
            source_bbox = source_face_data['bbox']
            target_bbox = target_face_data['bbox']
            
            source_area = (source_bbox[2] - source_bbox[0]) * (source_bbox[3] - source_bbox[1])
            target_area = (target_bbox[2] - target_bbox[0]) * (target_bbox[3] - target_bbox[1])
            
            size_ratio = min(source_area, target_area) / max(source_area, target_area)
            
            return {
                'similarity_score': float(similarity),
                'size_compatibility': float(size_ratio),
                'source_face_quality': float(source_face_data['det_score']),
                'target_face_quality': float(target_face_data['det_score']),
                'compatibility_rating': self._calculate_compatibility_rating(similarity, size_ratio),
                'success': True
            }
            
        except Exception as e:
            logger.error(f"Error analyzing face compatibility: {str(e)}")
            return {'error': str(e), 'success': False}
    
    def _calculate_compatibility_rating(self, similarity: float, size_ratio: float) -> str:
        """Calculate overall compatibility rating."""
        combined_score = (similarity + size_ratio) / 2
        
        if combined_score > 0.8:
            return "Excellent"
        elif combined_score > 0.6:
            return "Good"
        elif combined_score > 0.4:
            return "Fair"
        else:
            return "Poor"
    
    def batch_face_swap(self, source_image: np.ndarray, target_images: List[np.ndarray]) -> List[Dict[str, any]]:
        """Perform face swap on multiple target images."""
        results = []
        
        for i, target_image in enumerate(target_images):
            logger.info(f"Processing face swap {i+1}/{len(target_images)}")
            result = self.swap_faces(source_image, target_image)
            results.append(result)
        
        return results