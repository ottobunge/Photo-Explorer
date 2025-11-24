# Photo Explorer - AI Models Specification

## Overview

Photo Explorer uses AI models for various tasks including image embeddings, face detection, and scene understanding. This document specifies the model management system that allows users to browse, download, and configure models directly from the application.

## Supported Model Types

### Image Embedding Models (CLIP)

CLIP (Contrastive Language-Image Pre-training) models generate vector embeddings for both images and text, enabling semantic search.

| Model | Size | Accuracy | Speed | Use Case |
|-------|------|----------|-------|----------|
| ViT-B-32 | ~350MB | Good | Fast | Default, general use |
| ViT-B-16 | ~350MB | Better | Medium | Better accuracy |
| ViT-L-14 | ~900MB | Best | Slow | High quality searches |
| ViT-H-14 | ~2GB | Excellent | Very Slow | Maximum accuracy |

### Face Detection Models (InsightFace)

InsightFace models detect faces and generate face embeddings for recognition and clustering.

| Model | Size | Faces/Image | Speed | Use Case |
|-------|------|-------------|-------|----------|
| buffalo_s | ~30MB | Up to 10 | Fast | Quick processing |
| buffalo_m | ~60MB | Up to 20 | Medium | Balanced |
| buffalo_l | ~100MB | Up to 50 | Slow | Large group photos |

## Model Storage

Models are stored in the user's home directory:

```
~/.cache/photo-explorer/
├── models/
│   ├── clip/
│   │   └── ViT-B-32/
│   │       └── open_clip_pytorch_model.bin
│   ├── faces/
│   │   └── buffalo_l/
│   │       ├── det_10g.onnx
│   │       └── w600k_r50.onnx
│   └── huggingface/
│       └── author--model-name/
│           └── model files...
└── config.yaml
```

## Hugging Face Integration

### Supported Functionality

The system integrates with Hugging Face Hub for model discovery and download:

1. **Search Models**: Search Hugging Face for models by task or keyword
2. **Model Info**: Get detailed information about any model
3. **Download**: Download models directly to local storage
4. **Track Downloads**: Monitor download progress in real-time

### Supported Tasks

| Task ID | Description | Example Models |
|---------|-------------|----------------|
| `image-feature-extraction` | CLIP-style embeddings | openai/clip-vit-base-patch32 |
| `zero-shot-image-classification` | Image classification | openai/clip-vit-large-patch14 |
| `image-to-text` | Image captioning | Salesforce/blip-image-captioning-base |
| `visual-question-answering` | VQA models | dandelin/vilt-b32-finetuned-vqa |

### Recommended Models

The system provides curated recommended models:

```yaml
recommended_models:
  clip:
    - id: laion/CLIP-ViT-B-32-laion2B-s34B-b79K
      name: CLIP ViT-B/32 (LAION)
      description: Fast, good quality embeddings

    - id: laion/CLIP-ViT-L-14-laion2B-s32B-b82K
      name: CLIP ViT-L/14 (LAION)
      description: Higher quality, slower

  face_detection:
    - id: buffalo_l
      name: InsightFace Buffalo Large
      description: Best accuracy for group photos
```

---

## Configuration

### Model Configuration File

```yaml
# ~/.cache/photo-explorer/config.yaml
models:
  active:
    clip:
      model_id: laion/CLIP-ViT-B-32-laion2B-s34B-b79K
      pretrained: laion2b_s34b_b79k
    face_detection:
      model_id: buffalo_l

  settings:
    auto_download: false
    max_cache_size_gb: 10
    prefer_quantized: false
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `PHOTO_EXPLORER_MODELS_DIR` | Model storage directory | `~/.cache/photo-explorer/models` |
| `PHOTO_EXPLORER_CLIP_MODEL` | Active CLIP model | `ViT-B-32` |
| `PHOTO_EXPLORER_FACE_MODEL` | Active face model | `buffalo_l` |
| `HF_HOME` | Hugging Face cache directory | `~/.cache/huggingface` |

---

## API Endpoints

### Search Models

```http
GET /api/v1/models/search?query={query}&task={task}&limit={limit}

Response:
{
  "models": [
    {
      "model_id": "openai/clip-vit-base-patch32",
      "author": "openai",
      "model_name": "clip-vit-base-patch32",
      "downloads": 1500000,
      "likes": 500,
      "task": "image-feature-extraction",
      "last_modified": "2024-01-15T10:30:00Z",
      "size_mb": 350,
      "is_downloaded": false
    }
  ]
}
```

### Get Model Info

```http
GET /api/v1/models/info/{author}/{model_name}

Response:
{
  "model_id": "openai/clip-vit-base-patch32",
  "author": "openai",
  "model_name": "clip-vit-base-patch32",
  "description": "CLIP model with ViT-B/32 architecture",
  "tags": ["clip", "vision", "pytorch"],
  "downloads": 1500000,
  "likes": 500,
  "task": "image-feature-extraction",
  "size_mb": 350,
  "files": [
    {"name": "pytorch_model.bin", "size_mb": 340},
    {"name": "config.json", "size_mb": 0.001}
  ],
  "is_downloaded": true
}
```

### Download Model

```http
POST /api/v1/models/download
Content-Type: application/json

{
  "model_id": "openai/clip-vit-base-patch32",
  "revision": "main"
}

Response:
{
  "model_id": "openai/clip-vit-base-patch32",
  "status": "downloading",
  "progress": 0,
  "total_size_mb": 350,
  "downloaded_mb": 0
}
```

### List Downloaded Models

```http
GET /api/v1/models/downloaded

Response:
{
  "models": [
    {
      "model_id": "openai/clip-vit-base-patch32",
      "path": "/home/user/.cache/photo-explorer/models/huggingface/openai--clip-vit-base-patch32",
      "size_mb": 350,
      "downloaded_at": "2024-01-20T14:30:00Z"
    }
  ]
}
```

### Get Recommended Models

```http
GET /api/v1/models/recommended

Response:
{
  "clip": [
    {
      "model_id": "laion/CLIP-ViT-B-32-laion2B-s34B-b79K",
      "name": "CLIP ViT-B/32 (LAION)",
      "description": "Fast, good quality embeddings",
      "downloads": 500000,
      "is_downloaded": false
    }
  ],
  "face_detection": [
    {
      "model_id": "buffalo_l",
      "name": "InsightFace Buffalo Large",
      "description": "Best accuracy for group photos",
      "is_downloaded": true
    }
  ]
}
```

### Get/Set Active Models

```http
GET /api/v1/models/active

Response:
{
  "clip": {
    "model_id": "laion/CLIP-ViT-B-32-laion2B-s34B-b79K",
    "status": "loaded"
  },
  "face_detection": {
    "model_id": "buffalo_l",
    "status": "loaded"
  }
}
```

```http
POST /api/v1/models/active
Content-Type: application/json

{
  "task": "clip",
  "model_id": "laion/CLIP-ViT-L-14-laion2B-s32B-b82K"
}

Response:
{
  "task": "clip",
  "model_id": "laion/CLIP-ViT-L-14-laion2B-s32B-b82K",
  "status": "loading"
}
```

---

## UI Components

### Models Settings Section

```
AI Models
├── Active Models
│   ├── Image Embeddings (CLIP)
│   │   └── ViT-B/32 (LAION) - 350MB [Change]
│   └── Face Detection
│       └── buffalo_l - 100MB [Change]
│
├── Downloaded Models (3)
│   ├── laion/CLIP-ViT-B-32... [Active] [Delete]
│   ├── laion/CLIP-ViT-L-14... [Set Active] [Delete]
│   └── buffalo_l [Active] [Delete]
│
├── Recommended Models
│   ├── CLIP ViT-B/32 (Fast) [Downloaded]
│   ├── CLIP ViT-L/14 (Accurate) [Download]
│   └── Buffalo Large [Downloaded]
│
└── Browse Hugging Face
    ├── Search: [________________] [Search]
    ├── Or lookup by ID: [Lookup by ID]
    └── Results:
        └── model cards with [Download] buttons
```

### Model Download Dialog

```
Downloading: openai/clip-vit-base-patch32

[████████████░░░░░░░░] 60%
Downloaded: 210 MB / 350 MB
Speed: 15 MB/s
ETA: 10 seconds

[Cancel]
```

---

## Command Line Interface

### Download Models via CLI

```bash
# Download all recommended models
task models:setup

# Search for models
task models:search -- "CLIP vision"

# Download specific model
task models:download -- laion/CLIP-ViT-B-32-laion2B-s34B-b79K

# List downloaded models
task models:list
```

### Poetry Scripts

```bash
# Run model downloader directly
poetry run download-models --all
poetry run download-models --clip
poetry run download-models --face

# Use HuggingFace browser
poetry run python -m app.infrastructure.models.huggingface search "CLIP"
poetry run python -m app.infrastructure.models.huggingface info openai/clip-vit-base-patch32
poetry run python -m app.infrastructure.models.huggingface download openai/clip-vit-base-patch32
```

---

## Processing Pipeline Integration

### Model Loading

Models are loaded on-demand and cached in memory:

```python
class ModelManager:
    def __init__(self):
        self._clip_model: Optional[CLIPModel] = None
        self._face_model: Optional[FaceModel] = None

    async def get_clip_model(self) -> CLIPModel:
        if self._clip_model is None:
            config = await self.get_active_config("clip")
            self._clip_model = await CLIPModelLoader.load(config)
        return self._clip_model

    async def set_active_model(self, task: str, model_id: str):
        # Update configuration
        await self.config_repo.set_active_model(task, model_id)
        # Invalidate cache to force reload
        if task == "clip":
            self._clip_model = None
        elif task == "face_detection":
            self._face_model = None
```

### Embedding Generation

```python
async def generate_embeddings(photo: Photo) -> Embeddings:
    model = await model_manager.get_clip_model()

    # Load image
    image = await load_image(photo.source_path)

    # Generate embedding
    embedding = model.encode_image(image)

    return Embeddings(
        photo_id=photo.id,
        clip_embedding=embedding,
        model_id=model.model_id
    )
```

---

## Security Considerations

### Model Source Validation

- Only allow downloads from Hugging Face Hub
- Verify model checksums when available
- Scan for known malicious model files

### Storage Permissions

- Models stored in user-writable directory
- Config files have restrictive permissions (600)
- No execution of downloaded content

### Resource Limits

- Maximum model cache size configurable
- Automatic cleanup of unused models
- Memory limits for loaded models

---

## Future Enhancements

### Planned Features

1. **Model Quantization**: Support for quantized models (INT8, FP16)
2. **Custom Model Training**: Fine-tune models on user's photos
3. **Model Comparison**: Compare embedding quality across models
4. **Auto-Update**: Automatic model updates when new versions available
5. **Offline Mode**: Full functionality without internet connection

### Additional Model Types

| Type | Purpose | Example |
|------|---------|---------|
| Image Captioning | Generate descriptions | BLIP, BLIP-2 |
| Object Detection | Identify objects | DETR, YOLOv8 |
| OCR | Extract text from images | TrOCR, PaddleOCR |
| Depth Estimation | 3D understanding | MiDaS |
