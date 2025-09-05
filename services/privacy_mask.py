import cv2
import numpy as np
import torch
from typing import Dict, List, Tuple, Optional
import logging
from pathlib import Path
import mediapipe as mp
from .flame_model import FLAMEModelService

logger = logging.getLogger(__name__)

class PrivacyMaskGenerator:
    """Advanced privacy mask generator using FLAME model for precise face measurements."""
    
    def __init__(self, flame_service: Optional[FLAMEModelService] = None):
        self.flame_service = flame_service or FLAMEModelService()
        self.mp_face_mesh = mp.solutions.face_mesh.FaceMesh(
            static_image_mode=True,
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5
        )
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_drawing_styles = mp.solutions.drawing_styles
        
    def generate_adaptive_mask(self, image: np.ndarray, mask_type: str = "blur", 
                             strength: float = 1.0) -> Dict[str, any]:
        """Generate adaptive privacy mask based on FLAME face measurements."""
        try:
            # Analyze face with FLAME model
            flame_analysis = self.flame_service.analyze_face(image)
            if not flame_analysis.get('success', False):
                return {'error': 'Face analysis failed', 'success': False}
            
            measurements = flame_analysis['measurements']
            landmarks = np.array(flame_analysis['landmarks'])
            
            # Create mask based on face measurements
            mask = self._create_measurement_based_mask(image, landmarks, measurements)
            
            # Apply privacy effect
            if mask_type == "blur":
                masked_image = self._apply_adaptive_blur(image, mask, measurements, strength)
            elif mask_type == "pixelate":
                masked_image = self._apply_adaptive_pixelation(image, mask, measurements, strength)
            elif mask_type == "noise":
                masked_image = self._apply_noise_mask(image, mask, strength)
            elif mask_type == "synthetic":
                masked_image = self._apply_synthetic_face(image, mask, measurements, strength)
            else:
                masked_image = self._apply_adaptive_blur(image, mask, measurements, strength)
            
            return {
                'masked_image': masked_image,
                'mask': mask,
                'measurements': measurements,
                'success': True
            }
            
        except Exception as e:
            logger.error(f"Error generating adaptive mask: {str(e)}")
            return {'error': str(e), 'success': False}
    
    def _create_measurement_based_mask(self, image: np.ndarray, landmarks: np.ndarray, 
                                     measurements: Dict[str, float]) -> np.ndarray:
        """Create precise mask based on face measurements."""
        h, w = image.shape[:2]
        mask = np.zeros((h, w), dtype=np.uint8)
        
        # Use face width and height to determine mask boundaries
        face_width = measurements.get('face_width', 1.0)
        face_height = measurements.get('face_height', 1.0)
        
        # Calculate face center
        face_center_x = int(np.mean(landmarks[:, 0]))
        face_center_y = int(np.mean(landmarks[:, 1]))
        
        # Create elliptical mask based on measurements
        # Scale factor based on face proportions
        width_scale = int(face_width * 100)  # Scale to pixel space
        height_scale = int(face_height * 100)
        
        # Ensure reasonable bounds
        width_scale = max(50, min(width_scale, w // 3))
        height_scale = max(60, min(height_scale, h // 3))
        
        # Create elliptical mask
        cv2.ellipse(mask, 
                   (face_center_x, face_center_y),
                   (width_scale, height_scale),
                   0, 0, 360, 255, -1)
        
        # Refine mask using landmarks for better precision
        mask = self._refine_mask_with_landmarks(mask, landmarks)
        
        return mask
    
    def _refine_mask_with_landmarks(self, mask: np.ndarray, landmarks: np.ndarray) -> np.ndarray:
        """Refine mask using detailed landmark information."""
        # Create convex hull around face landmarks
        hull = cv2.convexHull(landmarks.astype(np.int32))
        
        # Create refined mask
        refined_mask = np.zeros_like(mask)
        cv2.fillPoly(refined_mask, [hull], 255)
        
        # Combine with original mask using intersection
        mask = cv2.bitwise_and(mask, refined_mask)
        
        # Apply morphological operations for smoothing
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        mask = cv2.GaussianBlur(mask, (15, 15), 0)
        
        return mask
    
    def _apply_adaptive_blur(self, image: np.ndarray, mask: np.ndarray, 
                           measurements: Dict[str, float], strength: float) -> np.ndarray:
        """Apply adaptive blur based on face measurements."""
        # Determine blur kernel size based on face size
        face_area = measurements.get('face_width', 1.0) * measurements.get('face_height', 1.0)
        base_kernel_size = max(5, int(face_area * 50 * strength))
        
        # Ensure odd kernel size
        kernel_size = base_kernel_size if base_kernel_size % 2 == 1 else base_kernel_size + 1
        kernel_size = min(kernel_size, 101)  # Cap at reasonable size
        
        # Apply Gaussian blur
        blurred = cv2.GaussianBlur(image, (kernel_size, kernel_size), 0)
        
        # Blend with original image using mask
        mask_normalized = mask.astype(np.float32) / 255.0
        mask_3d = np.stack([mask_normalized] * 3, axis=-1)
        
        result = image.astype(np.float32) * (1 - mask_3d) + blurred.astype(np.float32) * mask_3d
        
        return result.astype(np.uint8)
    
    def _apply_adaptive_pixelation(self, image: np.ndarray, mask: np.ndarray,
                                 measurements: Dict[str, float], strength: float) -> np.ndarray:
        """Apply adaptive pixelation based on face measurements."""
        # Determine pixel size based on face measurements
        face_width = measurements.get('face_width', 1.0)
        pixel_size = max(2, int(face_width * 20 * strength))
        
        # Create pixelated version
        h, w = image.shape[:2]
        small_image = cv2.resize(image, (w // pixel_size, h // pixel_size), 
                               interpolation=cv2.INTER_LINEAR)
        pixelated = cv2.resize(small_image, (w, h), interpolation=cv2.INTER_NEAREST)
        
        # Blend with original using mask
        mask_normalized = mask.astype(np.float32) / 255.0
        mask_3d = np.stack([mask_normalized] * 3, axis=-1)
        
        result = image.astype(np.float32) * (1 - mask_3d) + pixelated.astype(np.float32) * mask_3d
        
        return result.astype(np.uint8)
    
    def _apply_noise_mask(self, image: np.ndarray, mask: np.ndarray, strength: float) -> np.ndarray:
        """Apply noise-based privacy mask."""
        # Generate noise
        noise = np.random.normal(0, 50 * strength, image.shape).astype(np.int16)
        
        # Apply noise only to masked areas
        mask_normalized = mask.astype(np.float32) / 255.0
        mask_3d = np.stack([mask_normalized] * 3, axis=-1)
        
        # Add noise to masked areas
        noisy_image = image.astype(np.int16) + (noise * mask_3d).astype(np.int16)
        noisy_image = np.clip(noisy_image, 0, 255)
        
        return noisy_image.astype(np.uint8)
    
    def _apply_synthetic_face(self, image: np.ndarray, mask: np.ndarray,
                            measurements: Dict[str, float], strength: float) -> np.ndarray:
        """Apply synthetic face replacement (placeholder implementation)."""
        # This would integrate with face generation models
        # For now, apply a gradient-based replacement
        
        # Find mask region
        mask_coords = np.where(mask > 0)
        if len(mask_coords[0]) == 0:
            return image
        
        min_y, max_y = np.min(mask_coords[0]), np.max(mask_coords[0])
        min_x, max_x = np.min(mask_coords[1]), np.max(mask_coords[1])
        
        # Create synthetic pattern
        height = max_y - min_y
        width = max_x - min_x
        
        # Generate a face-like pattern
        synthetic = np.zeros((height, width, 3), dtype=np.uint8)
        
        # Add skin-tone gradient
        skin_color = [180, 150, 120]  # Base skin tone
        for i in range(height):
            for j in range(width):
                # Create subtle variations
                variation = np.sin(i * 0.1) * np.cos(j * 0.1) * 20
                for c in range(3):
                    synthetic[i, j, c] = np.clip(skin_color[c] + variation, 0, 255)
        
        # Apply to image
        result = image.copy()
        mask_region = mask[min_y:max_y, min_x:max_x]
        
        for c in range(3):
            result[min_y:max_y, min_x:max_x, c] = np.where(
                mask_region > 0,
                synthetic[:, :, c] * strength + result[min_y:max_y, min_x:max_x, c] * (1 - strength),
                result[min_y:max_y, min_x:max_x, c]
            )
        
        return result
    
    def create_privacy_levels(self, image: np.ndarray) -> Dict[str, any]:
        """Create multiple privacy levels for user selection."""
        try:
            privacy_levels = {}
            
            # Level 1: Light blur
            level1 = self.generate_adaptive_mask(image, "blur", 0.3)
            if level1['success']:
                privacy_levels['light'] = level1['masked_image']
            
            # Level 2: Medium blur
            level2 = self.generate_adaptive_mask(image, "blur", 0.7)
            if level2['success']:
                privacy_levels['medium'] = level2['masked_image']
            
            # Level 3: Strong blur
            level3 = self.generate_adaptive_mask(image, "blur", 1.0)
            if level3['success']:
                privacy_levels['strong'] = level3['masked_image']
            
            # Level 4: Pixelation
            level4 = self.generate_adaptive_mask(image, "pixelate", 0.8)
            if level4['success']:
                privacy_levels['pixelated'] = level4['masked_image']
            
            # Level 5: Complete anonymization
            level5 = self.generate_adaptive_mask(image, "synthetic", 1.0)
            if level5['success']:
                privacy_levels['anonymous'] = level5['masked_image']
            
            return {
                'privacy_levels': privacy_levels,
                'success': True
            }
            
        except Exception as e:
            logger.error(f"Error creating privacy levels: {str(e)}")
            return {'error': str(e), 'success': False}
    
    def batch_process_privacy_masks(self, images: List[np.ndarray], mask_type: str = "blur",
                                   strength: float = 1.0) -> List[Dict[str, any]]:
        """Process multiple images with privacy masks."""
        results = []
        
        for i, image in enumerate(images):
            logger.info(f"Processing image {i+1}/{len(images)}")
            result = self.generate_adaptive_mask(image, mask_type, strength)
            results.append(result)
        
        return results
    
    def get_supported_mask_types(self) -> List[str]:
        """Get list of supported mask types."""
        return ["blur", "pixelate", "noise", "synthetic"]