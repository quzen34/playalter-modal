import os
import uuid
import aiofiles
from typing import Optional, Dict, List, Tuple
from fastapi import UploadFile, HTTPException
import cv2
import numpy as np
from PIL import Image
import io
import logging
from pathlib import Path
import asyncio
import tempfile
import mimetypes

logger = logging.getLogger(__name__)

class FileHandler:
    """Handle file uploads, validation, and processing."""
    
    def __init__(self, upload_dir: str = "/tmp/uploads", max_file_size: int = 10 * 1024 * 1024):
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.max_file_size = max_file_size  # 10MB default
        
        # Supported image formats
        self.supported_formats = {
            'image/jpeg', 'image/jpg', 'image/png', 'image/bmp', 
            'image/tiff', 'image/webp'
        }
        
        # Supported video formats
        self.supported_video_formats = {
            'video/mp4', 'video/avi', 'video/mov', 'video/mkv', 'video/webm'
        }
    
    async def validate_file(self, file: UploadFile) -> Dict[str, any]:
        """Validate uploaded file."""
        try:
            # Check file size
            content = await file.read()
            file_size = len(content)
            
            if file_size > self.max_file_size:
                raise HTTPException(
                    status_code=413, 
                    detail=f"File too large. Maximum size: {self.max_file_size // (1024*1024)}MB"
                )
            
            # Reset file pointer
            await file.seek(0)
            
            # Check MIME type
            mime_type, _ = mimetypes.guess_type(file.filename)
            if not mime_type:
                # Fallback: check content type from upload
                mime_type = file.content_type
            
            # Validate format
            is_image = mime_type in self.supported_formats
            is_video = mime_type in self.supported_video_formats
            
            if not (is_image or is_video):
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported file format. Supported: {self.supported_formats | self.supported_video_formats}"
                )
            
            # Additional image validation
            if is_image:
                image_validation = await self._validate_image_content(content)
                if not image_validation['valid']:
                    raise HTTPException(status_code=400, detail=image_validation['error'])
            
            return {
                'valid': True,
                'file_size': file_size,
                'mime_type': mime_type,
                'is_image': is_image,
                'is_video': is_video,
                'filename': file.filename
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error validating file: {str(e)}")
            raise HTTPException(status_code=500, detail="File validation failed")
    
    async def _validate_image_content(self, content: bytes) -> Dict[str, any]:
        """Validate image content and dimensions."""
        try:
            # Try to open image with PIL
            image = Image.open(io.BytesIO(content))
            width, height = image.size
            
            # Check minimum dimensions
            if width < 64 or height < 64:
                return {
                    'valid': False,
                    'error': 'Image too small. Minimum size: 64x64 pixels'
                }
            
            # Check maximum dimensions
            if width > 4096 or height > 4096:
                return {
                    'valid': False,
                    'error': 'Image too large. Maximum size: 4096x4096 pixels'
                }
            
            # Check if image can be processed by OpenCV
            image_array = np.array(image)
            if len(image_array.shape) not in [2, 3]:
                return {
                    'valid': False,
                    'error': 'Invalid image format for processing'
                }
            
            return {
                'valid': True,
                'width': width,
                'height': height,
                'channels': len(image_array.shape),
                'mode': image.mode
            }
            
        except Exception as e:
            return {
                'valid': False,
                'error': f'Invalid image content: {str(e)}'
            }
    
    async def save_uploaded_file(self, file: UploadFile, 
                               validation_result: Optional[Dict] = None) -> Dict[str, any]:
        """Save uploaded file to disk."""
        try:
            if validation_result is None:
                validation_result = await self.validate_file(file)
            
            # Generate unique filename
            file_extension = Path(file.filename).suffix.lower()
            unique_filename = f"{uuid.uuid4()}{file_extension}"
            file_path = self.upload_dir / unique_filename
            
            # Save file
            async with aiofiles.open(file_path, 'wb') as f:
                content = await file.read()
                await f.write(content)
            
            return {
                'success': True,
                'file_path': str(file_path),
                'filename': unique_filename,
                'original_filename': file.filename,
                'file_size': validation_result['file_size'],
                'mime_type': validation_result['mime_type']
            }
            
        except Exception as e:
            logger.error(f"Error saving file: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to save file")
    
    def load_image_from_path(self, file_path: str) -> np.ndarray:
        """Load image from file path as numpy array."""
        try:
            if not os.path.exists(file_path):
                raise HTTPException(status_code=404, detail="File not found")
            
            # Load image with OpenCV
            image = cv2.imread(file_path)
            if image is None:
                raise HTTPException(status_code=400, detail="Failed to load image")
            
            return image
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error loading image from path: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to load image")
    
    async def process_uploaded_image(self, file: UploadFile) -> Tuple[np.ndarray, Dict[str, any]]:
        """Process uploaded image and return numpy array."""
        try:
            # Validate file
            validation_result = await self.validate_file(file)
            
            if not validation_result['is_image']:
                raise HTTPException(status_code=400, detail="File is not an image")
            
            # Read file content
            content = await file.read()
            
            # Convert to numpy array
            image_array = np.frombuffer(content, np.uint8)
            image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
            
            if image is None:
                raise HTTPException(status_code=400, detail="Failed to decode image")
            
            return image, validation_result
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error processing uploaded image: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to process image")
    
    async def process_multiple_images(self, files: List[UploadFile]) -> List[Tuple[np.ndarray, Dict[str, any]]]:
        """Process multiple uploaded images."""
        if len(files) > 10:
            raise HTTPException(status_code=400, detail="Maximum 10 files allowed")
        
        results = []
        for i, file in enumerate(files):
            try:
                image, metadata = await self.process_uploaded_image(file)
                results.append((image, metadata))
            except Exception as e:
                logger.error(f"Error processing file {i}: {str(e)}")
                raise HTTPException(status_code=400, detail=f"Error processing file {i}: {str(e)}")
        
        return results
    
    def save_processed_image(self, image: np.ndarray, 
                           original_filename: str = "processed",
                           quality: int = 95) -> str:
        """Save processed image to disk."""
        try:
            # Generate output filename
            base_name = Path(original_filename).stem
            output_filename = f"{base_name}_processed_{uuid.uuid4().hex[:8]}.jpg"
            output_path = self.upload_dir / output_filename
            
            # Save image
            cv2.imwrite(str(output_path), image, [cv2.IMWRITE_JPEG_QUALITY, quality])
            
            return str(output_path)
            
        except Exception as e:
            logger.error(f"Error saving processed image: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to save processed image")
    
    async def cleanup_temp_files(self, file_paths: List[str]):
        """Clean up temporary files."""
        for file_path in file_paths:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.debug(f"Cleaned up file: {file_path}")
            except Exception as e:
                logger.warning(f"Failed to cleanup file {file_path}: {str(e)}")
    
    def get_file_info(self, file_path: str) -> Dict[str, any]:
        """Get information about a file."""
        try:
            if not os.path.exists(file_path):
                return {'exists': False}
            
            stat = os.stat(file_path)
            mime_type, _ = mimetypes.guess_type(file_path)
            
            info = {
                'exists': True,
                'file_path': file_path,
                'file_size': stat.st_size,
                'mime_type': mime_type,
                'created_time': stat.st_ctime,
                'modified_time': stat.st_mtime
            }
            
            # Additional info for images
            if mime_type and mime_type.startswith('image/'):
                try:
                    with Image.open(file_path) as img:
                        info.update({
                            'width': img.width,
                            'height': img.height,
                            'mode': img.mode,
                            'format': img.format
                        })
                except Exception as e:
                    logger.warning(f"Could not get image info: {str(e)}")
            
            return info
            
        except Exception as e:
            logger.error(f"Error getting file info: {str(e)}")
            return {'exists': False, 'error': str(e)}
    
    async def create_temp_file(self, content: bytes, suffix: str = '.jpg') -> str:
        """Create temporary file with content."""
        try:
            # Create temporary file
            temp_fd, temp_path = tempfile.mkstemp(suffix=suffix, dir=self.upload_dir)
            
            # Write content
            with os.fdopen(temp_fd, 'wb') as f:
                f.write(content)
            
            return temp_path
            
        except Exception as e:
            logger.error(f"Error creating temp file: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to create temporary file")
    
    def get_supported_formats(self) -> Dict[str, List[str]]:
        """Get list of supported file formats."""
        return {
            'images': list(self.supported_formats),
            'videos': list(self.supported_video_formats),
            'max_file_size_mb': self.max_file_size // (1024 * 1024),
            'max_image_dimensions': '4096x4096',
            'min_image_dimensions': '64x64'
        }

class VideoHandler(FileHandler):
    """Extended handler for video files."""
    
    def __init__(self, upload_dir: str = "/tmp/uploads", max_file_size: int = 100 * 1024 * 1024):
        super().__init__(upload_dir, max_file_size)  # 100MB for videos
    
    def extract_frames(self, video_path: str, max_frames: int = 30) -> List[np.ndarray]:
        """Extract frames from video."""
        try:
            if not os.path.exists(video_path):
                raise HTTPException(status_code=404, detail="Video file not found")
            
            cap = cv2.VideoCapture(video_path)
            frames = []
            
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            frame_interval = max(1, total_frames // max_frames)
            
            frame_count = 0
            while cap.isOpened() and len(frames) < max_frames:
                ret, frame = cap.read()
                if not ret:
                    break
                
                if frame_count % frame_interval == 0:
                    frames.append(frame.copy())
                
                frame_count += 1
            
            cap.release()
            
            if len(frames) == 0:
                raise HTTPException(status_code=400, detail="No frames could be extracted from video")
            
            return frames
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error extracting frames: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to extract video frames")
    
    def get_video_info(self, video_path: str) -> Dict[str, any]:
        """Get video information."""
        try:
            cap = cv2.VideoCapture(video_path)
            
            info = {
                'frame_count': int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
                'fps': cap.get(cv2.CAP_PROP_FPS),
                'width': int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                'height': int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                'duration': int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) / cap.get(cv2.CAP_PROP_FPS)
            }
            
            cap.release()
            return info
            
        except Exception as e:
            logger.error(f"Error getting video info: {str(e)}")
            return {'error': str(e)}