# Human-in-the-Loop Video Labeling Tool

A web-based tool for extracting frames from videos, auto-labeling with YOLO, and human verification.

## Features

- Video upload (AVI, MP4, MOV, MKV, WMV)
- Frame extraction at configurable intervals (5, 10, 15, 30 seconds)
- YOLO-based automatic object detection
- Manual bounding box editing (add, delete, resize)
- Frame approval/rejection workflow
- YOLO format export (ZIP)
- File-based system (no database required)
- Remote access support (via ngrok)

## Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Copy YOLO model file
# weights/best.pt (custom trained) or weights/yolo11n.pt (COCO)
```

## Running

```bash
python run.py
```

After the server starts:
- Web Interface: http://localhost:8000/web/index.html
- API Docs: http://localhost:8000/docs

### Remote Access (ngrok)

Install ngrok (one-time):
```bash
# Windows (cmd)
winget install ngrok -s msstore

# Or download from https://ngrok.com/download
```

Run ngrok:
```bash
# In another terminal
ngrok http 8000

# Share the ngrok URL: https://xxxx.ngrok.io/web/index.html
```

## Project Structure

```
labeling/
├── backend/
│   ├── config.py              # Class definitions, settings
│   ├── main.py                # FastAPI application
│   ├── routers/
│   │   ├── video.py           # Video endpoints
│   │   ├── labeling.py        # Labeling endpoints
│   │   └── export.py          # Export endpoints
│   └── services/
│       ├── file_manager.py    # File operations
│       └── auto_labeler.py    # YOLO integration
├── frontend/web/
│   ├── index.html             # Web interface
│   └── config.js              # Frontend settings
├── data/
│   ├── uploads/               # Uploaded videos
│   ├── frames/                # Extracted frames
│   └── labels/                # Label files (txt)
├── weights/                   # YOLO model files
├── requirements.txt
├── run.py                     # Launcher
├── prepare_training.py        # YOLO training dataset preparation
└── README.md
```

## Class Definitions

| ID | Class | Color |
|----|-------|-------|
| 0 | person | Red |
| 1 | car | Blue |
| 2 | falldown | Yellow |
| 3 | bus | Green |
| 4 | truck | Purple |
| 5 | bicycle | Orange |
| 6 | motorcycle | Cyan |
| 7 | boar | Brown |
| 8 | tractor | Gray |
| 9 | scooter | Pink |
| 10 | cat | Lime |
| 11 | dog | Gold |

## API Endpoints

### Video Operations

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/videos/upload` | Upload video |
| GET | `/api/videos` | List all videos |
| GET | `/api/videos/{video_id}` | Get video details |
| DELETE | `/api/videos/{video_id}` | Delete video and related files |
| POST | `/api/videos/{video_id}/extract` | Extract frames |
| GET | `/api/videos/{video_id}/frames` | List video frames |
| GET | `/api/videos/{video_id}/delete-info` | Get deletion info |

### Labeling Operations

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/classes` | Get class list with colors |
| GET | `/api/frames/{video_id}/{frame_id}` | Get frame details with labels |
| GET | `/api/frames/{video_id}/{frame_id}/image` | Get frame image |
| POST | `/api/frames/{video_id}/{frame_id}/auto-label` | Auto-label with YOLO |
| PUT | `/api/frames/{video_id}/{frame_id}/labels` | Update labels |
| POST | `/api/frames/{video_id}/{frame_id}/approve` | Approve frame |
| POST | `/api/frames/{video_id}/{frame_id}/reject` | Reject frame (delete labels) |
| GET | `/api/stats` | Get overall statistics |
| GET | `/api/model-info` | Get YOLO model info |

### Export Operations

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/export/{video_id}` | Export as YOLO format ZIP |
| GET | `/api/export/{video_id}/stats` | Get export statistics |

## API Usage Examples

### Upload Video

```bash
curl -X POST "http://localhost:8000/api/videos/upload" \
  -F "file=@video.avi" \
  -F "folder_name=dataset1"
```

### Extract Frames

```bash
curl -X POST "http://localhost:8000/api/videos/my_video/extract" \
  -H "Content-Type: application/json" \
  -d '{"frame_interval": 10}'
```

### Auto-Label

```bash
curl -X POST "http://localhost:8000/api/frames/my_video/my_video_0001/auto-label" \
  -H "Content-Type: application/json" \
  -d '{"confidence_threshold": 0.35}'
```

### Update Labels

```bash
curl -X PUT "http://localhost:8000/api/frames/my_video/my_video_0001/labels" \
  -H "Content-Type: application/json" \
  -d '{
    "labels": [
      {
        "class_id": 0,
        "class_name": "person",
        "x_center": 0.5,
        "y_center": 0.5,
        "width": 0.2,
        "height": 0.4,
        "confidence": 0.85
      }
    ]
  }'
```

### Export Single Video

```bash
# Only approved frames
curl -O "http://localhost:8000/api/export/my_video?only_approved=true"

# With class IDs instead of names
curl -O "http://localhost:8000/api/export/my_video?use_class_id=true"
```

## Preparing YOLO Training Dataset

To prepare a complete training dataset from all approved labels:

```bash
python prepare_training.py
```

This will create:
```
dataset/
├── images/
│   ├── train/          # 80% of images
│   └── val/            # 20% of images
├── labels/
│   ├── train/          # Corresponding labels
│   └── val/
├── train.txt           # List of training image paths
├── val.txt             # List of validation image paths
├── data.yaml           # YOLO training config
└── classes.txt         # Class names
```

Options:
```bash
# Custom split ratio (default: 0.8)
python prepare_training.py --split 0.9

# Custom output directory
python prepare_training.py --output my_dataset

# Shuffle before split
python prepare_training.py --shuffle
```

Then train with:
```bash
yolo detect train data=dataset/data.yaml model=yolo11n.pt epochs=100
```

## Label File Format

Labels are stored as `.txt` files in YOLO format:

```
class_id x_center y_center width height
```

Example:
```
0 0.512500 0.486111 0.156250 0.388889
1 0.734375 0.652778 0.203125 0.180556
```

- Coordinates are normalized (0-1 range)
- `x_center`, `y_center`: Bounding box center
- `width`, `height`: Bounding box dimensions

## Status Management

The system is file-based:
- Frame has `.txt` file: **Approved**
- Frame has no `.txt` file: **Pending**

## Requirements

- Python 3.8+
- FastAPI
- Uvicorn
- OpenCV
- Ultralytics (YOLO)
- NumPy

## Notes

- Default confidence threshold: 0.35
- Supported video formats: AVI, MP4, MOV, MKV, WMV
- Non-ASCII filenames are handled automatically
- ffmpeg codec warnings are suppressed
