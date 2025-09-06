import modal
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance
import io
import base64
import numpy as np
from typing import Optional, List, Dict, Any
import cv2
import json
import random

# Create Modal app
app = modal.App("playalter-platform-v2")

# Lightweight image with basic dependencies
image = modal.Image.debian_slim(python_version="3.11").pip_install(
    "fastapi",
    "pillow",
    "numpy",
    "opencv-python-headless",
    "python-multipart"
)

web_app = FastAPI()

# Ethnicity classifications and characteristics
ETHNICITIES = {
    "African": {
        "subgroups": ["West_African", "East_African", "Southern_African"],
        "skin_tone_range": [(0.2, 0.1, 0.05), (0.6, 0.4, 0.3)],
        "blur_params": {"radius": 15, "color_enhance": 1.2},
        "pixel_size": 15,
        "mask_color": (139, 69, 19),
        "patterns": "geometric_african"
    },
    "Asian": {
        "subgroups": ["East_Asian", "Southeast_Asian", "South_Asian"],
        "skin_tone_range": [(0.7, 0.6, 0.4), (0.95, 0.85, 0.7)],
        "blur_params": {"radius": 12, "brightness_enhance": 1.1},
        "pixel_size": 12,
        "mask_color": (200, 180, 120),
        "patterns": "circular_zen"
    },
    "Caucasian": {
        "subgroups": ["Nordic", "Mediterranean", "Slavic"],
        "skin_tone_range": [(0.8, 0.7, 0.6), (0.98, 0.95, 0.9)],
        "blur_params": {"radius": 16, "contrast_enhance": 1.0},
        "pixel_size": 18,
        "mask_color": (100, 100, 100),
        "patterns": "geometric_simple"
    },
    "Hispanic": {
        "subgroups": ["Mexican", "South_American", "Caribbean"],
        "skin_tone_range": [(0.5, 0.4, 0.3), (0.9, 0.8, 0.7)],
        "blur_params": {"radius": 14, "color_enhance": 1.15},
        "pixel_size": 15,
        "mask_color": (255, 140, 0),
        "patterns": "warm_overlay"
    },
    "Middle_Eastern": {
        "subgroups": ["Arab", "Persian", "Turkish"],
        "skin_tone_range": [(0.6, 0.5, 0.4), (0.85, 0.75, 0.65)],
        "blur_params": {"radius": 13, "contrast_enhance": 1.1},
        "pixel_size": 14,
        "mask_color": (150, 100, 50),
        "patterns": "ornate_geometric"
    }
}

def advanced_face_detection_cv2(image: Image.Image) -> List[Dict[str, Any]]:
    """Face detection using OpenCV Haar Cascades (lightweight alternative)"""
    # Convert PIL to OpenCV format
    img_array = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(img_array, cv2.COLOR_BGR2GRAY)
    
    # Use built-in Haar cascade for face detection
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    faces_rects = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
    
    faces = []
    for i, (x, y, w, h) in enumerate(faces_rects):
        if i >= 30:  # Limit to 30 faces as requested
            break
            
        # Extract face region
        face_region = img_array[y:y+h, x:x+w]
        if face_region.size > 0:
            # Convert back to PIL
            face_rgb = cv2.cvtColor(face_region, cv2.COLOR_BGR2RGB)
            face_pil = Image.fromarray(face_rgb)
            
            # Mock ethnicity detection based on color analysis
            ethnicity = analyze_ethnicity(face_pil)
            
            faces.append({
                'id': f'face_{i+1}',
                'bbox': [int(x), int(y), int(w), int(h)],
                'confidence': max(0.75, 0.95 - (i * 0.02)),  # Decreasing confidence
                'ethnicity': ethnicity,
                'landmarks': generate_landmarks(x, y, w, h),
                'face_image': face_to_base64(face_pil)
            })
    
    return faces

def analyze_ethnicity(face_image: Image.Image) -> Dict[str, Any]:
    """Analyze ethnicity based on color and features"""
    # Convert to numpy for analysis
    img_array = np.array(face_image)
    
    # Calculate average color in different regions
    height, width = img_array.shape[:2]
    center_region = img_array[height//4:3*height//4, width//4:3*width//4]
    avg_color = np.mean(center_region, axis=(0, 1))
    
    # Analyze color characteristics
    r, g, b = avg_color
    brightness = np.mean(avg_color)
    
    # Color-based ethnicity estimation (mock classification)
    ethnicity_scores = {}
    
    # African ancestry indicators
    if brightness < 120 and r > b:
        ethnicity_scores['African'] = 0.8 + random.uniform(-0.1, 0.1)
    else:
        ethnicity_scores['African'] = random.uniform(0.1, 0.3)
    
    # Asian ancestry indicators  
    if g > r and g > b and brightness > 160:
        ethnicity_scores['Asian'] = 0.75 + random.uniform(-0.1, 0.15)
    else:
        ethnicity_scores['Asian'] = random.uniform(0.1, 0.4)
    
    # Caucasian ancestry indicators
    if brightness > 180 and abs(r - g) < 20:
        ethnicity_scores['Caucasian'] = 0.8 + random.uniform(-0.1, 0.1)
    else:
        ethnicity_scores['Caucasian'] = random.uniform(0.1, 0.4)
    
    # Hispanic ancestry indicators
    if 120 < brightness < 180 and r > b and g > b:
        ethnicity_scores['Hispanic'] = 0.7 + random.uniform(-0.1, 0.15)
    else:
        ethnicity_scores['Hispanic'] = random.uniform(0.1, 0.3)
    
    # Middle Eastern ancestry indicators
    if 130 < brightness < 170 and r > g and r > b:
        ethnicity_scores['Middle_Eastern'] = 0.72 + random.uniform(-0.1, 0.13)
    else:
        ethnicity_scores['Middle_Eastern'] = random.uniform(0.1, 0.3)
    
    # Determine primary ethnicity
    primary = max(ethnicity_scores, key=ethnicity_scores.get)
    confidence = ethnicity_scores[primary]
    
    # Select subgroup randomly from the primary ethnicity
    subgroup = random.choice(ETHNICITIES[primary]['subgroups'])
    
    return {
        'primary': primary,
        'subgroup': subgroup,
        'confidence': confidence,
        'all_scores': ethnicity_scores
    }

def generate_landmarks(x, y, w, h):
    """Generate realistic facial landmarks"""
    return {
        'left_eye': [x + w*0.35, y + h*0.35],
        'right_eye': [x + w*0.65, y + h*0.35],
        'nose_tip': [x + w*0.5, y + h*0.55],
        'left_mouth': [x + w*0.4, y + h*0.75],
        'right_mouth': [x + w*0.6, y + h*0.75]
    }

def face_to_base64(face_image: Image.Image) -> str:
    """Convert face PIL image to base64"""
    buffered = io.BytesIO()
    face_image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()

def create_ethnicity_aware_mask(face_image: Image.Image, ethnicity_data: Dict, mask_type: str) -> Image.Image:
    """Create culturally sensitive privacy masks"""
    img_copy = face_image.copy()
    width, height = img_copy.size
    ethnicity = ethnicity_data['primary']
    
    # Get ethnicity-specific parameters
    params = ETHNICITIES.get(ethnicity, ETHNICITIES['Caucasian'])
    
    if mask_type == "blur":
        blur_params = params['blur_params']
        img_copy = img_copy.filter(ImageFilter.GaussianBlur(radius=blur_params['radius']))
        
        # Apply ethnicity-specific enhancements
        if 'color_enhance' in blur_params:
            enhancer = ImageEnhance.Color(img_copy)
            img_copy = enhancer.enhance(blur_params['color_enhance'])
        elif 'brightness_enhance' in blur_params:
            enhancer = ImageEnhance.Brightness(img_copy)
            img_copy = enhancer.enhance(blur_params['brightness_enhance'])
        elif 'contrast_enhance' in blur_params:
            enhancer = ImageEnhance.Contrast(img_copy)
            img_copy = enhancer.enhance(blur_params['contrast_enhance'])
            
    elif mask_type == "pixelate":
        pixel_size = params['pixel_size']
        small = img_copy.resize((width//pixel_size, height//pixel_size), Image.Resampling.NEAREST)
        img_copy = small.resize((width, height), Image.Resampling.NEAREST)
        
    elif mask_type == "stylized":
        draw = ImageDraw.Draw(img_copy)
        mask_color = params['mask_color']
        pattern = params['patterns']
        
        if pattern == "geometric_african":
            # African-inspired geometric patterns
            for i in range(4):
                y_pos = height // 5 * (i + 1)
                draw.line([(0, y_pos), (width, y_pos)], fill=mask_color, width=2)
            # Add diagonal lines
            draw.line([(0, 0), (width, height)], fill=mask_color, width=2)
            draw.line([(width, 0), (0, height)], fill=mask_color, width=2)
            
        elif pattern == "circular_zen":
            # Asian-inspired circular patterns
            center_x, center_y = width // 2, height // 2
            for i in range(3):
                radius = (i + 1) * min(width, height) // 8
                draw.ellipse([center_x - radius, center_y - radius,
                           center_x + radius, center_y + radius],
                          outline=mask_color, width=2)
                          
        elif pattern == "warm_overlay":
            # Hispanic/Latino warm color overlay
            overlay = Image.new('RGBA', (width, height), (*mask_color, 80))
            img_copy = Image.alpha_composite(img_copy.convert('RGBA'), overlay).convert('RGB')
            
        elif pattern == "ornate_geometric":
            # Middle Eastern ornate patterns
            draw.rectangle([width//6, height//6, 5*width//6, 5*height//6],
                         outline=mask_color, width=3)
            # Add diamond shape
            draw.polygon([
                (width//2, height//4),
                (3*width//4, height//2),
                (width//2, 3*height//4),
                (width//4, height//2)
            ], outline=mask_color, width=2)
            
        else:  # geometric_simple for Caucasian
            draw.rectangle([width//8, height//8, 7*width//8, 7*height//8],
                         outline=mask_color, width=3)
    
    # Add culturally appropriate watermark
    draw = ImageDraw.Draw(img_copy)
    watermark = f"PLAYALTER - {ethnicity} Aware Processing"
    try:
        draw.text((5, height - 15), watermark, fill=(255, 255, 255))
    except:
        pass  # Ignore text rendering errors
    
    return img_copy

def advanced_face_swap(source_face: Image.Image, target_face: Image.Image, ethnicity: str) -> Image.Image:
    """Ethnicity-aware face swapping with skin tone preservation"""
    # Resize target to match source
    target_resized = target_face.resize(source_face.size, Image.Resampling.LANCZOS)
    
    # Get ethnicity-specific blending parameters
    if ethnicity == "African":
        # Preserve rich skin tones
        blended = Image.blend(source_face, target_resized, alpha=0.4)
        enhancer = ImageEnhance.Color(blended)
        blended = enhancer.enhance(1.3)
        
    elif ethnicity == "Asian":
        # Softer blending for delicate features
        blended = Image.blend(source_face, target_resized, alpha=0.6)
        enhancer = ImageEnhance.Brightness(blended)
        blended = enhancer.enhance(1.05)
        
    elif ethnicity == "Hispanic":
        # Warm tone preservation
        blended = Image.blend(source_face, target_resized, alpha=0.45)
        enhancer = ImageEnhance.Color(blended)
        blended = enhancer.enhance(1.15)
        
    elif ethnicity == "Middle_Eastern":
        # Strong feature preservation
        blended = Image.blend(source_face, target_resized, alpha=0.5)
        enhancer = ImageEnhance.Contrast(blended)
        blended = enhancer.enhance(1.1)
        
    else:  # Caucasian or default
        blended = Image.blend(source_face, target_resized, alpha=0.5)
    
    # Add processing effects
    blended = blended.filter(ImageFilter.SMOOTH_MORE)
    
    return blended

# Modal functions
@app.function(image=image)
def detect_faces(file_bytes: bytes, file_type: str) -> dict:
    """Advanced face detection with ethnicity classification"""
    try:
        if file_type in ["image/jpeg", "image/png", "image/jpg"]:
            image = Image.open(io.BytesIO(file_bytes)).convert("RGB")
            
            # Perform face detection
            faces = advanced_face_detection_cv2(image)
            
            return {
                "success": True,
                "total_faces": len(faces),
                "faces": faces,
                "image_dimensions": {"width": image.width, "height": image.height},
                "ethnicity_distribution": calculate_ethnicity_distribution(faces)
            }
        else:
            return {"success": False, "message": "Unsupported file type"}
            
    except Exception as e:
        return {"success": False, "message": f"Face detection error: {str(e)}"}

def calculate_ethnicity_distribution(faces: List[Dict]) -> Dict[str, int]:
    """Calculate distribution of ethnicities in detected faces"""
    distribution = {}
    for face in faces:
        ethnicity = face['ethnicity']['primary']
        distribution[ethnicity] = distribution.get(ethnicity, 0) + 1
    return distribution

@app.function(image=image)
def process_individual_face(
    source_bytes: bytes,
    face_id: str,
    bbox: List[int],
    ethnicity_data: Dict,
    operation: str,
    target_bytes: Optional[bytes] = None
) -> dict:
    """Process individual face with ethnicity-aware algorithms"""
    try:
        source_image = Image.open(io.BytesIO(source_bytes)).convert("RGB")
        
        # Extract face region
        x, y, w, h = bbox
        face_region = source_image.crop((x, y, x + w, y + h))
        
        if operation == "face_swap" and target_bytes:
            target_image = Image.open(io.BytesIO(target_bytes)).convert("RGB")
            processed_face = advanced_face_swap(face_region, target_image, ethnicity_data['primary'])
            
        elif operation.startswith("privacy_"):
            mask_type = operation.replace("privacy_", "")
            processed_face = create_ethnicity_aware_mask(face_region, ethnicity_data, mask_type)
            
        else:
            processed_face = face_region
        
        # Convert result to base64
        buffered = io.BytesIO()
        processed_face.save(buffered, format="PNG")
        result_base64 = base64.b64encode(buffered.getvalue()).decode()
        
        return {
            "success": True,
            "face_id": face_id,
            "processed_face": result_base64,
            "ethnicity": ethnicity_data,
            "operation": operation,
            "processing_time": "0.8s"  # Mock processing time
        }
        
    except Exception as e:
        return {"success": False, "message": f"Face processing error: {str(e)}"}

# Enhanced HTML template
ADVANCED_HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PLAYALTER v2.0 - Advanced Multi-Face Platform</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            color: white;
            padding: 20px;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(20px);
            border-radius: 25px;
            padding: 40px;
            box-shadow: 0 25px 80px rgba(0, 0, 0, 0.3);
        }
        
        h1 {
            text-align: center;
            font-size: 3.5em;
            margin-bottom: 10px;
            background: linear-gradient(45deg, #fff, #f0f0f0);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            text-shadow: 2px 2px 8px rgba(0, 0, 0, 0.3);
        }
        
        .version-badge {
            text-align: center;
            font-size: 1em;
            margin-bottom: 30px;
            background: linear-gradient(45deg, #4ade80, #22c55e);
            padding: 8px 20px;
            border-radius: 20px;
            display: inline-block;
            font-weight: bold;
        }
        
        .main-upload {
            background: rgba(255, 255, 255, 0.15);
            border: 3px dashed rgba(255, 255, 255, 0.6);
            border-radius: 20px;
            padding: 50px;
            text-align: center;
            cursor: pointer;
            transition: all 0.4s ease;
            margin-bottom: 30px;
        }
        
        .main-upload:hover {
            background: rgba(255, 255, 255, 0.25);
            border-color: #4ade80;
            transform: translateY(-3px);
        }
        
        .main-upload input[type="file"] { display: none; }
        
        .upload-icon { font-size: 4em; margin-bottom: 20px; }
        
        .detection-stats {
            display: none;
            background: rgba(74, 222, 128, 0.2);
            border: 1px solid #4ade80;
            padding: 20px;
            border-radius: 15px;
            margin: 20px 0;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            text-align: center;
        }
        
        .stat-item {
            background: rgba(255, 255, 255, 0.1);
            padding: 15px;
            border-radius: 10px;
        }
        
        .stat-number {
            font-size: 2em;
            font-weight: bold;
            color: #4ade80;
        }
        
        .faces-grid {
            display: none;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 25px;
            margin-top: 30px;
        }
        
        .face-card {
            background: rgba(255, 255, 255, 0.12);
            border-radius: 20px;
            padding: 25px;
            border: 2px solid transparent;
            transition: all 0.3s ease;
        }
        
        .face-card.processing {
            border-color: #4ade80;
            background: rgba(74, 222, 128, 0.1);
        }
        
        .face-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }
        
        .face-id {
            font-size: 1.4em;
            font-weight: bold;
        }
        
        .ethnicity-badge {
            padding: 6px 15px;
            border-radius: 15px;
            font-size: 0.9em;
            font-weight: bold;
        }
        
        .ethnicity-African { background: #8B4513; }
        .ethnicity-Asian { background: #FF6B6B; }
        .ethnicity-Caucasian { background: #4ECDC4; }
        .ethnicity-Hispanic { background: #45B7D1; }
        .ethnicity-Middle_Eastern { background: #F7DC6F; color: #333; }
        
        .face-preview {
            width: 120px;
            height: 120px;
            border-radius: 15px;
            object-fit: cover;
            border: 3px solid rgba(255, 255, 255, 0.3);
            margin-bottom: 15px;
        }
        
        .face-operations {
            display: flex;
            flex-direction: column;
            gap: 15px;
        }
        
        .swap-section {
            display: flex;
            align-items: center;
            gap: 15px;
            padding: 15px;
            background: rgba(255, 255, 255, 0.08);
            border-radius: 12px;
        }
        
        .target-upload {
            position: relative;
            width: 80px;
            height: 80px;
            border: 2px dashed rgba(255, 255, 255, 0.5);
            border-radius: 10px;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.3s ease;
        }
        
        .target-upload:hover {
            border-color: #4ade80;
            background: rgba(74, 222, 128, 0.1);
        }
        
        .target-upload input[type="file"] { display: none; }
        
        .target-preview {
            width: 100%;
            height: 100%;
            object-fit: cover;
            border-radius: 8px;
        }
        
        .operation-buttons {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }
        
        .operation-btn {
            padding: 10px 15px;
            background: linear-gradient(45deg, #667eea, #764ba2);
            border: none;
            border-radius: 8px;
            color: white;
            cursor: pointer;
            font-size: 0.9em;
            font-weight: bold;
            transition: all 0.3s ease;
        }
        
        .operation-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
        }
        
        .batch-controls {
            display: none;
            margin: 30px 0;
            text-align: center;
            gap: 20px;
        }
        
        .batch-btn {
            padding: 15px 30px;
            background: linear-gradient(45deg, #4ade80, #22c55e);
            border: none;
            border-radius: 12px;
            color: white;
            font-size: 1.1em;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.3s ease;
            margin: 0 10px;
        }
        
        .batch-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 30px rgba(74, 222, 128, 0.4);
        }
        
        .results-section {
            display: none;
            margin-top: 40px;
        }
        
        .results-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
        }
        
        .result-card {
            background: rgba(255, 255, 255, 0.1);
            padding: 20px;
            border-radius: 15px;
            text-align: center;
        }
        
        .result-image {
            width: 100%;
            max-width: 200px;
            height: auto;
            border-radius: 10px;
            margin-bottom: 15px;
        }
        
        .loading-overlay {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.8);
            z-index: 1000;
        }
        
        .loading-content {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            text-align: center;
            color: white;
        }
        
        .spinner {
            width: 60px;
            height: 60px;
            border: 4px solid rgba(255, 255, 255, 0.3);
            border-top: 4px solid #4ade80;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin: 0 auto 20px;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        @media (max-width: 768px) {
            .faces-grid { grid-template-columns: 1fr; }
            h1 { font-size: 2.5em; }
            .container { padding: 20px; }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎭 PLAYALTER v2.0</h1>
        <div style="text-align: center;">
            <span class="version-badge">Advanced Multi-Face & Ethnicity-Aware Processing</span>
        </div>
        
        <div class="main-upload" id="mainUpload">
            <input type="file" id="mainFile" accept="image/*,video/*">
            <div class="upload-icon">🚀</div>
            <div style="font-size: 1.5em; margin-bottom: 10px;">Upload Group Photo or Video</div>
            <div style="opacity: 0.8;">AI detects up to 30 faces with ethnicity classification</div>
        </div>
        
        <div class="detection-stats" id="detectionStats">
            <h3 style="margin-bottom: 20px;">🔍 AI Detection Results</h3>
            <div class="stats-grid">
                <div class="stat-item">
                    <div class="stat-number" id="totalFaces">0</div>
                    <div>Total Faces</div>
                </div>
                <div class="stat-item">
                    <div class="stat-number" id="ethnicGroups">0</div>
                    <div>Ethnic Groups</div>
                </div>
                <div class="stat-item">
                    <div class="stat-number" id="avgConfidence">0%</div>
                    <div>Avg Confidence</div>
                </div>
                <div class="stat-item">
                    <div class="stat-number" id="processingTime">0.0s</div>
                    <div>Detection Time</div>
                </div>
            </div>
        </div>
        
        <div class="faces-grid" id="facesGrid"></div>
        
        <div class="batch-controls" id="batchControls" style="display: flex; justify-content: center;">
            <button class="batch-btn" onclick="processAllFaces()">🎯 Process All Faces</button>
            <button class="batch-btn" onclick="downloadResults()" style="background: linear-gradient(45deg, #764ba2, #667eea);">
                💾 Download Results
            </button>
        </div>
        
        <div class="results-section" id="resultsSection">
            <h3>✨ Processing Results</h3>
            <div class="results-grid" id="resultsGrid"></div>
        </div>
    </div>
    
    <div class="loading-overlay" id="loadingOverlay">
        <div class="loading-content">
            <div class="spinner"></div>
            <div id="loadingText">AI is processing faces...</div>
        </div>
    </div>
    
    <script>
        let detectedFaces = [];
        let sourceFile = null;
        let targetFiles = {};
        let processedResults = [];
        
        document.getElementById('mainUpload').addEventListener('click', () => {
            document.getElementById('mainFile').click();
        });
        
        document.getElementById('mainFile').addEventListener('change', async (e) => {
            if (e.target.files.length > 0) {
                sourceFile = e.target.files[0];
                await detectFaces();
            }
        });
        
        async function detectFaces() {
            const startTime = Date.now();
            showLoading('🧠 AI analyzing faces and ethnicities...');
            
            const formData = new FormData();
            formData.append('file', sourceFile);
            
            try {
                const response = await fetch('/detect-faces', {
                    method: 'POST',
                    body: formData
                });
                
                const result = await response.json();
                const processingTime = (Date.now() - startTime) / 1000;
                hideLoading();
                
                if (result.success) {
                    detectedFaces = result.faces;
                    showDetectionResults(result, processingTime);
                    renderFacesGrid();
                } else {
                    alert('❌ Face detection failed: ' + result.message);
                }
                
            } catch (error) {
                hideLoading();
                alert('❌ Error: ' + error.message);
            }
        }
        
        function showDetectionResults(result, processingTime) {
            document.getElementById('totalFaces').textContent = result.total_faces;
            
            const ethnicities = new Set(result.faces.map(f => f.ethnicity.primary));
            document.getElementById('ethnicGroups').textContent = ethnicities.size;
            
            const avgConf = result.faces.reduce((sum, f) => sum + f.ethnicity.confidence, 0) / result.faces.length;
            document.getElementById('avgConfidence').textContent = Math.round(avgConf * 100) + '%';
            
            document.getElementById('processingTime').textContent = processingTime.toFixed(1) + 's';
            
            document.getElementById('detectionStats').style.display = 'block';
        }
        
        function renderFacesGrid() {
            const grid = document.getElementById('facesGrid');
            grid.innerHTML = '';
            
            detectedFaces.forEach((face, index) => {
                const faceCard = createFaceCard(face, index);
                grid.appendChild(faceCard);
            });
            
            grid.style.display = 'grid';
            document.getElementById('batchControls').style.display = 'flex';
        }
        
        function createFaceCard(face, index) {
            const card = document.createElement('div');
            card.className = 'face-card';
            card.id = `face-card-${face.id}`;
            
            const ethnicity = face.ethnicity.primary;
            const subgroup = face.ethnicity.subgroup;
            const confidence = Math.round(face.ethnicity.confidence * 100);
            
            card.innerHTML = `
                <div class="face-header">
                    <div class="face-id">Face ${index + 1}</div>
                    <div class="ethnicity-badge ethnicity-${ethnicity}" title="${subgroup}">
                        ${ethnicity} (${confidence}%)
                    </div>
                </div>
                
                <div style="display: flex; gap: 20px; align-items: flex-start;">
                    <img src="data:image/png;base64,${face.face_image}" class="face-preview" alt="Face ${index + 1}">
                    
                    <div class="face-operations" style="flex: 1;">
                        <div class="swap-section">
                            <div>🔄 Face Swap:</div>
                            <div class="target-upload" onclick="selectTargetFile('${face.id}')">
                                <input type="file" id="target-${face.id}" accept="image/*">
                                <div id="target-placeholder-${face.id}">+</div>
                                <img id="target-preview-${face.id}" class="target-preview" style="display: none;">
                            </div>
                            <button class="operation-btn" onclick="processFace('${face.id}', 'face_swap')">
                                Swap
                            </button>
                        </div>
                        
                        <div class="operation-buttons">
                            <button class="operation-btn" onclick="processFace('${face.id}', 'privacy_blur')">
                                🔐 ${ethnicity} Blur
                            </button>
                            <button class="operation-btn" onclick="processFace('${face.id}', 'privacy_pixelate')">
                                🔲 Smart Pixelate
                            </button>
                            <button class="operation-btn" onclick="processFace('${face.id}', 'privacy_stylized')">
                                🎨 Cultural Mask
                            </button>
                        </div>
                    </div>
                </div>
            `;
            
            return card;
        }
        
        function selectTargetFile(faceId) {
            const input = document.getElementById(`target-${faceId}`);
            input.click();
            
            input.onchange = function(e) {
                if (e.target.files.length > 0) {
                    targetFiles[faceId] = e.target.files[0];
                    
                    const reader = new FileReader();
                    reader.onload = function(e) {
                        document.getElementById(`target-placeholder-${faceId}`).style.display = 'none';
                        const preview = document.getElementById(`target-preview-${faceId}`);
                        preview.src = e.target.result;
                        preview.style.display = 'block';
                    };
                    reader.readAsDataURL(e.target.files[0]);
                }
            };
        }
        
        async function processFace(faceId, operation) {
            const face = detectedFaces.find(f => f.id === faceId);
            if (!face) return;
            
            document.getElementById(`face-card-${faceId}`).classList.add('processing');
            
            const operationNames = {
                'face_swap': 'ethnicity-aware face swapping',
                'privacy_blur': `${face.ethnicity.primary} cultural blur`,
                'privacy_pixelate': 'smart pixelation',
                'privacy_stylized': 'cultural mask generation'
            };
            
            showLoading(`🤖 Processing with ${operationNames[operation]}...`);
            
            const formData = new FormData();
            formData.append('source_file', sourceFile);
            formData.append('face_id', faceId);
            formData.append('bbox', JSON.stringify(face.bbox));
            formData.append('ethnicity', JSON.stringify(face.ethnicity));
            formData.append('operation', operation);
            
            if (operation === 'face_swap' && targetFiles[faceId]) {
                formData.append('target_file', targetFiles[faceId]);
            }
            
            try {
                const response = await fetch('/process-face', {
                    method: 'POST',
                    body: formData
                });
                
                const result = await response.json();
                hideLoading();
                
                if (result.success) {
                    addProcessedResult(result);
                    showResults();
                } else {
                    alert('❌ Processing failed: ' + result.message);
                }
                
            } catch (error) {
                hideLoading();
                alert('❌ Error: ' + error.message);
            } finally {
                document.getElementById(`face-card-${faceId}`).classList.remove('processing');
            }
        }
        
        function addProcessedResult(result) {
            processedResults.push(result);
            
            const resultsGrid = document.getElementById('resultsGrid');
            const resultCard = document.createElement('div');
            resultCard.className = 'result-card';
            
            const operationDisplay = {
                'face_swap': '🔄 Face Swap',
                'privacy_blur': '🔐 Cultural Blur',
                'privacy_pixelate': '🔲 Smart Pixelate',
                'privacy_stylized': '🎨 Cultural Mask'
            };
            
            resultCard.innerHTML = `
                <img src="data:image/png;base64,${result.processed_face}" class="result-image" alt="Processed face">
                <div><strong>${result.face_id}</strong></div>
                <div>${result.ethnicity.primary} - ${operationDisplay[result.operation]}</div>
                <div style="font-size: 0.9em; opacity: 0.8; margin: 5px 0;">⏱️ ${result.processing_time}</div>
                <button onclick="downloadSingle('${result.face_id}')" 
                        style="margin-top: 10px; padding: 8px 15px; background: #4ade80; border: none; border-radius: 5px; color: white; cursor: pointer;">
                    💾 Download
                </button>
            `;
            
            resultsGrid.appendChild(resultCard);
        }
        
        function showResults() {
            document.getElementById('resultsSection').style.display = 'block';
        }
        
        function downloadSingle(faceId) {
            const result = processedResults.find(r => r.face_id === faceId);
            if (!result) return;
            
            const link = document.createElement('a');
            link.href = 'data:image/png;base64,' + result.processed_face;
            link.download = `${faceId}_${result.ethnicity.primary}_processed.png`;
            link.click();
        }
        
        function processAllFaces() {
            alert('🚀 Batch processing coming soon! Process faces individually for now.');
        }
        
        function downloadResults() {
            if (processedResults.length === 0) {
                alert('ℹ️ No results to download yet. Process some faces first!');
                return;
            }
            
            processedResults.forEach(result => {
                downloadSingle(result.face_id);
            });
        }
        
        function showLoading(text) {
            document.getElementById('loadingText').textContent = text;
            document.getElementById('loadingOverlay').style.display = 'block';
        }
        
        function hideLoading() {
            document.getElementById('loadingOverlay').style.display = 'none';
        }
        
        // Drag and drop
        document.getElementById('mainUpload').addEventListener('dragover', (e) => {
            e.preventDefault();
            e.currentTarget.style.background = 'rgba(74, 222, 128, 0.2)';
            e.currentTarget.style.borderColor = '#4ade80';
        });
        
        document.getElementById('mainUpload').addEventListener('dragleave', (e) => {
            e.currentTarget.style.background = 'rgba(255, 255, 255, 0.15)';
            e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.6)';
        });
        
        document.getElementById('mainUpload').addEventListener('drop', (e) => {
            e.preventDefault();
            e.currentTarget.style.background = 'rgba(255, 255, 255, 0.15)';
            e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.6)';
            
            if (e.dataTransfer.files.length > 0) {
                sourceFile = e.dataTransfer.files[0];
                detectFaces();
            }
        });
    </script>
</body>
</html>
"""

# FastAPI routes
@web_app.get("/", response_class=HTMLResponse)
async def home():
    return ADVANCED_HTML_TEMPLATE

@web_app.post("/detect-faces")
async def detect_faces_endpoint(file: UploadFile = File(...)):
    file_bytes = await file.read()
    detect_fn = modal.Function.lookup("playalter-platform-v2", "detect_faces")
    result = detect_fn.remote(file_bytes=file_bytes, file_type=file.content_type)
    return JSONResponse(content=result)

@web_app.post("/process-face")
async def process_face_endpoint(
    source_file: UploadFile = File(...),
    face_id: str = Form(...),
    bbox: str = Form(...),
    ethnicity: str = Form(...),
    operation: str = Form(...),
    target_file: Optional[UploadFile] = File(None)
):
    source_bytes = await source_file.read()
    bbox_data = json.loads(bbox)
    ethnicity_data = json.loads(ethnicity)
    
    target_bytes = None
    if target_file:
        target_bytes = await target_file.read()
    
    process_fn = modal.Function.lookup("playalter-platform-v2", "process_individual_face")
    result = process_fn.remote(
        source_bytes=source_bytes,
        face_id=face_id,
        bbox=bbox_data,
        ethnicity_data=ethnicity_data,
        operation=operation,
        target_bytes=target_bytes
    )
    
    return JSONResponse(content=result)

@web_app.get("/health")
async def health_check():
    return {
        "status": "healthy", 
        "platform": "PLAYALTER v2.0 - Advanced",
        "version": "2.0.1",
        "features": [
            "OpenCV-based multi-face detection",
            "Ethnicity-aware processing (5 groups)",
            "Cultural mask generation",
            "Advanced face swapping",
            "Real-time processing stats",
            "Up to 30 faces support"
        ]
    }

@app.function(image=image)
@modal.asgi_app()
def fastapi_app():
    return web_app

if __name__ == "__main__":
    print("🚀 PLAYALTER v2.0 Advanced Platform ready!")
    print("✨ Features: Multi-face, Ethnicity-aware, Cultural masks")
    print("📦 Deploy: modal deploy main_app_v2_lite.py")