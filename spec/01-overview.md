# Photo Explorer - Project Overview

## Vision

Photo Explorer is a self-hosted application that enables users to organize, search, and explore their photo collections using AI-powered semantic search and face recognition capabilities.

## Core Objectives

1. **Semantic Photo Search**: Allow users to search photos using natural language queries (e.g., "sunset at the beach", "family dinner", "dog playing in snow")
2. **Face Recognition & Tagging**: Automatically detect faces, group similar faces, and allow users to tag them with names
3. **Flexible Photo Import**: Support both direct uploads and scanning of local filesystem directories
4. **Rich Metadata**: Extract and display photo metadata including location, date, scene type (indoor/outdoor), detected objects, and faces

## Technology Stack

### Backend
- **Framework**: Python FastAPI
- **Vector Database**: Qdrant (for storing and searching CLIP embeddings)
- **Image Embeddings**: CLIP (Contrastive Language-Image Pre-training)
- **Vision Model**: High-end vision LLM for detailed image descriptions
- **Face Detection**: InsightFace or similar library
- **Database**: PostgreSQL (for metadata, albums, face tags)
- **Task Queue**: Celery with Redis (for background processing)

### Frontend
- **Framework**: SvelteKit
- **Styling**: TailwindCSS
- **State Management**: Svelte stores
- **Image Handling**: Lazy loading, virtual scrolling for large galleries

### Infrastructure
- **Container Runtime**: Docker with docker-compose
- **Development**: NixOS with shell.nix for reproducible environments
- **Task Runner**: Taskfile (go-task)

## User Flows

### 1. Photo Upload Flow
```
User uploads photos/albums → Backend receives files →
Background job processes each photo:
  1. Extract EXIF metadata
  2. Generate CLIP embedding
  3. Run vision model for description
  4. Detect faces and generate face embeddings
  5. Store all data in Qdrant + PostgreSQL
```

### 2. Folder Scanning Flow
```
User configures folder path → Backend scans directory →
For each new/modified photo:
  Same processing pipeline as upload flow
  Maintains sync with filesystem changes
```

### 3. Search Flow
```
User enters text query → Backend generates CLIP text embedding →
Query Qdrant for similar image embeddings →
Return ranked results with metadata
```

### 4. Face Tagging Flow
```
User navigates to Face Explorer → Views clustered faces →
Selects a face cluster → Assigns a name →
All photos with that face are now tagged
```

## Key Features

- **Albums**: Organize photos into albums (manual or auto-generated)
- **Smart Search**: Natural language photo search
- **Face Groups**: Automatic clustering of similar faces
- **Face Tagging**: Manual assignment of names to face clusters
- **Metadata View**: EXIF data, AI-generated descriptions, detected objects
- **Scene Classification**: Indoor/outdoor detection, scene type
- **Folder Sync**: Keep in sync with local directories
- **Batch Operations**: Tag multiple photos, move between albums

## Non-Goals (v1)

- Cloud storage integration (future consideration)
- Mobile app (web-responsive only for v1)
- Video support (photos only for v1)
- Multi-user/authentication (single user for v1)
