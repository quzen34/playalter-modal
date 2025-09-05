# 🔥 PLAYALTER Platform

**Advanced AI Face Processing Platform with FLAME Model & Privacy Protection**

PLAYALTER is a comprehensive face processing platform that provides state-of-the-art AI-powered services including face analysis using the FLAME 3D model, adaptive privacy mask generation, and high-quality face swapping using InSwapper technology.

## ✨ Features

### 🔍 Face Analysis with FLAME Model
- **Precise 3D Face Modeling**: Uses the FLAME (Faces Learned with an Articulated Model and Expressions) model for accurate face measurement extraction
- **Detailed Measurements**: Extract 15+ facial measurements including face width, height, eye distance, nose dimensions, jaw width, and more
- **3D Mesh Generation**: Generate 3D face meshes from 2D images
- **Shape Parameter Analysis**: Access to 300+ shape parameters for detailed face characterization

### 🔒 Privacy Mask Generation
- **Adaptive Masks**: Generate privacy masks based on real face measurements for optimal anonymization
- **Multiple Mask Types**:
  - Adaptive Blur: Intelligent blurring based on face structure
  - Pixelation: Face-aware pixelation
  - Noise Pattern: Privacy-preserving noise overlay
  - Synthetic Face: AI-generated replacement faces
- **Strength Control**: Adjustable privacy levels from light to complete anonymization
- **Batch Privacy Levels**: Generate multiple privacy levels simultaneously

### 🔄 Face Swapping
- **InSwapper Integration**: High-quality face swapping using the InSwapper model
- **Advanced Blending**: Sophisticated color correction and blending techniques
- **Multi-Face Support**: Handle multiple faces in single image
- **Compatibility Analysis**: Check face compatibility before swapping
- **Quality Enhancement**: Automatic sharpening and noise reduction

### ⚡ Batch Processing
- **Multi-Image Support**: Process up to 10 images simultaneously
- **Operation Types**: Face analysis, privacy masking, and more
- **Progress Tracking**: Real-time batch processing status
- **Bulk Download**: Download all processed results at once

### 🛡️ Security & Authentication
- **API Key Authentication**: Secure API access with user-specific keys
- **JWT Token Support**: Session-based authentication
- **Rate Limiting**: Tiered rate limiting (Basic: 100/hr, Premium: 500/hr, Enterprise: 2000/hr)
- **Input Validation**: Comprehensive file and content validation
- **Audit Logging**: Complete audit trail of all operations

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Modal account (for deployment)
- GPU support recommended

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-username/playalter-modal.git
   cd playalter-modal
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up Modal**
   ```bash
   pip install modal
   modal token new
   ```

4. **Deploy to Modal**
   ```bash
   modal deploy main.py
   ```

### Local Development

1. **Test the configuration**
   ```bash
   python main.py test
   ```

2. **Run local development server**
   ```bash
   python main.py serve
   ```

3. **Access the web interface**
   - Web Interface: http://localhost:8000
   - API Documentation: http://localhost:8000/docs
   - Health Check: http://localhost:8000/health

## 📚 API Usage

### Authentication
Include your API key in the Authorization header:
```bash
Authorization: Bearer your_api_key
```

### Face Analysis
```bash
curl -X POST "https://your-modal-url/api/face/analyze" \
  -H "Authorization: Bearer your_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "image_base64": "base64_encoded_image",
    "include_measurements": true,
    "include_3d_mesh": false
  }'
```

### Privacy Mask Generation
```bash
curl -X POST "https://your-modal-url/api/privacy/mask" \
  -H "Authorization: Bearer your_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "image_base64": "base64_encoded_image",
    "mask_type": "blur",
    "strength": 1.0,
    "create_levels": false
  }'
```

### Face Swapping
```bash
curl -X POST "https://your-modal-url/api/face/swap" \
  -H "Authorization: Bearer your_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "source_image_base64": "base64_encoded_source",
    "target_image_base64": "base64_encoded_target",
    "source_face_index": 0,
    "target_face_index": 0
  }'
```

### Batch Processing
```bash
curl -X POST "https://your-modal-url/api/batch/process" \
  -H "Authorization: Bearer your_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "images_base64": ["image1_base64", "image2_base64"],
    "operation": "privacy_mask",
    "parameters": {"mask_type": "blur", "strength": 1.0}
  }'
```

## 🏗️ Architecture

```
PLAYALTER Platform
├── 📁 api/                 # API endpoints and routing
├── 📁 auth/                # Authentication and security
├── 📁 config/              # Configuration management
├── 📁 services/            # Core AI services
│   ├── 🔥 flame_model.py   # FLAME model integration
│   ├── 🔒 privacy_mask.py  # Privacy mask generation
│   └── 🔄 face_swap.py     # Face swapping service
├── 📁 utils/               # Utilities and helpers
├── 📁 web/                 # Web interface
├── 📄 main.py              # Main deployment script
└── 📄 requirements.txt     # Dependencies
```

### Key Components

- **FLAME Model Service**: 3D face modeling and measurement extraction
- **Privacy Mask Generator**: Adaptive privacy protection
- **Face Swap Service**: High-quality face swapping
- **Security Manager**: Authentication, rate limiting, validation
- **File Handler**: Upload processing and validation
- **Configuration Manager**: Environment and settings management
- **Logging System**: Comprehensive logging and monitoring

## ⚙️ Configuration

### Environment Variables
```bash
# Application
PLAYALTER__ENVIRONMENT=production
PLAYALTER__DEBUG=false
PLAYALTER__LOG_LEVEL=INFO

# Modal Configuration
PLAYALTER__GPU_TYPE=T4
PLAYALTER__MEMORY_MB=16384
PLAYALTER__KEEP_WARM=1

# Security
PLAYALTER__SECURITY__MAX_FILE_SIZE_MB=10
PLAYALTER__SECURITY__RATE_LIMIT_REQUESTS=100
PLAYALTER__SECURITY__JWT_SECRET_KEY=your_secret_key

# Features
PLAYALTER__ENABLE_FACE_ANALYSIS=true
PLAYALTER__ENABLE_PRIVACY_MASKS=true
PLAYALTER__ENABLE_FACE_SWAP=true
```

### Configuration File
Create `config.json` for custom settings:
```json
{
  "app_name": "PLAYALTER Platform",
  "environment": "production",
  "model": {
    "flame_model_path": "/tmp/flame_model",
    "max_image_size": [4096, 4096]
  },
  "security": {
    "max_file_size_mb": 10,
    "rate_limit_requests": 100
  }
}
```

## 🔧 Development

### Project Structure
```
services/
├── flame_model.py      # FLAME 3D face model integration
├── privacy_mask.py     # Adaptive privacy mask generation  
└── face_swap.py        # InSwapper face swapping

api/
└── endpoints.py        # FastAPI endpoints and routing

auth/
└── security.py         # Authentication and security

utils/
├── file_handler.py     # File upload and processing
└── logging_config.py   # Logging configuration

config/
└── settings.py         # Configuration management

web/
├── index.html          # Web interface
└── script.js           # Frontend JavaScript
```

### Adding New Services

1. **Create Service Class**
   ```python
   from utils.logging_config import LoggerMixin
   
   class NewService(LoggerMixin):
       def __init__(self):
           self.logger.info("Service initialized")
       
       def process(self, data):
           # Implementation
           pass
   ```

2. **Add API Endpoint**
   ```python
   @app.function(image=image, gpu="T4", memory=16384)
   @modal.web_endpoint(method="POST", path="/api/new-service")
   async def new_service_endpoint(request: RequestModel):
       # Implementation
       pass
   ```

3. **Update Configuration**
   ```python
   # Add to settings.py
   enable_new_service: bool = True
   ```

### Testing

```bash
# Run configuration test
python main.py test

# Test specific service
python -c "from services.flame_model import FLAMEModelService; FLAMEModelService()"

# Check service status
curl http://localhost:8000/api/services/status
```

## 📊 Monitoring & Logging

### Log Files
- `playalter.log` - General application logs
- `playalter.json` - Structured JSON logs
- `errors.log` - Error logs only
- `performance.log` - Performance metrics
- `security.log` - Security events

### Metrics
- Request processing time
- Success/failure rates
- GPU utilization
- Memory usage
- Rate limit violations

## 🚧 Limitations

- **File Size**: Maximum 10MB per image
- **Batch Size**: Maximum 10 images per batch
- **Image Dimensions**: 64x64 to 4096x4096 pixels
- **Supported Formats**: JPEG, PNG, BMP, TIFF, WebP
- **Processing Time**: Maximum 5 minutes per request

## 🔮 Future Enhancements

- [ ] Video processing support
- [ ] Real-time face processing
- [ ] Custom model training
- [ ] Advanced 3D reconstruction
- [ ] Multi-language support
- [ ] Mobile app integration
- [ ] Webhook notifications
- [ ] Cloud storage integration

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

## 📞 Support

- 📧 Email: support@playalter.com
- 💬 Discord: [Join our community](https://discord.gg/playalter)
- 📚 Documentation: [docs.playalter.com](https://docs.playalter.com)
- 🐛 Issues: [GitHub Issues](https://github.com/your-username/playalter-modal/issues)

---

**Built with ❤️ using Modal, FastAPI, and cutting-edge AI models**