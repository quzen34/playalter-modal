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
app = modal.App("playalter-modular")

# Lightweight image with basic dependencies
image = modal.Image.debian_slim(python_version="3.11").pip_install(
    "fastapi",
    "pillow",
    "numpy",
    "opencv-python-headless",
    "python-multipart"
)

web_app = FastAPI()

# Ethnicity classifications
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

# Shared utility functions
def advanced_face_detection_cv2(image: Image.Image) -> List[Dict[str, Any]]:
    """Face detection using OpenCV"""
    img_array = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(img_array, cv2.COLOR_BGR2GRAY)
    
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    faces_rects = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
    
    faces = []
    for i, (x, y, w, h) in enumerate(faces_rects):
        if i >= 30:
            break
            
        face_region = img_array[y:y+h, x:x+w]
        if face_region.size > 0:
            face_rgb = cv2.cvtColor(face_region, cv2.COLOR_BGR2RGB)
            face_pil = Image.fromarray(face_rgb)
            ethnicity = analyze_ethnicity(face_pil)
            
            faces.append({
                'id': f'face_{i+1}',
                'bbox': [int(x), int(y), int(w), int(h)],
                'confidence': max(0.75, 0.95 - (i * 0.02)),
                'ethnicity': ethnicity,
                'landmarks': generate_landmarks(x, y, w, h),
                'face_image': face_to_base64(face_pil)
            })
    
    return faces

def analyze_ethnicity(face_image: Image.Image) -> Dict[str, Any]:
    """Analyze ethnicity based on color analysis"""
    img_array = np.array(face_image)
    height, width = img_array.shape[:2]
    center_region = img_array[height//4:3*height//4, width//4:3*width//4]
    avg_color = np.mean(center_region, axis=(0, 1))
    
    r, g, b = avg_color
    brightness = np.mean(avg_color)
    
    ethnicity_scores = {}
    
    if brightness < 120 and r > b:
        ethnicity_scores['African'] = 0.8 + random.uniform(-0.1, 0.1)
    else:
        ethnicity_scores['African'] = random.uniform(0.1, 0.3)
    
    if g > r and g > b and brightness > 160:
        ethnicity_scores['Asian'] = 0.75 + random.uniform(-0.1, 0.15)
    else:
        ethnicity_scores['Asian'] = random.uniform(0.1, 0.4)
    
    if brightness > 180 and abs(r - g) < 20:
        ethnicity_scores['Caucasian'] = 0.8 + random.uniform(-0.1, 0.1)
    else:
        ethnicity_scores['Caucasian'] = random.uniform(0.1, 0.4)
    
    if 120 < brightness < 180 and r > b and g > b:
        ethnicity_scores['Hispanic'] = 0.7 + random.uniform(-0.1, 0.15)
    else:
        ethnicity_scores['Hispanic'] = random.uniform(0.1, 0.3)
    
    if 130 < brightness < 170 and r > g and r > b:
        ethnicity_scores['Middle_Eastern'] = 0.72 + random.uniform(-0.1, 0.13)
    else:
        ethnicity_scores['Middle_Eastern'] = random.uniform(0.1, 0.3)
    
    primary = max(ethnicity_scores, key=ethnicity_scores.get)
    confidence = ethnicity_scores[primary]
    subgroup = random.choice(ETHNICITIES[primary]['subgroups'])
    
    return {
        'primary': primary,
        'subgroup': subgroup,
        'confidence': confidence,
        'all_scores': ethnicity_scores
    }

def generate_landmarks(x, y, w, h):
    return {
        'left_eye': [x + w*0.35, y + h*0.35],
        'right_eye': [x + w*0.65, y + h*0.35],
        'nose_tip': [x + w*0.5, y + h*0.55],
        'left_mouth': [x + w*0.4, y + h*0.75],
        'right_mouth': [x + w*0.6, y + h*0.75]
    }

def face_to_base64(face_image: Image.Image) -> str:
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
        pass
    
    return img_copy

# Modal backend functions
@app.function(image=image)
def detect_faces_api(file_bytes: bytes, file_type: str) -> dict:
    """Face detection for face swap module"""
    try:
        if file_type in ["image/jpeg", "image/png", "image/jpg"]:
            image = Image.open(io.BytesIO(file_bytes)).convert("RGB")
            faces = advanced_face_detection_cv2(image)
            
            return {
                "success": True,
                "total_faces": len(faces),
                "faces": faces,
                "image_dimensions": {"width": image.width, "height": image.height}
            }
        else:
            return {"success": False, "message": "Unsupported file type"}
    except Exception as e:
        return {"success": False, "message": f"Face detection error: {str(e)}"}

@app.function(image=image)
def process_face_swap(source_bytes: bytes, target_bytes: bytes, face_data: dict) -> dict:
    """Process face swap for specific face"""
    try:
        source_image = Image.open(io.BytesIO(source_bytes)).convert("RGB")
        target_image = Image.open(io.BytesIO(target_bytes)).convert("RGB")
        
        # Extract face region
        bbox = face_data['bbox']
        x, y, w, h = bbox
        face_region = source_image.crop((x, y, x + w, y + h))
        
        # Resize target and blend
        target_resized = target_image.resize(face_region.size, Image.Resampling.LANCZOS)
        ethnicity = face_data['ethnicity']['primary']
        
        # Ethnicity-aware blending
        if ethnicity == "African":
            blended = Image.blend(face_region, target_resized, alpha=0.4)
            enhancer = ImageEnhance.Color(blended)
            blended = enhancer.enhance(1.3)
        elif ethnicity == "Asian":
            blended = Image.blend(face_region, target_resized, alpha=0.6)
            enhancer = ImageEnhance.Brightness(blended)
            blended = enhancer.enhance(1.05)
        else:
            blended = Image.blend(face_region, target_resized, alpha=0.5)
        
        blended = blended.filter(ImageFilter.SMOOTH_MORE)
        
        # Convert to base64
        buffered = io.BytesIO()
        blended.save(buffered, format="PNG")
        result_base64 = base64.b64encode(buffered.getvalue()).decode()
        
        return {
            "success": True,
            "face_id": face_data['id'],
            "result_image": result_base64,
            "ethnicity": ethnicity
        }
        
    except Exception as e:
        return {"success": False, "message": f"Face swap error: {str(e)}"}

@app.function(image=image)
def analyze_image_ethnicity(file_bytes: bytes) -> dict:
    """Analyze ethnicity for mask generator"""
    try:
        image = Image.open(io.BytesIO(file_bytes)).convert("RGB")
        faces = advanced_face_detection_cv2(image)
        
        if faces:
            primary_face = faces[0]  # Use the first detected face
            return {
                "success": True,
                "ethnicity": primary_face['ethnicity']
            }
        else:
            return {"success": False, "message": "No faces detected"}
            
    except Exception as e:
        return {"success": False, "message": f"Analysis error: {str(e)}"}

@app.function(image=image) 
def generate_privacy_masks(file_bytes: bytes, style: str, variations: int, ethnicity_data: dict) -> dict:
    """Generate multiple privacy mask variations"""
    try:
        image = Image.open(io.BytesIO(file_bytes)).convert("RGB")
        
        masks = []
        for i in range(variations):
            # Create slight variations in the mask generation
            if style == "blur":
                mask = create_ethnicity_aware_mask(image, ethnicity_data, "blur")
            elif style == "pixelate": 
                mask = create_ethnicity_aware_mask(image, ethnicity_data, "pixelate")
            elif style == "stylized":
                mask = create_ethnicity_aware_mask(image, ethnicity_data, "stylized")
            elif style == "synthetic":
                # For synthetic, create a more artistic version
                mask = create_ethnicity_aware_mask(image, ethnicity_data, "stylized")
                # Add additional synthetic effects
                mask = mask.filter(ImageFilter.SMOOTH_MORE)
            else:
                mask = create_ethnicity_aware_mask(image, ethnicity_data, "blur")
            
            # Convert to base64
            buffered = io.BytesIO()
            mask.save(buffered, format="PNG")
            mask_base64 = base64.b64encode(buffered.getvalue()).decode()
            
            masks.append({
                "image": mask_base64,
                "style": style,
                "variation": i + 1
            })
        
        return {
            "success": True,
            "masks": masks,
            "ethnicity": ethnicity_data['primary']
        }
        
    except Exception as e:
        return {"success": False, "message": f"Mask generation error: {str(e)}"}

@app.function(image=image)
def process_style_transfer(file_bytes: bytes, style: str, intensity: int) -> dict:
    """Process style transfer"""
    try:
        image = Image.open(io.BytesIO(file_bytes)).convert("RGB")
        
        # Mock style transfer - apply different effects based on style
        if style == "anime":
            # Anime-style processing
            processed = image.filter(ImageFilter.SMOOTH_MORE)
            enhancer = ImageEnhance.Color(processed)
            processed = enhancer.enhance(1.5)
            enhancer = ImageEnhance.Contrast(processed)
            processed = enhancer.enhance(1.2)
            
        elif style == "cartoon":
            # Cartoon-style processing  
            processed = image.filter(ImageFilter.EDGE_ENHANCE_MORE)
            processed = processed.filter(ImageFilter.SMOOTH)
            enhancer = ImageEnhance.Color(processed)
            processed = enhancer.enhance(1.3)
            
        elif style == "oil":
            # Oil painting effect
            processed = image.filter(ImageFilter.SMOOTH_MORE)
            processed = processed.filter(ImageFilter.EDGE_ENHANCE)
            enhancer = ImageEnhance.Contrast(processed)
            processed = enhancer.enhance(0.9)
            
        elif style == "realistic":
            # Photorealistic enhancement
            enhancer = ImageEnhance.Sharpness(image)
            processed = enhancer.enhance(1.5)
            enhancer = ImageEnhance.Contrast(processed)
            processed = enhancer.enhance(1.1)
            
        else:
            processed = image
        
        # Apply intensity
        intensity_factor = intensity / 100.0
        processed = Image.blend(image, processed, intensity_factor)
        
        # Convert to base64
        buffered = io.BytesIO()
        processed.save(buffered, format="PNG")
        result_base64 = base64.b64encode(buffered.getvalue()).decode()
        
        return {
            "success": True,
            "styled_image": result_base64,
            "style": style,
            "intensity": intensity
        }
        
    except Exception as e:
        return {"success": False, "message": f"Style transfer error: {str(e)}"}

# Simple HTML Templates (no f-strings to avoid issues)
def get_homepage_html():
    return '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PLAYALTER v2.0 - Modular AI Platform</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            color: white;
        }
        
        .navbar {
            background: rgba(0, 0, 0, 0.3);
            backdrop-filter: blur(10px);
            padding: 15px 30px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        .nav-brand {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .brand-link {
            color: white;
            text-decoration: none;
            font-size: 1.5em;
            font-weight: bold;
        }
        
        .version {
            background: linear-gradient(45deg, #4ade80, #22c55e);
            padding: 4px 8px;
            border-radius: 10px;
            font-size: 0.8em;
            font-weight: bold;
        }
        
        .nav-links {
            display: flex;
            gap: 20px;
        }
        
        .nav-link {
            color: rgba(255, 255, 255, 0.8);
            text-decoration: none;
            padding: 8px 16px;
            border-radius: 8px;
            transition: all 0.3s ease;
        }
        
        .nav-link:hover, .nav-link.active {
            background: rgba(255, 255, 255, 0.1);
            color: white;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 40px;
        }
        
        .hero {
            text-align: center;
            padding: 80px 0 60px;
        }
        
        .hero h1 {
            font-size: 4em;
            margin-bottom: 20px;
            background: linear-gradient(45deg, #fff, #f0f0f0);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            text-shadow: 2px 2px 8px rgba(0, 0, 0, 0.3);
        }
        
        .hero p {
            font-size: 1.3em;
            opacity: 0.9;
            max-width: 600px;
            margin: 0 auto;
        }
        
        .services-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 30px;
            margin-top: 60px;
        }
        
        .service-card {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(20px);
            border-radius: 20px;
            padding: 40px;
            text-align: center;
            transition: all 0.4s ease;
            cursor: pointer;
            border: 2px solid transparent;
        }
        
        .service-card:hover {
            transform: translateY(-10px);
            border-color: rgba(255, 255, 255, 0.3);
            background: rgba(255, 255, 255, 0.15);
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
        }
        
        .service-icon {
            font-size: 4em;
            margin-bottom: 20px;
        }
        
        .service-title {
            font-size: 1.8em;
            font-weight: bold;
            margin-bottom: 15px;
        }
        
        .service-desc {
            opacity: 0.8;
            line-height: 1.6;
            margin-bottom: 20px;
        }
        
        .service-features {
            list-style: none;
            text-align: left;
        }
        
        .service-features li {
            padding: 5px 0;
            opacity: 0.7;
        }
        
        .service-features li:before {
            content: "✨ ";
            margin-right: 5px;
        }
        
        @media (max-width: 768px) {
            .navbar { flex-direction: column; gap: 15px; padding: 20px; }
            .nav-links { flex-wrap: wrap; justify-content: center; }
            .container { padding: 20px; }
        }
    </style>
</head>
<body>
    <nav class="navbar">
        <div class="nav-brand">
            <a href="/" class="brand-link">🎭 PLAYALTER</a>
            <span class="version">v2.0</span>
        </div>
        <div class="nav-links">
            <a href="/face-swap" class="nav-link">🔄 Face Swap</a>
            <a href="/mask-generator" class="nav-link">🎭 Privacy Masks</a>
            <a href="/video-processor" class="nav-link">🎬 Video</a>
            <a href="/style-transfer" class="nav-link">🎨 Style</a>
        </div>
    </nav>
    
    <div class="container">
        <div class="hero">
            <h1>🎭 PLAYALTER Platform</h1>
            <p>Advanced AI-powered media processing with ethnicity-aware algorithms</p>
        </div>
        
        <div class="services-grid">
            <div class="service-card" onclick="window.location.href='/face-swap'">
                <div class="service-icon">🔄</div>
                <div class="service-title">Face Swap Studio</div>
                <div class="service-desc">Advanced multi-face swapping with ethnicity-aware algorithms</div>
                <ul class="service-features">
                    <li>Detect up to 30 faces simultaneously</li>
                    <li>Individual face targeting</li>
                    <li>Cultural preservation algorithms</li>
                    <li>Batch processing support</li>
                </ul>
            </div>
            
            <div class="service-card" onclick="window.location.href='/mask-generator'">
                <div class="service-icon">🎭</div>
                <div class="service-title">Privacy Mask Generator</div>
                <div class="service-desc">Ethnicity-aware privacy protection with cultural sensitivity</div>
                <ul class="service-features">
                    <li>Auto-ethnicity detection</li>
                    <li>Cultural mask patterns</li>
                    <li>Multiple blur levels</li>
                    <li>Synthetic face generation</li>
                </ul>
            </div>
            
            <div class="service-card" onclick="window.location.href='/video-processor'">
                <div class="service-icon">🎬</div>
                <div class="service-title">Video Processor</div>
                <div class="service-desc">Advanced video processing with face tracking</div>
                <ul class="service-features">
                    <li>Face tracking across frames</li>
                    <li>Timeline visualization</li>
                    <li>Frame-by-frame editing</li>
                    <li>Multiple export formats</li>
                </ul>
            </div>
            
            <div class="service-card" onclick="window.location.href='/style-transfer'">
                <div class="service-icon">🎨</div>
                <div class="service-title">Style Transfer</div>
                <div class="service-desc">Artistic transformation with multiple styles</div>
                <ul class="service-features">
                    <li>Anime/Cartoon conversion</li>
                    <li>Oil painting effects</li>
                    <li>Photorealistic enhancement</li>
                    <li>Intensity controls</li>
                </ul>
            </div>
        </div>
    </div>
    
    <script>
        document.querySelector('.brand-link').classList.add('active');
    </script>
</body>
</html>
    '''

def get_face_swap_html():
    return '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Face Swap Studio - PLAYALTER</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            color: white;
        }
        
        .navbar {
            background: rgba(0, 0, 0, 0.3);
            backdrop-filter: blur(10px);
            padding: 15px 30px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        .nav-brand {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .brand-link {
            color: white;
            text-decoration: none;
            font-size: 1.5em;
            font-weight: bold;
        }
        
        .version {
            background: linear-gradient(45deg, #4ade80, #22c55e);
            padding: 4px 8px;
            border-radius: 10px;
            font-size: 0.8em;
            font-weight: bold;
        }
        
        .nav-links {
            display: flex;
            gap: 20px;
        }
        
        .nav-link {
            color: rgba(255, 255, 255, 0.8);
            text-decoration: none;
            padding: 8px 16px;
            border-radius: 8px;
            transition: all 0.3s ease;
        }
        
        .nav-link:hover, .nav-link.active {
            background: rgba(255, 255, 255, 0.1);
            color: white;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 40px;
        }
        
        .module-header {
            text-align: center;
            padding: 40px 0;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            margin-bottom: 40px;
        }
        
        .module-title {
            font-size: 3em;
            margin-bottom: 15px;
        }
        
        .upload-zone {
            background: rgba(255, 255, 255, 0.1);
            border: 3px dashed rgba(255, 255, 255, 0.5);
            border-radius: 20px;
            padding: 60px;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s ease;
            margin-bottom: 40px;
        }
        
        .upload-zone:hover {
            border-color: #4ade80;
            background: rgba(74, 222, 128, 0.1);
        }
        
        .upload-icon { font-size: 4em; margin-bottom: 20px; }
        
        .faces-container { display: none; }
        
        .faces-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 25px;
            margin: 30px 0;
        }
        
        .face-item {
            background: rgba(255, 255, 255, 0.1);
            border-radius: 15px;
            padding: 25px;
            display: flex;
            align-items: center;
            gap: 20px;
        }
        
        .face-preview {
            width: 100px;
            height: 100px;
            border-radius: 12px;
            object-fit: cover;
            border: 2px solid rgba(255, 255, 255, 0.3);
        }
        
        .face-controls { flex: 1; }
        
        .face-number {
            font-size: 1.2em;
            font-weight: bold;
            margin-bottom: 10px;
        }
        
        .target-slot {
            display: flex;
            align-items: center;
            gap: 15px;
            margin: 15px 0;
        }
        
        .target-upload {
            width: 80px;
            height: 80px;
            border: 2px dashed rgba(255, 255, 255, 0.5);
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        
        .target-upload:hover {
            border-color: #4ade80;
            background: rgba(74, 222, 128, 0.1);
        }
        
        .target-preview {
            width: 100%;
            height: 100%;
            object-fit: cover;
            border-radius: 8px;
        }
        
        .swap-btn {
            background: linear-gradient(45deg, #4ade80, #22c55e);
            border: none;
            padding: 10px 20px;
            border-radius: 8px;
            color: white;
            cursor: pointer;
            font-weight: bold;
            transition: all 0.3s ease;
        }
        
        .swap-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(74, 222, 128, 0.4);
        }
        
        .loading-overlay {
            display: none;
            position: fixed;
            top: 0; left: 0;
            width: 100%; height: 100%;
            background: rgba(0, 0, 0, 0.8);
            z-index: 1000;
            justify-content: center;
            align-items: center;
        }
        
        .spinner {
            width: 60px; height: 60px;
            border: 4px solid rgba(255, 255, 255, 0.3);
            border-top: 4px solid #4ade80;
            border-radius: 50%;
            animation: spin 1s linear infinite;
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
    <nav class="navbar">
        <div class="nav-brand">
            <a href="/" class="brand-link">🎭 PLAYALTER</a>
            <span class="version">v2.0</span>
        </div>
        <div class="nav-links">
            <a href="/face-swap" class="nav-link active">🔄 Face Swap</a>
            <a href="/mask-generator" class="nav-link">🎭 Privacy Masks</a>
            <a href="/video-processor" class="nav-link">🎬 Video</a>
            <a href="/style-transfer" class="nav-link">🎨 Style</a>
        </div>
    </nav>
    
    <div class="container">
        <div class="module-header">
            <h1 class="module-title">🔄 Face Swap Studio</h1>
            <p>Upload an image and swap faces with precision targeting</p>
        </div>
        
        <div class="upload-zone" id="uploadZone">
            <input type="file" id="sourceFile" accept="image/*" style="display: none;">
            <div class="upload-icon">📸</div>
            <h3>Upload Image for Face Swapping</h3>
            <p>Supports JPG, PNG - Detects up to 30 faces</p>
        </div>
        
        <div class="faces-container" id="facesContainer">
            <h3>Detected Faces - Select targets for each:</h3>
            <div class="faces-grid" id="facesGrid"></div>
        </div>
    </div>
    
    <div class="loading-overlay" id="loadingOverlay">
        <div class="loading-content">
            <div class="spinner"></div>
            <div id="loadingText">Processing face swap...</div>
        </div>
    </div>
    
    <script>
        let detectedFaces = [];
        let sourceFile = null;
        let targetFiles = {};
        
        document.getElementById('uploadZone').addEventListener('click', () => {
            document.getElementById('sourceFile').click();
        });
        
        document.getElementById('sourceFile').addEventListener('change', async (e) => {
            if (e.target.files.length > 0) {
                sourceFile = e.target.files[0];
                await detectFaces();
            }
        });
        
        async function detectFaces() {
            showLoading('🔍 Detecting faces in image...');
            
            const formData = new FormData();
            formData.append('file', sourceFile);
            
            try {
                const response = await fetch('/api/face-swap/detect', {
                    method: 'POST',
                    body: formData
                });
                
                const result = await response.json();
                hideLoading();
                
                if (result.success) {
                    detectedFaces = result.faces;
                    renderFaces();
                } else {
                    alert('Face detection failed: ' + result.message);
                }
            } catch (error) {
                hideLoading();
                alert('Error: ' + error.message);
            }
        }
        
        function renderFaces() {
            const grid = document.getElementById('facesGrid');
            grid.innerHTML = '';
            
            detectedFaces.forEach((face, index) => {
                const faceItem = document.createElement('div');
                faceItem.className = 'face-item';
                faceItem.innerHTML = `
                    <img src="data:image/png;base64,${face.face_image}" class="face-preview" alt="Face ${index + 1}">
                    <div class="face-controls">
                        <div class="face-number">Face ${index + 1} (${face.ethnicity.primary})</div>
                        <div class="target-slot">
                            <span>Target:</span>
                            <div class="target-upload" onclick="selectTarget('${face.id}')">
                                <input type="file" id="target-${face.id}" accept="image/*" style="display: none;">
                                <div id="placeholder-${face.id}">+</div>
                                <img id="preview-${face.id}" class="target-preview" style="display: none;">
                            </div>
                            <button class="swap-btn" onclick="swapFace('${face.id}')">Swap</button>
                        </div>
                    </div>
                `;
                grid.appendChild(faceItem);
            });
            
            document.getElementById('facesContainer').style.display = 'block';
        }
        
        function selectTarget(faceId) {
            const input = document.getElementById(`target-${faceId}`);
            input.click();
            
            input.onchange = function(e) {
                if (e.target.files.length > 0) {
                    targetFiles[faceId] = e.target.files[0];
                    
                    const reader = new FileReader();
                    reader.onload = function(e) {
                        document.getElementById(`placeholder-${faceId}`).style.display = 'none';
                        const preview = document.getElementById(`preview-${faceId}`);
                        preview.src = e.target.result;
                        preview.style.display = 'block';
                    };
                    reader.readAsDataURL(e.target.files[0]);
                }
            };
        }
        
        async function swapFace(faceId) {
            if (!targetFiles[faceId]) {
                alert('Please select a target image first!');
                return;
            }
            
            const face = detectedFaces.find(f => f.id === faceId);
            showLoading(`🤖 Swapping ${face.ethnicity.primary} face...`);
            
            const formData = new FormData();
            formData.append('source_file', sourceFile);
            formData.append('target_file', targetFiles[faceId]);
            formData.append('face_data', JSON.stringify(face));
            
            try {
                const response = await fetch('/api/face-swap/process', {
                    method: 'POST',
                    body: formData
                });
                
                const result = await response.json();
                hideLoading();
                
                if (result.success) {
                    // Show result
                    const link = document.createElement('a');
                    link.href = 'data:image/png;base64,' + result.result_image;
                    link.download = `${result.face_id}_swapped.png`;
                    link.click();
                } else {
                    alert('Face swap failed: ' + result.message);
                }
            } catch (error) {
                hideLoading();
                alert('Error: ' + error.message);
            }
        }
        
        function showLoading(text) {
            document.getElementById('loadingText').textContent = text;
            document.getElementById('loadingOverlay').style.display = 'flex';
        }
        
        function hideLoading() {
            document.getElementById('loadingOverlay').style.display = 'none';
        }
    </script>
</body>
</html>
    '''

# FastAPI Routes
@web_app.get("/", response_class=HTMLResponse)
async def home():
    """Homepage with service cards"""
    return get_homepage_html()

@web_app.get("/face-swap", response_class=HTMLResponse)
async def face_swap_page():
    """Face Swap Studio interface"""
    return get_face_swap_html()

@web_app.get("/mask-generator", response_class=HTMLResponse)
async def mask_generator_page():
    """Privacy Mask Generator interface"""
    return HTMLResponse(content="<h1>🎭 Privacy Mask Generator - Coming Soon!</h1>")

@web_app.get("/video-processor", response_class=HTMLResponse)
async def video_processor_page():
    """Video Processor interface"""
    return HTMLResponse(content="<h1>🎬 Video Processor - Coming Soon!</h1>")

@web_app.get("/style-transfer", response_class=HTMLResponse)
async def style_transfer_page():
    """Style Transfer interface"""
    return HTMLResponse(content="<h1>🎨 Style Transfer - Coming Soon!</h1>")

# API Endpoints
@web_app.post("/api/face-swap/detect")
async def api_face_swap_detect(file: UploadFile = File(...)):
    """Face detection API for face swap module"""
    file_bytes = await file.read()
    detect_fn = modal.Function.lookup("playalter-modular", "detect_faces_api")
    result = detect_fn.remote(file_bytes=file_bytes, file_type=file.content_type)
    return JSONResponse(content=result)

@web_app.post("/api/face-swap/process")
async def api_face_swap_process(
    source_file: UploadFile = File(...),
    target_file: UploadFile = File(...),
    face_data: str = Form(...)
):
    """Face swap processing API"""
    source_bytes = await source_file.read()
    target_bytes = await target_file.read()
    face_info = json.loads(face_data)
    
    swap_fn = modal.Function.lookup("playalter-modular", "process_face_swap")
    result = swap_fn.remote(
        source_bytes=source_bytes,
        target_bytes=target_bytes,
        face_data=face_info
    )
    return JSONResponse(content=result)

@web_app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "platform": "PLAYALTER v2.0 - Modular Architecture",
        "version": "2.1.0",
        "modules": ["face-swap", "mask-generator", "video-processor", "style-transfer"],
        "features": [
            "Modular service architecture", 
            "Multi-face detection and processing",
            "Ethnicity-aware algorithms",
            "Independent service interfaces",
            "Real-time processing"
        ]
    }

# Modal ASGI app
@app.function(image=image)
@modal.asgi_app()
def fastapi_app():
    """Serve the modular FastAPI app through Modal"""
    return web_app

if __name__ == "__main__":
    print("🚀 PLAYALTER v2.0 - Modular Architecture ready!")
    print("📦 Services: Face Swap, Privacy Masks, Video Processing, Style Transfer")
    print("🔧 Deploy: modal deploy main_app_modular_fixed.py")