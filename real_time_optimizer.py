"""
PLAYALTER Real-Time Performance Optimizer
GPU acceleration, frame caching, and ultra-low latency processing
"""

import numpy as np
import cv2
import time
from typing import Dict, List, Optional, Tuple, Any
from collections import deque
import threading
import queue
import asyncio
from concurrent.futures import ThreadPoolExecutor

class PerformanceOptimizer:
    """Optimizes real-time face processing for minimal latency"""
    
    def __init__(self, max_fps: int = 30, gpu_enabled: bool = True):
        self.max_fps = max_fps
        self.target_frame_time = 1.0 / max_fps
        self.gpu_enabled = gpu_enabled
        
        # Performance tracking
        self.frame_times = deque(maxlen=30)
        self.processing_times = deque(maxlen=30)
        self.face_cache = {}
        self.face_tracker = FaceTracker()
        
        # Threading for async processing
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.frame_queue = queue.Queue(maxsize=3)
        self.result_queue = queue.Queue(maxsize=3)
        
        # Adaptive quality settings
        self.current_quality = "balanced"
        self.quality_settings = {
            "performance": {
                "detection_scale": 1.5,
                "min_face_size": (60, 60),
                "max_faces": 3,
                "blur_kernel": 11,
                "skip_frames": 2
            },
            "balanced": {
                "detection_scale": 1.2,
                "min_face_size": (40, 40),
                "max_faces": 5,
                "blur_kernel": 15,
                "skip_frames": 1
            },
            "quality": {
                "detection_scale": 1.1,
                "min_face_size": (30, 30),
                "max_faces": 8,
                "blur_kernel": 19,
                "skip_frames": 0
            }
        }
        
        # GPU context if available
        self.gpu_context = None
        if self.gpu_enabled:
            self._init_gpu_context()
    
    def _init_gpu_context(self):
        """Initialize GPU context for OpenCV"""
        try:
            # Try to use GPU acceleration
            if cv2.cuda.getCudaEnabledDeviceCount() > 0:
                self.gpu_context = cv2.cuda_DeviceInfo(0)
                print("GPU acceleration enabled")
            else:
                print("GPU not available, using CPU")
                self.gpu_enabled = False
        except:
            print("GPU acceleration not supported, using CPU")
            self.gpu_enabled = False
    
    def adaptive_quality_control(self, processing_time: float):
        """Automatically adjust quality based on performance"""
        target_time = self.target_frame_time * 0.8  # Leave 20% buffer
        
        if processing_time > target_time * 1.5:
            # Too slow, reduce quality
            if self.current_quality == "quality":
                self.current_quality = "balanced"
            elif self.current_quality == "balanced":
                self.current_quality = "performance"
        elif processing_time < target_time * 0.5:
            # Too fast, can increase quality
            if self.current_quality == "performance":
                self.current_quality = "balanced"
            elif self.current_quality == "balanced":
                self.current_quality = "quality"
    
    def get_current_settings(self) -> Dict[str, Any]:
        """Get current quality settings"""
        return self.quality_settings[self.current_quality]

class FaceTracker:
    """Track faces across frames for temporal consistency"""
    
    def __init__(self, max_disappeared: int = 10):
        self.next_id = 0
        self.objects = {}
        self.disappeared = {}
        self.max_disappeared = max_disappeared
    
    def register(self, centroid: Tuple[int, int]) -> int:
        """Register a new face"""
        self.objects[self.next_id] = centroid
        self.disappeared[self.next_id] = 0
        self.next_id += 1
        return self.next_id - 1
    
    def deregister(self, object_id: int):
        """Remove a face from tracking"""
        del self.objects[object_id]
        del self.disappeared[object_id]
    
    def update(self, face_rects: List[Tuple[int, int, int, int]]) -> Dict[int, Tuple[int, int, int, int]]:
        """Update face tracking with new detections"""
        if len(face_rects) == 0:
            # Mark all existing objects as disappeared
            for object_id in list(self.disappeared.keys()):
                self.disappeared[object_id] += 1
                if self.disappeared[object_id] > self.max_disappeared:
                    self.deregister(object_id)
            return {}
        
        input_centroids = []
        for (x, y, w, h) in face_rects:
            cx = int(x + w / 2.0)
            cy = int(y + h / 2.0)
            input_centroids.append((cx, cy))
        
        if len(self.objects) == 0:
            # No existing objects, register all
            tracked_faces = {}
            for i, rect in enumerate(face_rects):
                object_id = self.register(input_centroids[i])
                tracked_faces[object_id] = rect
            return tracked_faces
        
        # Compute distance matrix and assign
        object_centroids = list(self.objects.values())
        D = np.linalg.norm(np.array(object_centroids)[:, np.newaxis] - input_centroids, axis=2)
        
        # Assign detections to existing objects
        rows = D.min(axis=1).argsort()
        cols = D.argmin(axis=1)[rows]
        
        used_row_idxs = set()
        used_col_idxs = set()
        tracked_faces = {}
        
        for (row, col) in zip(rows, cols):
            if row in used_row_idxs or col in used_col_idxs:
                continue
            
            if D[row, col] > 50:  # Maximum distance threshold
                continue
            
            object_id = list(self.objects.keys())[row]
            self.objects[object_id] = input_centroids[col]
            self.disappeared[object_id] = 0
            tracked_faces[object_id] = face_rects[col]
            
            used_row_idxs.add(row)
            used_col_idxs.add(col)
        
        # Handle unmatched detections and objects
        unused_rows = set(range(0, D.shape[0])).difference(used_row_idxs)
        unused_cols = set(range(0, D.shape[1])).difference(used_col_idxs)
        
        if D.shape[0] >= D.shape[1]:
            # More objects than detections
            for row in unused_rows:
                object_id = list(self.objects.keys())[row]
                self.disappeared[object_id] += 1
                
                if self.disappeared[object_id] > self.max_disappeared:
                    self.deregister(object_id)
        else:
            # More detections than objects
            for col in unused_cols:
                object_id = self.register(input_centroids[col])
                tracked_faces[object_id] = face_rects[col]
        
        return tracked_faces

class OptimizedFaceDetector:
    """Ultra-fast face detection optimized for real-time streaming"""
    
    def __init__(self, performance_optimizer: PerformanceOptimizer):
        self.optimizer = performance_optimizer
        self.cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_alt.xml')
        self.frame_skip_counter = 0
        self.last_detections = []
        
        # GPU-accelerated cascade if available
        if self.optimizer.gpu_enabled:
            try:
                self.gpu_cascade = cv2.cuda.CascadeClassifier_create(
                    cv2.data.haarcascades + 'haarcascade_frontalface_alt.xml'
                )
            except:
                self.gpu_cascade = None
    
    def detect_faces_optimized(self, frame: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """Detect faces with performance optimizations"""
        settings = self.optimizer.get_current_settings()
        
        # Frame skipping for performance
        if self.frame_skip_counter < settings["skip_frames"]:
            self.frame_skip_counter += 1
            return self.last_detections
        
        self.frame_skip_counter = 0
        
        # Resize frame for faster detection
        height, width = frame.shape[:2]
        scale = settings["detection_scale"]
        small_frame = cv2.resize(frame, (int(width/scale), int(height/scale)))
        gray = cv2.cvtColor(small_frame, cv2.COLOR_BGR2GRAY)
        
        # GPU detection if available
        if self.optimizer.gpu_enabled and self.gpu_cascade:
            try:
                gpu_frame = cv2.cuda_GpuMat()
                gpu_frame.upload(gray)
                faces_gpu = self.gpu_cascade.detectMultiScale(gpu_frame)
                faces = faces_gpu.download()
            except:
                # Fallback to CPU
                faces = self.cascade.detectMultiScale(
                    gray,
                    scaleFactor=1.3,
                    minNeighbors=3,
                    minSize=settings["min_face_size"]
                )
        else:
            # CPU detection
            faces = self.cascade.detectMultiScale(
                gray,
                scaleFactor=1.3,
                minNeighbors=3,
                minSize=settings["min_face_size"]
            )
        
        # Scale back to original size
        faces_scaled = []
        for (x, y, w, h) in faces[:settings["max_faces"]]:
            faces_scaled.append((
                int(x * scale),
                int(y * scale),
                int(w * scale),
                int(h * scale)
            ))
        
        self.last_detections = faces_scaled
        return faces_scaled

class OptimizedMaskApplicator:
    """Apply privacy masks with GPU acceleration and optimizations"""
    
    def __init__(self, performance_optimizer: PerformanceOptimizer):
        self.optimizer = performance_optimizer
        self.mask_cache = {}
        
    def apply_mask_ultra_fast(self, frame: np.ndarray, faces: Dict[int, Tuple[int, int, int, int]], 
                             mask_type: str, intensity: float) -> np.ndarray:
        """Apply privacy mask with ultra-fast processing"""
        if not faces:
            return frame
        
        settings = self.optimizer.get_current_settings()
        result_frame = frame.copy()
        
        for face_id, (x, y, w, h) in faces.items():
            # Use cached mask if available
            cache_key = f"{face_id}_{w}_{h}_{mask_type}_{intensity}"
            
            if cache_key in self.mask_cache:
                mask_region = self.mask_cache[cache_key]
            else:
                face_region = result_frame[y:y+h, x:x+w]
                mask_region = self._create_optimized_mask(face_region, mask_type, intensity, settings)
                
                # Cache for future use (limit cache size)
                if len(self.mask_cache) < 50:
                    self.mask_cache[cache_key] = mask_region
            
            # Apply cached mask
            if mask_region.shape == result_frame[y:y+h, x:x+w].shape:
                result_frame[y:y+h, x:x+w] = mask_region
        
        return result_frame
    
    def _create_optimized_mask(self, face_region: np.ndarray, mask_type: str, 
                              intensity: float, settings: Dict) -> np.ndarray:
        """Create optimized mask for face region"""
        if mask_type == "blur":
            kernel_size = settings["blur_kernel"]
            if kernel_size % 2 == 0:
                kernel_size += 1
            return cv2.GaussianBlur(face_region, (kernel_size, kernel_size), 0)
        
        elif mask_type == "pixelate":
            h, w = face_region.shape[:2]
            pixel_size = max(4, min(w, h) // 20)
            temp = cv2.resize(face_region, (w//pixel_size, h//pixel_size), interpolation=cv2.INTER_LINEAR)
            return cv2.resize(temp, (w, h), interpolation=cv2.INTER_NEAREST)
        
        elif mask_type == "color_block":
            color = (100, 100, 100)
            overlay = np.full_like(face_region, color, dtype=np.uint8)
            return cv2.addWeighted(face_region, 1-intensity, overlay, intensity, 0)
        
        return face_region

class RealTimeProcessor:
    """Main real-time processing pipeline with all optimizations"""
    
    def __init__(self, target_fps: int = 30):
        self.target_fps = target_fps
        self.optimizer = PerformanceOptimizer(max_fps=target_fps)
        self.face_detector = OptimizedFaceDetector(self.optimizer)
        self.mask_applicator = OptimizedMaskApplicator(self.optimizer)
        
        # Performance statistics
        self.stats = {
            "current_fps": 0,
            "avg_latency": 0,
            "dropped_frames": 0,
            "total_frames": 0,
            "faces_detected": 0
        }
        
        self.last_stat_time = time.time()
        self.frame_count = 0
    
    async def process_frame_async(self, frame: np.ndarray, mask_settings: Dict) -> Tuple[np.ndarray, Dict]:
        """Process single frame with full optimization pipeline"""
        start_time = time.time()
        
        # Detect faces with tracking
        face_rects = self.face_detector.detect_faces_optimized(frame)
        tracked_faces = self.optimizer.face_tracker.update(face_rects)
        
        # Apply masks
        if mask_settings.get('type', 'off') != 'off':
            result_frame = self.mask_applicator.apply_mask_ultra_fast(
                frame, tracked_faces, 
                mask_settings['type'], 
                mask_settings.get('intensity', 0.7)
            )
        else:
            result_frame = frame
        
        # Update performance stats
        processing_time = time.time() - start_time
        self.optimizer.adaptive_quality_control(processing_time)
        self._update_stats(processing_time, len(tracked_faces))
        
        # Performance info
        perf_info = {
            "processing_time_ms": processing_time * 1000,
            "faces_detected": len(tracked_faces),
            "current_quality": self.optimizer.current_quality,
            "stats": self.stats
        }
        
        return result_frame, perf_info
    
    def _update_stats(self, processing_time: float, face_count: int):
        """Update performance statistics"""
        self.frame_count += 1
        self.stats["total_frames"] += 1
        self.stats["faces_detected"] = face_count
        
        # Update FPS every second
        current_time = time.time()
        if current_time - self.last_stat_time >= 1.0:
            self.stats["current_fps"] = self.frame_count / (current_time - self.last_stat_time)
            self.frame_count = 0
            self.last_stat_time = current_time
        
        # Update latency
        self.optimizer.processing_times.append(processing_time * 1000)
        if self.optimizer.processing_times:
            self.stats["avg_latency"] = sum(self.optimizer.processing_times) / len(self.optimizer.processing_times)
        
        # Check for dropped frames
        if processing_time > self.optimizer.target_frame_time:
            self.stats["dropped_frames"] += 1
    
    def get_performance_report(self) -> Dict:
        """Get detailed performance report"""
        return {
            "fps": self.stats["current_fps"],
            "avg_latency_ms": self.stats["avg_latency"],
            "dropped_frames": self.stats["dropped_frames"],
            "total_frames": self.stats["total_frames"],
            "drop_rate": self.stats["dropped_frames"] / max(1, self.stats["total_frames"]),
            "current_quality": self.optimizer.current_quality,
            "gpu_enabled": self.optimizer.gpu_enabled,
            "faces_detected": self.stats["faces_detected"]
        }

# Example usage and testing
async def benchmark_performance():
    """Benchmark the real-time processor"""
    processor = RealTimeProcessor(target_fps=30)
    
    # Create test frames
    test_frames = []
    for i in range(100):
        # Random frame with some faces
        frame = np.random.randint(0, 255, (720, 1280, 3), dtype=np.uint8)
        # Add some rectangular "faces" for testing
        for j in range(3):
            x, y = np.random.randint(50, 1000, 2)
            cv2.rectangle(frame, (x, y), (x+100, y+100), (255, 255, 255), -1)
        test_frames.append(frame)
    
    # Test processing
    mask_settings = {"type": "blur", "intensity": 0.7}
    
    print("Starting performance benchmark...")
    start_time = time.time()
    
    for i, frame in enumerate(test_frames):
        processed_frame, perf_info = await processor.process_frame_async(frame, mask_settings)
        
        if i % 30 == 0:  # Print every 30 frames
            print(f"Frame {i}: {perf_info['processing_time_ms']:.1f}ms, "
                  f"Faces: {perf_info['faces_detected']}, "
                  f"Quality: {perf_info['current_quality']}")
    
    total_time = time.time() - start_time
    report = processor.get_performance_report()
    
    print("\n=== PERFORMANCE REPORT ===")
    print(f"Total processing time: {total_time:.2f}s")
    print(f"Average FPS: {len(test_frames)/total_time:.1f}")
    print(f"Average latency: {report['avg_latency_ms']:.1f}ms")
    print(f"Drop rate: {report['drop_rate']*100:.1f}%")
    print(f"GPU enabled: {report['gpu_enabled']}")
    print(f"Final quality setting: {report['current_quality']}")

if __name__ == "__main__":
    asyncio.run(benchmark_performance())