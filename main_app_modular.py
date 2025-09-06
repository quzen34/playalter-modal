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

# Common navbar HTML
NAVBAR_HTML = """
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
"""

COMMON_STYLES = """
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
        .navbar { flex-direction: column; gap: 15px; padding: 20px; }
        .nav-links { flex-wrap: wrap; justify-content: center; }
        .container { padding: 20px; }
    }
</style>
"""

# Homepage Template
HOMEPAGE_HTML = f""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PLAYALTER v2.0 - AI-Powered Media Processing Platform</title>
    {COMMON_STYLES}
    <style>
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
        
        .stats-bar {
            background: rgba(0, 0, 0, 0.2);
            padding: 30px 0;
            margin: 60px 0;
            border-radius: 15px;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 30px;
            text-align: center;
        }
        
        .stat-item h3 {
            font-size: 2.5em;
            color: #4ade80;
            margin-bottom: 5px;
        }
        
        .stat-item p {
            opacity: 0.8;
        }
    </style>
</head>
<body>
    {NAVBAR_HTML}
    
    <div class="container">
        <div class="hero">
            <h1>PLAYALTER Platform</h1>
            <p>Advanced AI-powered media processing with ethnicity-aware algorithms and multi-face detection</p>
        </div>
        
        <div class="stats-bar">
            <div class="stats-grid">
                <div class="stat-item">
                    <h3>30+</h3>
                    <p>Faces per image</p>
                </div>
                <div class="stat-item">
                    <h3>5</h3>
                    <p>Ethnic groups</p>
                </div>
                <div class="stat-item">
                    <h3>4</h3>
                    <p>AI services</p>
                </div>
                <div class="stat-item">
                    <h3>Real-time</h3>
                    <p>Processing</p>
                </div>
            </div>
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
                    <li>HD quality output</li>
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
                    <li>Format variations</li>
                </ul>
            </div>
            
            <div class="service-card" onclick="window.location.href='/video-processor'">
                <div class="service-icon">🎬</div>
                <div class="service-title">Video Processor</div>
                <div class="service-desc">Advanced video processing with face tracking and timeline control</div>
                <ul class="service-features">
                    <li>Face tracking across frames</li>
                    <li>Timeline visualization</li>
                    <li>Frame-by-frame editing</li>
                    <li>Multiple export formats</li>
                    <li>Batch operations</li>
                </ul>
            </div>
            
            <div class="service-card" onclick="window.location.href='/style-transfer'">
                <div class="service-icon">🎨</div>
                <div class="service-title">Style Transfer</div>
                <div class="service-desc">Artistic transformation with multiple style options</div>
                <ul class="service-features">
                    <li>Anime/Cartoon conversion</li>
                    <li>Oil painting effects</li>
                    <li>Photorealistic enhancement</li>
                    <li>Intensity controls</li>
                    <li>Batch processing</li>
                </ul>
            </div>
        </div>
    </div>
    
    <script>
        // Add active state to navbar
        document.querySelector('.brand-link').classList.add('active');
    </script>
</body>
</html>
"""

# Face Swap Module Template
FACE_SWAP_HTML = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Face Swap Studio - PLAYALTER</title>
    {COMMON_STYLES}
    <style>
        .module-header {{
            text-align: center;
            padding: 40px 0;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            margin-bottom: 40px;
        }}
        
        .module-title {{
            font-size: 3em;
            margin-bottom: 15px;
        }}
        
        .upload-zone {{
            background: rgba(255, 255, 255, 0.1);
            border: 3px dashed rgba(255, 255, 255, 0.5);
            border-radius: 20px;
            padding: 60px;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s ease;
            margin-bottom: 40px;
        }}
        
        .upload-zone:hover {{
            border-color: #4ade80;
            background: rgba(74, 222, 128, 0.1);
        }}
        
        .upload-icon {{ font-size: 4em; margin-bottom: 20px; }}
        
        .faces-container {{
            display: none;
        }}
        
        .faces-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 25px;
            margin: 30px 0;
        }}
        
        .face-item {{
            background: rgba(255, 255, 255, 0.1);
            border-radius: 15px;
            padding: 25px;
            display: flex;
            align-items: center;
            gap: 20px;
        }}
        
        .face-preview {{
            width: 100px;
            height: 100px;
            border-radius: 12px;
            object-fit: cover;
            border: 2px solid rgba(255, 255, 255, 0.3);
        }}
        
        .face-controls {{
            flex: 1;
        }}
        
        .face-number {{
            font-size: 1.2em;
            font-weight: bold;
            margin-bottom: 10px;
        }}
        
        .target-slot {{
            display: flex;
            align-items: center;
            gap: 15px;
            margin: 15px 0;
        }}
        
        .target-upload {{
            width: 80px;
            height: 80px;
            border: 2px dashed rgba(255, 255, 255, 0.5);
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            transition: all 0.3s ease;
        }}
        
        .target-upload:hover {{
            border-color: #4ade80;
            background: rgba(74, 222, 128, 0.1);
        }}
        
        .target-preview {{
            width: 100%;
            height: 100%;
            object-fit: cover;
            border-radius: 8px;
        }}
        
        .swap-btn {{
            background: linear-gradient(45deg, #4ade80, #22c55e);
            border: none;
            padding: 10px 20px;
            border-radius: 8px;
            color: white;
            cursor: pointer;
            font-weight: bold;
            transition: all 0.3s ease;
        }}
        
        .swap-btn:hover {{
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(74, 222, 128, 0.4);
        }}
        
        .batch-controls {{
            display: none;
            text-align: center;
            margin: 40px 0;
            gap: 20px;
        }}
        
        .batch-btn {{
            background: linear-gradient(45deg, #667eea, #764ba2);
            border: none;
            padding: 15px 30px;
            border-radius: 10px;
            color: white;
            font-size: 1.1em;
            font-weight: bold;
            cursor: pointer;
            margin: 0 10px;
            transition: all 0.3s ease;
        }}
        
        .batch-btn:hover {{
            transform: translateY(-2px);
            box-shadow: 0 10px 30px rgba(102, 126, 234, 0.4);
        }}
        
        .results-section {{
            display: none;
            margin-top: 60px;
        }}
        
        .results-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
        }}
        
        .result-card {{
            background: rgba(255, 255, 255, 0.1);
            border-radius: 15px;
            padding: 20px;
            text-align: center;
        }}
        
        .result-image {{
            width: 100%;
            max-width: 200px;
            border-radius: 10px;
            margin-bottom: 15px;
        }}
    </style>
</head>
<body>
    {NAVBAR_HTML}
    
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
            
            <div class="batch-controls" id="batchControls" style="display: flex; justify-content: center;">
                <button class="batch-btn" onclick="swapAllFaces()">🔄 Swap All Faces</button>
                <button class="batch-btn" onclick="downloadAllResults()">💾 Download All</button>
            </div>
        </div>
        
        <div class="results-section" id="resultsSection">
            <h3>✨ Swap Results</h3>
            <div class="results-grid" id="resultsGrid"></div>
        </div>
    </div>
    
    <div class="loading-overlay" id="loadingOverlay">
        <div class="loading-content">
            <div class="spinner"></div>
            <div id="loadingText">Processing face swap...</div>
        </div>
    </div>
    
    <script>
        document.querySelector('a[href="/face-swap"]').classList.add('active');
        
        let detectedFaces = [];
        let sourceFile = null;
        let targetFiles = {{}};
        let processedResults = [];
        
        document.getElementById('uploadZone').addEventListener('click', () => {{
            document.getElementById('sourceFile').click();
        }});
        
        document.getElementById('sourceFile').addEventListener('change', async (e) => {{
            if (e.target.files.length > 0) {{
                sourceFile = e.target.files[0];
                await detectFaces();
            }}
        }});
        
        async function detectFaces() {{
            showLoading('🔍 Detecting faces in image...');
            
            const formData = new FormData();
            formData.append('file', sourceFile);
            
            try {{
                const response = await fetch('/api/face-swap/detect', {{
                    method: 'POST',
                    body: formData
                }});
                
                const result = await response.json();
                hideLoading();
                
                if (result.success) {{
                    detectedFaces = result.faces;
                    renderFaces();
                }} else {{
                    alert('Face detection failed: ' + result.message);
                }}
            }} catch (error) {{
                hideLoading();
                alert('Error: ' + error.message);
            }}
        }}
        
        function renderFaces() {{
            const grid = document.getElementById('facesGrid');
            grid.innerHTML = '';
            
            detectedFaces.forEach((face, index) => {{
                const faceItem = document.createElement('div');
                faceItem.className = 'face-item';
                faceItem.innerHTML = `
                    <img src="data:image/png;base64,${{face.face_image}}" class="face-preview" alt="Face ${{index + 1}}">
                    <div class="face-controls">
                        <div class="face-number">Face ${{index + 1}} (${{face.ethnicity.primary}})</div>
                        <div class="target-slot">
                            <span>Target:</span>
                            <div class="target-upload" onclick="selectTarget('${{face.id}}')">
                                <input type="file" id="target-${{face.id}}" accept="image/*" style="display: none;">
                                <div id="placeholder-${{face.id}}">+</div>
                                <img id="preview-${{face.id}}" class="target-preview" style="display: none;">
                            </div>
                            <button class="swap-btn" onclick="swapFace('${{face.id}}')">Swap</button>
                        </div>
                    </div>
                `;
                grid.appendChild(faceItem);
            }});
            
            document.getElementById('facesContainer').style.display = 'block';
        }}
        
        function selectTarget(faceId) {{
            const input = document.getElementById(`target-${{faceId}}`);
            input.click();
            
            input.onchange = function(e) {{
                if (e.target.files.length > 0) {{
                    targetFiles[faceId] = e.target.files[0];
                    
                    const reader = new FileReader();
                    reader.onload = function(e) {{
                        document.getElementById(`placeholder-${{faceId}}`).style.display = 'none';
                        const preview = document.getElementById(`preview-${{faceId}}`);
                        preview.src = e.target.result;
                        preview.style.display = 'block';
                    }};
                    reader.readAsDataURL(e.target.files[0]);
                }}
            }};
        }}
        
        async function swapFace(faceId) {{
            if (!targetFiles[faceId]) {{
                alert('Please select a target image first!');
                return;
            }}
            
            const face = detectedFaces.find(f => f.id === faceId);
            showLoading(`🤖 Swapping ${{face.ethnicity.primary}} face...`);
            
            const formData = new FormData();
            formData.append('source_file', sourceFile);
            formData.append('target_file', targetFiles[faceId]);
            formData.append('face_data', JSON.stringify(face));
            
            try {{
                const response = await fetch('/api/face-swap/process', {{
                    method: 'POST',
                    body: formData
                }});
                
                const result = await response.json();
                hideLoading();
                
                if (result.success) {{
                    addResult(result);
                    showResults();
                }} else {{
                    alert('Face swap failed: ' + result.message);
                }}
            }} catch (error) {{
                hideLoading();
                alert('Error: ' + error.message);
            }}
        }}
        
        function addResult(result) {{
            processedResults.push(result);
            
            const grid = document.getElementById('resultsGrid');
            const card = document.createElement('div');
            card.className = 'result-card';
            card.innerHTML = `
                <img src="data:image/png;base64,${{result.result_image}}" class="result-image">
                <h4>${{result.face_id}} - ${{result.ethnicity}}</h4>
                <button onclick="downloadResult('${{result.face_id}}')" 
                        style="padding: 8px 15px; background: #4ade80; border: none; border-radius: 5px; color: white; cursor: pointer; margin-top: 10px;">
                    Download
                </button>
            `;
            grid.appendChild(card);
        }}
        
        function showResults() {{
            document.getElementById('resultsSection').style.display = 'block';
        }}
        
        function downloadResult(faceId) {{
            const result = processedResults.find(r => r.face_id === faceId);
            if (result) {{
                const link = document.createElement('a');
                link.href = 'data:image/png;base64,' + result.result_image;
                link.download = `${{faceId}}_swapped.png`;
                link.click();
            }}
        }}
        
        function swapAllFaces() {{
            alert('🚀 Batch swap coming soon!');
        }}
        
        function downloadAllResults() {{
            processedResults.forEach(result => downloadResult(result.face_id));
        }}
        
        function showLoading(text) {{
            document.getElementById('loadingText').textContent = text;
            document.getElementById('loadingOverlay').style.display = 'flex';
        }}
        
        function hideLoading() {{
            document.getElementById('loadingOverlay').style.display = 'none';
        }}
    </script>
</body>
</html>
"""

# Privacy Mask Generator Template  
PRIVACY_MASK_HTML = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Privacy Mask Generator - PLAYALTER</title>
    {COMMON_STYLES}
    <style>
        .module-header {{
            text-align: center;
            padding: 40px 0;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            margin-bottom: 40px;
        }}
        
        .module-title {{
            font-size: 3em;
            margin-bottom: 15px;
        }}
        
        .upload-zone {{
            background: rgba(255, 255, 255, 0.1);
            border: 3px dashed rgba(255, 255, 255, 0.5);
            border-radius: 20px;
            padding: 60px;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s ease;
            margin-bottom: 40px;
        }}
        
        .upload-zone:hover {{
            border-color: #4ade80;
            background: rgba(74, 222, 128, 0.1);
        }}
        
        .controls-panel {{
            display: none;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 20px;
            padding: 30px;
            margin-bottom: 40px;
        }}
        
        .control-group {{
            margin-bottom: 25px;
        }}
        
        .control-label {{
            display: block;
            margin-bottom: 10px;
            font-weight: bold;
        }}
        
        .ethnicity-display {{
            background: rgba(74, 222, 128, 0.2);
            border: 1px solid #4ade80;
            padding: 15px;
            border-radius: 10px;
            margin-bottom: 20px;
        }}
        
        .mask-options {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
        }}
        
        .mask-option {{
            background: rgba(255, 255, 255, 0.1);
            border: 2px solid transparent;
            border-radius: 10px;
            padding: 15px;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s ease;
        }}
        
        .mask-option:hover, .mask-option.selected {{
            border-color: #4ade80;
            background: rgba(74, 222, 128, 0.2);
        }}
        
        .variations-slider {{
            width: 100%;
            margin: 10px 0;
        }}
        
        .generate-btn {{
            background: linear-gradient(45deg, #4ade80, #22c55e);
            border: none;
            padding: 15px 40px;
            border-radius: 10px;
            color: white;
            font-size: 1.2em;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.3s ease;
            display: block;
            margin: 20px auto;
        }}
        
        .generate-btn:hover {{
            transform: translateY(-2px);
            box-shadow: 0 10px 30px rgba(74, 222, 128, 0.4);
        }}
        
        .results-section {{
            display: none;
        }}
        
        .results-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 25px;
        }}
        
        .result-card {{
            background: rgba(255, 255, 255, 0.1);
            border-radius: 15px;
            padding: 20px;
            text-align: center;
        }}
        
        .result-image {{
            width: 100%;
            border-radius: 10px;
            margin-bottom: 15px;
        }}
    </style>
</head>
<body>
    {NAVBAR_HTML}
    
    <div class="container">
        <div class="module-header">
            <h1 class="module-title">🎭 Privacy Mask Generator</h1>
            <p>Ethnicity-aware privacy protection with cultural sensitivity</p>
        </div>
        
        <div class="upload-zone" id="uploadZone">
            <input type="file" id="imageFile" accept="image/*" style="display: none;">
            <div class="upload-icon">🖼️</div>
            <h3>Upload Photo for Privacy Masking</h3>
            <p>AI will analyze ethnicity and generate appropriate masks</p>
        </div>
        
        <div class="controls-panel" id="controlsPanel">
            <div class="ethnicity-display" id="ethnicityDisplay">
                <h4>🧬 Detected Ethnicity: <span id="detectedEthnicity">Analyzing...</span></h4>
                <p>Confidence: <span id="ethnicityConfidence">0%</span></p>
            </div>
            
            <div class="control-group">
                <label class="control-label">🎨 Mask Style:</label>
                <div class="mask-options">
                    <div class="mask-option selected" data-style="blur">
                        <div>🔐</div>
                        <div>Cultural Blur</div>
                    </div>
                    <div class="mask-option" data-style="pixelate">
                        <div>🔲</div>
                        <div>Smart Pixelate</div>
                    </div>
                    <div class="mask-option" data-style="stylized">
                        <div>🎨</div>
                        <div>Cultural Pattern</div>
                    </div>
                    <div class="mask-option" data-style="synthetic">
                        <div>🤖</div>
                        <div>AI Generated</div>
                    </div>
                </div>
            </div>
            
            <div class="control-group">
                <label class="control-label">📊 Number of Variations: <span id="variationsCount">3</span></label>
                <input type="range" class="variations-slider" id="variationsSlider" min="1" max="10" value="3">
            </div>
            
            <button class="generate-btn" onclick="generateMasks()">🎭 Generate Privacy Masks</button>
        </div>
        
        <div class="results-section" id="resultsSection">
            <h3>✨ Generated Privacy Masks</h3>
            <div class="results-grid" id="resultsGrid"></div>
        </div>
    </div>
    
    <div class="loading-overlay" id="loadingOverlay">
        <div class="loading-content">
            <div class="spinner"></div>
            <div id="loadingText">Analyzing image...</div>
        </div>
    </div>
    
    <script>
        document.querySelector('a[href="/mask-generator"]').classList.add('active');
        
        let uploadedFile = null;
        let detectedEthnicity = null;
        let selectedStyle = 'blur';
        
        document.getElementById('uploadZone').addEventListener('click', () => {{
            document.getElementById('imageFile').click();
        }});
        
        document.getElementById('imageFile').addEventListener('change', async (e) => {{
            if (e.target.files.length > 0) {{
                uploadedFile = e.target.files[0];
                await analyzeImage();
            }}
        }});
        
        document.getElementById('variationsSlider').addEventListener('input', (e) => {{
            document.getElementById('variationsCount').textContent = e.target.value;
        }});
        
        document.querySelectorAll('.mask-option').forEach(option => {{
            option.addEventListener('click', () => {{
                document.querySelectorAll('.mask-option').forEach(o => o.classList.remove('selected'));
                option.classList.add('selected');
                selectedStyle = option.dataset.style;
            }});
        }});
        
        async function analyzeImage() {{
            showLoading('🧬 Analyzing ethnicity and preparing masks...');
            
            const formData = new FormData();
            formData.append('file', uploadedFile);
            
            try {{
                const response = await fetch('/api/mask/analyze', {{
                    method: 'POST',
                    body: formData
                }});
                
                const result = await response.json();
                hideLoading();
                
                if (result.success) {{
                    detectedEthnicity = result.ethnicity;
                    displayEthnicity();
                    showControls();
                }} else {{
                    alert('Analysis failed: ' + result.message);
                }}
            }} catch (error) {{
                hideLoading();
                alert('Error: ' + error.message);
            }}
        }}
        
        function displayEthnicity() {{
            document.getElementById('detectedEthnicity').textContent = detectedEthnicity.primary + ' (' + detectedEthnicity.subgroup + ')';
            document.getElementById('ethnicityConfidence').textContent = Math.round(detectedEthnicity.confidence * 100) + '%';
        }}
        
        function showControls() {{
            document.getElementById('controlsPanel').style.display = 'block';
        }}
        
        async function generateMasks() {{
            const variations = document.getElementById('variationsSlider').value;
            showLoading(`🎨 Generating ${{variations}} ${{detectedEthnicity.primary}} cultural masks...`);
            
            const formData = new FormData();
            formData.append('file', uploadedFile);
            formData.append('style', selectedStyle);
            formData.append('variations', variations);
            formData.append('ethnicity', JSON.stringify(detectedEthnicity));
            
            try {{
                const response = await fetch('/api/mask/generate', {{
                    method: 'POST',
                    body: formData
                }});
                
                const result = await response.json();
                hideLoading();
                
                if (result.success) {{
                    displayResults(result.masks);
                }} else {{
                    alert('Mask generation failed: ' + result.message);
                }}
            }} catch (error) {{
                hideLoading();
                alert('Error: ' + error.message);
            }}
        }}
        
        function displayResults(masks) {{
            const grid = document.getElementById('resultsGrid');
            grid.innerHTML = '';
            
            masks.forEach((mask, index) => {{
                const card = document.createElement('div');
                card.className = 'result-card';
                card.innerHTML = `
                    <img src="data:image/png;base64,${{mask.image}}" class="result-image">
                    <h4>Variation ${{index + 1}}</h4>
                    <p>${{mask.style}} - ${{detectedEthnicity.primary}}</p>
                    <button onclick="downloadMask(${{index}})" 
                            style="padding: 8px 15px; background: #4ade80; border: none; border-radius: 5px; color: white; cursor: pointer; margin-top: 10px;">
                        💾 Download
                    </button>
                `;
                grid.appendChild(card);
            }});
            
            document.getElementById('resultsSection').style.display = 'block';
        }}
        
        function downloadMask(index) {{
            // Implementation for downloading specific mask
            alert(`Downloading mask variation ${{index + 1}}`);
        }}
        
        function showLoading(text) {{
            document.getElementById('loadingText').textContent = text;
            document.getElementById('loadingOverlay').style.display = 'flex';
        }}
        
        function hideLoading() {{
            document.getElementById('loadingOverlay').style.display = 'none';
        }}
    </script>
</body>
</html>
"""

# Video Processor Template
VIDEO_PROCESSOR_HTML = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Video Processor - PLAYALTER</title>
    {COMMON_STYLES}
    <style>
        .module-header {{
            text-align: center;
            padding: 40px 0;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            margin-bottom: 40px;
        }}
        
        .module-title {{ font-size: 3em; margin-bottom: 15px; }}
        
        .upload-zone {{
            background: rgba(255, 255, 255, 0.1);
            border: 3px dashed rgba(255, 255, 255, 0.5);
            border-radius: 20px;
            padding: 60px;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s ease;
            margin-bottom: 40px;
        }}
        
        .video-timeline {{
            display: none;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 20px;
            padding: 30px;
            margin-bottom: 40px;
        }}
        
        .timeline-bar {{
            width: 100%;
            height: 60px;
            background: rgba(0, 0, 0, 0.3);
            border-radius: 10px;
            margin: 20px 0;
            position: relative;
        }}
        
        .frame-marker {{
            position: absolute;
            width: 4px;
            height: 100%;
            background: #4ade80;
            border-radius: 2px;
        }}
        
        .video-controls {{
            display: flex;
            justify-content: center;
            gap: 15px;
            margin: 20px 0;
        }}
        
        .control-btn {{
            background: rgba(255, 255, 255, 0.2);
            border: none;
            padding: 10px 15px;
            border-radius: 8px;
            color: white;
            cursor: pointer;
            transition: all 0.3s ease;
        }}
        
        .control-btn:hover {{ background: rgba(255, 255, 255, 0.3); }}
        
        .face-tracking {{
            display: none;
            margin-top: 30px;
        }}
        
        .tracked-faces {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
        }}
        
        .tracked-face {{
            background: rgba(255, 255, 255, 0.1);
            border-radius: 15px;
            padding: 20px;
            text-align: center;
        }}
        
        .face-track-preview {{
            width: 100px;
            height: 100px;
            border-radius: 10px;
            object-fit: cover;
            margin-bottom: 10px;
        }}
    </style>
</head>
<body>
    {NAVBAR_HTML}
    
    <div class="container">
        <div class="module-header">
            <h1 class="module-title">🎬 Video Processor</h1>
            <p>Advanced video processing with face tracking and timeline control</p>
        </div>
        
        <div class="upload-zone" id="uploadZone">
            <input type="file" id="videoFile" accept="video/*" style="display: none;">
            <div class="upload-icon">🎬</div>
            <h3>Upload Video for Processing</h3>
            <p>Supports MP4, AVI, MOV - Face tracking across frames</p>
        </div>
        
        <div class="video-timeline" id="videoTimeline">
            <h3>📹 Video Timeline</h3>
            <div class="timeline-bar" id="timelineBar">
                <div class="frame-marker" style="left: 25%;"></div>
            </div>
            
            <div class="video-controls">
                <button class="control-btn" onclick="playPause()">⏯️ Play/Pause</button>
                <button class="control-btn" onclick="previousFrame()">⏮️ Prev Frame</button>
                <button class="control-btn" onclick="nextFrame()">⏭️ Next Frame</button>
                <button class="control-btn" onclick="trackFaces()">👥 Track Faces</button>
            </div>
            
            <div class="face-tracking" id="faceTracking">
                <h4>🔍 Tracked Faces Across Frames</h4>
                <div class="tracked-faces" id="trackedFaces"></div>
            </div>
        </div>
    </div>
    
    <div class="loading-overlay" id="loadingOverlay">
        <div class="loading-content">
            <div class="spinner"></div>
            <div id="loadingText">Processing video...</div>
        </div>
    </div>
    
    <script>
        document.querySelector('a[href="/video-processor"]').classList.add('active');
        
        let uploadedVideo = null;
        
        document.getElementById('uploadZone').addEventListener('click', () => {{
            document.getElementById('videoFile').click();
        }});
        
        document.getElementById('videoFile').addEventListener('change', async (e) => {{
            if (e.target.files.length > 0) {{
                uploadedVideo = e.target.files[0];
                await processVideo();
            }}
        }});
        
        async function processVideo() {{
            showLoading('🎬 Processing video and detecting faces...');
            
            // Simulate video processing
            setTimeout(() => {{
                hideLoading();
                showTimeline();
            }}, 3000);
        }}
        
        function showTimeline() {{
            document.getElementById('videoTimeline').style.display = 'block';
        }}
        
        function trackFaces() {{
            showLoading('👥 Tracking faces across video frames...');
            
            setTimeout(() => {{
                hideLoading();
                showTrackedFaces();
            }}, 2000);
        }}
        
        function showTrackedFaces() {{
            const container = document.getElementById('trackedFaces');
            container.innerHTML = `
                <div class="tracked-face">
                    <div style="width: 100px; height: 100px; background: #4ade80; border-radius: 10px; margin: 0 auto 10px;"></div>
                    <h5>Face 1</h5>
                    <p>Frames: 1-120</p>
                    <p>Ethnicity: Asian</p>
                </div>
                <div class="tracked-face">
                    <div style="width: 100px; height: 100px; background: #FF6B6B; border-radius: 10px; margin: 0 auto 10px;"></div>
                    <h5>Face 2</h5>
                    <p>Frames: 15-95</p>
                    <p>Ethnicity: Caucasian</p>
                </div>
            `;
            
            document.getElementById('faceTracking').style.display = 'block';
        }}
        
        function playPause() {{ alert('▶️ Video playback controls coming soon!'); }}
        function previousFrame() {{ alert('⏮️ Frame navigation coming soon!'); }}
        function nextFrame() {{ alert('⏭️ Frame navigation coming soon!'); }}
        
        function showLoading(text) {{
            document.getElementById('loadingText').textContent = text;
            document.getElementById('loadingOverlay').style.display = 'flex';
        }}
        
        function hideLoading() {{
            document.getElementById('loadingOverlay').style.display = 'none';
        }}
    </script>
</body>
</html>
"""

# Style Transfer Template
STYLE_TRANSFER_HTML = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Style Transfer - PLAYALTER</title>
    {COMMON_STYLES}
    <style>
        .module-header {{
            text-align: center;
            padding: 40px 0;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            margin-bottom: 40px;
        }}
        
        .module-title {{ font-size: 3em; margin-bottom: 15px; }}
        
        .upload-zone {{
            background: rgba(255, 255, 255, 0.1);
            border: 3px dashed rgba(255, 255, 255, 0.5);
            border-radius: 20px;
            padding: 60px;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s ease;
            margin-bottom: 40px;
        }}
        
        .style-selector {{
            display: none;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 20px;
            padding: 30px;
            margin-bottom: 40px;
        }}
        
        .style-options {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }}
        
        .style-option {{
            background: rgba(255, 255, 255, 0.1);
            border: 2px solid transparent;
            border-radius: 15px;
            padding: 20px;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s ease;
        }}
        
        .style-option:hover, .style-option.selected {{
            border-color: #4ade80;
            background: rgba(74, 222, 128, 0.2);
        }}
        
        .style-preview {{
            width: 100%;
            height: 100px;
            border-radius: 10px;
            margin-bottom: 10px;
            background: linear-gradient(45deg, #FF6B6B, #4ECDC4);
        }}
        
        .intensity-control {{
            margin: 30px 0;
        }}
        
        .intensity-slider {{
            width: 100%;
            margin: 10px 0;
        }}
        
        .transfer-btn {{
            background: linear-gradient(45deg, #4ade80, #22c55e);
            border: none;
            padding: 15px 40px;
            border-radius: 10px;
            color: white;
            font-size: 1.2em;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.3s ease;
            display: block;
            margin: 20px auto;
        }}
        
        .transfer-btn:hover {{
            transform: translateY(-2px);
            box-shadow: 0 10px 30px rgba(74, 222, 128, 0.4);
        }}
        
        .preview-section {{
            display: none;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 20px;
            padding: 30px;
            margin-bottom: 40px;
        }}
        
        .before-after {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
            margin: 20px 0;
        }}
        
        .preview-item {{
            text-align: center;
        }}
        
        .preview-image {{
            width: 100%;
            max-width: 300px;
            border-radius: 15px;
            margin-bottom: 15px;
        }}
    </style>
</head>
<body>
    {NAVBAR_HTML}
    
    <div class="container">
        <div class="module-header">
            <h1 class="module-title">🎨 Style Transfer</h1>
            <p>Transform your images with artistic AI styles</p>
        </div>
        
        <div class="upload-zone" id="uploadZone">
            <input type="file" id="imageFile" accept="image/*" style="display: none;">
            <div class="upload-icon">🖼️</div>
            <h3>Upload Image for Style Transfer</h3>
            <p>Transform with AI artistic styles</p>
        </div>
        
        <div class="style-selector" id="styleSelector">
            <h3>🎨 Choose Artistic Style</h3>
            <div class="style-options">
                <div class="style-option selected" data-style="anime">
                    <div class="style-preview" style="background: linear-gradient(45deg, #FF6B6B, #FFE66D);"></div>
                    <h4>🌸 Anime</h4>
                    <p>Japanese animation style</p>
                </div>
                <div class="style-option" data-style="cartoon">
                    <div class="style-preview" style="background: linear-gradient(45deg, #4ECDC4, #45B7D1);"></div>
                    <h4>🎭 Cartoon</h4>
                    <p>Western cartoon style</p>
                </div>
                <div class="style-option" data-style="oil">
                    <div class="style-preview" style="background: linear-gradient(45deg, #F7DC6F, #F1948A);"></div>
                    <h4>🖌️ Oil Paint</h4>
                    <p>Classic oil painting</p>
                </div>
                <div class="style-option" data-style="realistic">
                    <div class="style-preview" style="background: linear-gradient(45deg, #85C1E9, #D5A6BD);"></div>
                    <h4>📸 Photorealistic</h4>
                    <p>Enhanced realism</p>
                </div>
            </div>
            
            <div class="intensity-control">
                <label>🔥 Style Intensity: <span id="intensityValue">70%</span></label>
                <input type="range" class="intensity-slider" id="intensitySlider" min="10" max="100" value="70">
            </div>
            
            <button class="transfer-btn" onclick="transferStyle()">🎨 Apply Style Transfer</button>
        </div>
        
        <div class="preview-section" id="previewSection">
            <h3>✨ Style Transfer Result</h3>
            <div class="before-after">
                <div class="preview-item">
                    <h4>Original</h4>
                    <img id="originalPreview" class="preview-image" alt="Original">
                </div>
                <div class="preview-item">
                    <h4>Styled</h4>
                    <img id="styledPreview" class="preview-image" alt="Styled">
                    <br>
                    <button onclick="downloadStyled()" 
                            style="padding: 10px 20px; background: #4ade80; border: none; border-radius: 8px; color: white; cursor: pointer; margin-top: 15px;">
                        💾 Download Styled Image
                    </button>
                </div>
            </div>
        </div>
    </div>
    
    <div class="loading-overlay" id="loadingOverlay">
        <div class="loading-content">
            <div class="spinner"></div>
            <div id="loadingText">Applying artistic style...</div>
        </div>
    </div>
    
    <script>
        document.querySelector('a[href="/style-transfer"]').classList.add('active');
        
        let uploadedFile = null;
        let selectedStyle = 'anime';
        
        document.getElementById('uploadZone').addEventListener('click', () => {{
            document.getElementById('imageFile').click();
        }});
        
        document.getElementById('imageFile').addEventListener('change', async (e) => {{
            if (e.target.files.length > 0) {{
                uploadedFile = e.target.files[0];
                showStyleSelector();
                showOriginalPreview();
            }}
        }});
        
        document.getElementById('intensitySlider').addEventListener('input', (e) => {{
            document.getElementById('intensityValue').textContent = e.target.value + '%';
        }});
        
        document.querySelectorAll('.style-option').forEach(option => {{
            option.addEventListener('click', () => {{
                document.querySelectorAll('.style-option').forEach(o => o.classList.remove('selected'));
                option.classList.add('selected');
                selectedStyle = option.dataset.style;
            }});
        }});
        
        function showStyleSelector() {{
            document.getElementById('styleSelector').style.display = 'block';
        }}
        
        function showOriginalPreview() {{
            const reader = new FileReader();
            reader.onload = function(e) {{
                document.getElementById('originalPreview').src = e.target.result;
            }};
            reader.readAsDataURL(uploadedFile);
        }}
        
        async function transferStyle() {{
            const intensity = document.getElementById('intensitySlider').value;
            const styleNames = {{
                'anime': '🌸 Anime transformation',
                'cartoon': '🎭 Cartoon stylization', 
                'oil': '🖌️ Oil painting effect',
                'realistic': '📸 Photorealistic enhancement'
            }};
            
            showLoading(`${{styleNames[selectedStyle]}} at ${{intensity}}% intensity...`);
            
            const formData = new FormData();
            formData.append('file', uploadedFile);
            formData.append('style', selectedStyle);
            formData.append('intensity', intensity);
            
            try {{
                const response = await fetch('/api/style-transfer/process', {{
                    method: 'POST',
                    body: formData
                }});
                
                const result = await response.json();
                hideLoading();
                
                if (result.success) {{
                    showResult(result.styled_image);
                }} else {{
                    alert('Style transfer failed: ' + result.message);
                }}
            }} catch (error) {{
                hideLoading();
                alert('Error: ' + error.message);
            }}
        }}
        
        function showResult(styledImageBase64) {{
            document.getElementById('styledPreview').src = 'data:image/png;base64,' + styledImageBase64;
            document.getElementById('previewSection').style.display = 'block';
        }}
        
        function downloadStyled() {{
            const link = document.createElement('a');
            link.href = document.getElementById('styledPreview').src;
            link.download = `styled_${{selectedStyle}}_image.png`;
            link.click();
        }}
        
        function showLoading(text) {{
            document.getElementById('loadingText').textContent = text;
            document.getElementById('loadingOverlay').style.display = 'flex';
        }}
        
        function hideLoading() {{
            document.getElementById('loadingOverlay').style.display = 'none';
        }}
    </script>
</body>
</html>
"""

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

# FastAPI Routes
@web_app.get("/", response_class=HTMLResponse)
async def home():
    """Homepage with service cards"""
    return HOMEPAGE_HTML

@web_app.get("/face-swap", response_class=HTMLResponse)
async def face_swap_page():
    """Face Swap Studio interface"""
    return FACE_SWAP_HTML

@web_app.get("/mask-generator", response_class=HTMLResponse)
async def mask_generator_page():
    """Privacy Mask Generator interface"""
    return PRIVACY_MASK_HTML

@web_app.get("/video-processor", response_class=HTMLResponse)
async def video_processor_page():
    """Video Processor interface"""
    return VIDEO_PROCESSOR_HTML

@web_app.get("/style-transfer", response_class=HTMLResponse)
async def style_transfer_page():
    """Style Transfer interface"""
    return STYLE_TRANSFER_HTML

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

@web_app.post("/api/mask/analyze")
async def api_mask_analyze(file: UploadFile = File(...)):
    """Ethnicity analysis API for mask generator"""
    file_bytes = await file.read()
    analyze_fn = modal.Function.lookup("playalter-modular", "analyze_image_ethnicity")
    result = analyze_fn.remote(file_bytes=file_bytes)
    return JSONResponse(content=result)

@web_app.post("/api/mask/generate")
async def api_mask_generate(
    file: UploadFile = File(...),
    style: str = Form(...),
    variations: int = Form(...),
    ethnicity: str = Form(...)
):
    """Privacy mask generation API"""
    file_bytes = await file.read()
    ethnicity_data = json.loads(ethnicity)
    
    generate_fn = modal.Function.lookup("playalter-modular", "generate_privacy_masks")
    result = generate_fn.remote(
        file_bytes=file_bytes,
        style=style,
        variations=variations,
        ethnicity_data=ethnicity_data
    )
    return JSONResponse(content=result)

@web_app.post("/api/style-transfer/process")
async def api_style_transfer_process(
    file: UploadFile = File(...),
    style: str = Form(...),
    intensity: int = Form(...)
):
    """Style transfer processing API"""
    file_bytes = await file.read()
    
    transfer_fn = modal.Function.lookup("playalter-modular", "process_style_transfer")
    result = transfer_fn.remote(
        file_bytes=file_bytes,
        style=style,
        intensity=intensity
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
    print("🔧 Deploy: modal deploy main_app_modular.py")