import torch
import numpy as np
import cv2
from typing import Dict, Tuple, Optional, List
import logging
from pathlib import Path
import pickle
from flame import FLAME
import face_alignment

logger = logging.getLogger(__name__)

class FLAMEModelService:
    """Service for FLAME model face analysis and measurement extraction."""
    
    def __init__(self, model_path: Optional[str] = None):
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.flame_model = None
        self.face_detector = None
        self.model_path = model_path or self._get_default_model_path()
        
        # FLAME parameters
        self.n_shape = 300  # Shape parameters
        self.n_exp = 100    # Expression parameters
        self.n_pose = 15    # Pose parameters (3 global + 12 jaw/neck)
        
        self._load_models()
    
    def _get_default_model_path(self) -> str:
        """Get default FLAME model path."""
        return "/tmp/flame_model"
    
    def _load_models(self):
        """Load FLAME model and face detector."""
        try:
            # Initialize face detector
            self.face_detector = face_alignment.FaceAlignment(
                face_alignment.LandmarksType._2D, 
                flip_input=False,
                device=str(self.device)
            )
            
            # Initialize FLAME model
            self.flame_model = FLAME(
                config={
                    'flame_model_path': self.model_path,
                    'n_shape': self.n_shape,
                    'n_exp': self.n_exp,
                    'flame_lmk_embedding_path': f"{self.model_path}/flame_static_embedding.pkl"
                }
            ).to(self.device)
            
            logger.info("FLAME model and face detector loaded successfully")
            
        except Exception as e:
            logger.error(f"Error loading FLAME models: {str(e)}")
            raise
    
    def detect_face_landmarks(self, image: np.ndarray) -> Optional[np.ndarray]:
        """Detect facial landmarks in image."""
        try:
            landmarks = self.face_detector.get_landmarks(image)
            if landmarks is not None and len(landmarks) > 0:
                return landmarks[0]  # Return first face landmarks
            return None
        except Exception as e:
            logger.error(f"Error detecting face landmarks: {str(e)}")
            return None
    
    def fit_flame_to_landmarks(self, landmarks: np.ndarray, image_shape: Tuple[int, int]) -> Dict[str, torch.Tensor]:
        """Fit FLAME model to detected landmarks."""
        try:
            # Convert landmarks to tensor
            landmarks_tensor = torch.tensor(landmarks, dtype=torch.float32, device=self.device)
            
            # Initialize parameters
            shape_params = torch.zeros(1, self.n_shape, device=self.device, requires_grad=True)
            exp_params = torch.zeros(1, self.n_exp, device=self.device, requires_grad=True)
            pose_params = torch.zeros(1, self.n_pose, device=self.device, requires_grad=True)
            
            # Camera parameters (simplified orthographic projection)
            scale = torch.tensor([1.0], device=self.device, requires_grad=True)
            translation = torch.zeros(2, device=self.device, requires_grad=True)
            
            # Optimization parameters
            optimizer = torch.optim.Adam([shape_params, exp_params, pose_params, scale, translation], lr=0.01)
            
            # Optimization loop
            for iteration in range(100):
                optimizer.zero_grad()
                
                # Forward pass through FLAME
                vertices, landmarks_3d = self.flame_model(
                    shape_params=shape_params,
                    expression_params=exp_params,
                    pose_params=pose_params
                )
                
                # Project 3D landmarks to 2D
                landmarks_2d_pred = self._project_landmarks(landmarks_3d, scale, translation)
                
                # Compute loss
                loss = torch.nn.functional.mse_loss(landmarks_2d_pred, landmarks_tensor.unsqueeze(0))
                
                loss.backward()
                optimizer.step()
                
                if iteration % 20 == 0:
                    logger.debug(f"Iteration {iteration}, Loss: {loss.item():.6f}")
            
            return {
                'shape_params': shape_params.detach(),
                'exp_params': exp_params.detach(),
                'pose_params': pose_params.detach(),
                'scale': scale.detach(),
                'translation': translation.detach(),
                'vertices': vertices.detach(),
                'landmarks_3d': landmarks_3d.detach()
            }
            
        except Exception as e:
            logger.error(f"Error fitting FLAME model: {str(e)}")
            raise
    
    def _project_landmarks(self, landmarks_3d: torch.Tensor, scale: torch.Tensor, translation: torch.Tensor) -> torch.Tensor:
        """Project 3D landmarks to 2D using orthographic projection."""
        landmarks_2d = landmarks_3d[:, :, :2] * scale.unsqueeze(-1).unsqueeze(-1)
        landmarks_2d += translation.unsqueeze(0).unsqueeze(0)
        return landmarks_2d
    
    def extract_face_measurements(self, flame_params: Dict[str, torch.Tensor]) -> Dict[str, float]:
        """Extract detailed face measurements from FLAME parameters."""
        try:
            vertices = flame_params['vertices'].cpu().numpy()[0]  # Shape: [5023, 3]
            
            measurements = {}
            
            # Key vertex indices for measurements (approximated)
            # Face width (cheek to cheek)
            left_cheek_idx = 234
            right_cheek_idx = 1803
            face_width = np.linalg.norm(vertices[left_cheek_idx] - vertices[right_cheek_idx])
            measurements['face_width'] = float(face_width)
            
            # Face height (forehead to chin)
            forehead_idx = 9
            chin_idx = 3694
            face_height = np.linalg.norm(vertices[forehead_idx] - vertices[chin_idx])
            measurements['face_height'] = float(face_height)
            
            # Eye distance
            left_eye_inner_idx = 2658
            right_eye_inner_idx = 225
            eye_distance = np.linalg.norm(vertices[left_eye_inner_idx] - vertices[right_eye_inner_idx])
            measurements['eye_distance'] = float(eye_distance)
            
            # Nose width
            nose_left_idx = 2794
            nose_right_idx = 305
            nose_width = np.linalg.norm(vertices[nose_left_idx] - vertices[nose_right_idx])
            measurements['nose_width'] = float(nose_width)
            
            # Nose height
            nose_tip_idx = 19
            nose_bridge_idx = 3506
            nose_height = np.linalg.norm(vertices[nose_tip_idx] - vertices[nose_bridge_idx])
            measurements['nose_height'] = float(nose_height)
            
            # Mouth width
            mouth_left_idx = 308
            mouth_right_idx = 78
            mouth_width = np.linalg.norm(vertices[mouth_left_idx] - vertices[mouth_right_idx])
            measurements['mouth_width'] = float(mouth_width)
            
            # Jaw width
            jaw_left_idx = 172
            jaw_right_idx = 1923
            jaw_width = np.linalg.norm(vertices[jaw_left_idx] - vertices[jaw_right_idx])
            measurements['jaw_width'] = float(jaw_width)
            
            # Add shape parameter-based measurements
            shape_params = flame_params['shape_params'].cpu().numpy()[0]
            for i, param in enumerate(shape_params[:10]):  # First 10 shape parameters
                measurements[f'shape_param_{i}'] = float(param)
            
            return measurements
            
        except Exception as e:
            logger.error(f"Error extracting face measurements: {str(e)}")
            return {}
    
    def analyze_face(self, image: np.ndarray) -> Dict[str, any]:
        """Complete face analysis pipeline."""
        try:
            # Detect landmarks
            landmarks = self.detect_face_landmarks(image)
            if landmarks is None:
                return {'error': 'No face detected in image'}
            
            # Fit FLAME model
            flame_params = self.fit_flame_to_landmarks(landmarks, image.shape[:2])
            
            # Extract measurements
            measurements = self.extract_face_measurements(flame_params)
            
            # Return comprehensive analysis
            return {
                'landmarks': landmarks.tolist(),
                'flame_parameters': {
                    'shape_params': flame_params['shape_params'].cpu().numpy().tolist(),
                    'exp_params': flame_params['exp_params'].cpu().numpy().tolist(),
                    'pose_params': flame_params['pose_params'].cpu().numpy().tolist()
                },
                'measurements': measurements,
                'success': True
            }
            
        except Exception as e:
            logger.error(f"Error in face analysis: {str(e)}")
            return {'error': str(e), 'success': False}
    
    def create_3d_mesh(self, flame_params: Dict[str, torch.Tensor]) -> Dict[str, any]:
        """Create 3D mesh from FLAME parameters."""
        try:
            vertices = flame_params['vertices'].cpu().numpy()[0]
            
            # FLAME face topology (simplified)
            # In practice, you would use the actual FLAME face indices
            faces = self._get_flame_faces()
            
            return {
                'vertices': vertices.tolist(),
                'faces': faces.tolist() if faces is not None else [],
                'success': True
            }
            
        except Exception as e:
            logger.error(f"Error creating 3D mesh: {str(e)}")
            return {'error': str(e), 'success': False}
    
    def _get_flame_faces(self) -> Optional[np.ndarray]:
        """Get FLAME face topology."""
        try:
            # This should be loaded from the FLAME model files
            # For now, return None - would need actual FLAME topology file
            return None
        except:
            return None