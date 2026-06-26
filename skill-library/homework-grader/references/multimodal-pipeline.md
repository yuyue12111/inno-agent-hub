# Multimodal Processing Pipeline

This document details the Intermediate Representation (IR) format and the
processing pipelines for text, image, and video submissions.

---

## Design Principle

The evaluation engine is modality-agnostic. It scores submissions based solely
on the Intermediate Representation (IR), a unified JSON format. Each modality
has its own preprocessing pipeline that converts raw files into IR.

```
Raw Files                    Pipelines                    Evaluation Engine
─────────                    ─────────                    ─────────────────
.docx/.pdf  ──→  Text Pipeline    ──→  IR (JSON)  ──→  Score against Rubric
.jpg/.png   ──→  Image Pipeline   ──→  IR (JSON)  ──→  Score against Rubric
.mp4        ──→  Video Pipeline   ──→  IR (JSON)  ──→  Score against Rubric
mixed       ──→  Combined         ──→  IR (JSON)  ──→  Score against Rubric
```

---

## Intermediate Representation (IR)

The IR schema is defined in `templates/ir-schema.json`. This section explains
the design rationale and field semantics.

### Common Fields (All Modalities)

| Field | Type | Purpose |
|-------|------|---------|
| `student_id` | string | Anonymous ID (format: `anon-NNN`). Real identity stays in local mapping file. |
| `submission_type` | enum | `text`, `image`, `video`, `mixed` |
| `source_files` | string[] | Relative paths to original files in `workspace/raw/` |
| `extracted_at` | datetime | When preprocessing completed |
| `metadata` | object | Modality-specific metadata (word count, image count, duration, etc.) |
| `content` | object | Modality-specific extracted content |
| `gate_results` | array | Results of gate checks (populated during preprocessing) |
| `processing_log` | array | Step-by-step processing log for debugging |

### Anonymization

Student identity is **never** included in the IR or sent to the Claude API.

- The `student_id` field uses anonymous identifiers (`anon-001`, `anon-002`, etc.)
- A local mapping file (`workspace/student-mapping.csv`) maps anonymous IDs
  back to real student info (student number, name)
- This mapping file is used only during Excel export, never during scoring
- File names in `source_files` should be anonymized during preprocessing

---

## Text Pipeline

**Input**: `.docx` or `.pdf` files

### Processing Steps

```
1. Format Detection
   ├─ Check file extension
   ├─ Verify with magic bytes (optional)
   └─ Reject if unrecognized → log as format_error

2. Text Extraction
   ├─ .docx → python-docx: extract paragraphs, headings, tables
   ├─ .pdf  → PyMuPDF (fitz): extract text blocks with position info
   └─ Failure → log as extraction_error, skip submission

3. Structure Parsing
   ├─ Identify heading hierarchy (H1, H2, H3)
   ├─ Split into sections based on headings
   ├─ Convert to Markdown format
   └─ If no headings found → treat as single section, split on double newlines

4. Metadata Extraction
   ├─ Word count (CJK: character count; alphabetic: whitespace-split)
   ├─ Paragraph count
   ├─ Heading count
   ├─ Reference section detection (keyword scan)
   └─ Language detection (simple heuristic: CJK ratio)

5. IR Generation
   └─ Assemble into IR JSON schema
```

### IR Content Fields (Text)

```json
{
  "content": {
    "full_text": "Complete text in Markdown format",
    "sections": [
      {
        "heading": "一、引言",
        "level": 1,
        "text": "Section body text..."
      }
    ]
  },
  "metadata": {
    "word_count": 2350,
    "paragraph_count": 18,
    "heading_count": 5,
    "has_references": true,
    "language": "zh-CN"
  }
}
```

### Text Pipeline Error Handling

| Error | Detection | Action |
|-------|-----------|--------|
| Password-protected file | python-docx / PyMuPDF raises exception | Log, mark as `protected_file` |
| Corrupted file | Parse failure | Log, mark as `corrupted_file` |
| Empty document | `word_count < 10` | Log, mark as `empty_submission` |
| Encoding issues | Unicode decode errors | Try multiple encodings, fall back to lossy decode |
| Embedded images in docx | Image elements detected | Extract and note in metadata (future: feed to Image Pipeline) |

---

## Image Pipeline

**Input**: `.jpg`, `.png` files

### Processing Steps

```
1. Format Validation
   ├─ Open with Pillow (PIL)
   ├─ Verify image is readable and not corrupted
   └─ Failure → log as format_error

2. Metadata Extraction
   ├─ Resolution (width × height)
   ├─ File size
   ├─ Color mode
   └─ EXIF data (if present, strip for privacy)

3. Content Understanding (Claude Vision API)
   ├─ Send image to Claude with structured analysis prompt
   ├─ Receive: image type, visual elements, extracted text (OCR),
   │          design observations
   └─ API failure → retry 3×, then mark as vision_error

4. IR Generation
   └─ Assemble image descriptions into IR JSON
```

### Claude Vision Prompt for Image Analysis

```
You are a visual content analyst. Analyze this image and provide a structured
description in the following format:

1. **Image Type**: What kind of image is this? (poster, infographic, UI design,
   screenshot, diagram, photo, etc.)

2. **Visual Elements**:
   - Primary visual elements (text, graphics, colors, layout)
   - Composition and visual hierarchy
   - Brand/theme consistency (if applicable)

3. **Text Content**: Extract all readable text from the image (OCR).

4. **Design Quality Observations**:
   - Professional quality assessment
   - Specific strengths
   - Areas for improvement

Output as structured text with the section headers above.
```

### IR Content Fields (Image)

```json
{
  "content": {
    "images": [
      {
        "file": "raw/anon-002-1.jpg",
        "type": "Marketing poster",
        "visual_elements": "Bold headline in red, product image center...",
        "extracted_text": "新品上市 限时优惠...",
        "design_observations": "Professional layout with clear hierarchy...",
        "description": "Combined structured description..."
      }
    ]
  },
  "metadata": {
    "image_count": 2,
    "resolutions": ["1920x1080", "1080x1920"],
    "total_size_mb": 3.2
  }
}
```

### Multi-Image Submissions

When a student submits multiple images:
- Process each image independently through the Vision API
- Store results as separate entries in `content.images[]`
- Metadata aggregates across all images
- The scoring engine receives all image descriptions together

---

## Video Pipeline (V2 — Future)

**Input**: `.mp4` files

This pipeline is planned for a future version. The design is documented here
for reference.

### Processing Steps

```
1. Format Validation
   ├─ FFprobe: extract duration, resolution, codec, FPS
   └─ Failure → log as format_error

2. Keyframe Extraction
   ├─ FFmpeg: extract one frame every N seconds
   │  (N = max(5, duration/20) to get ~20 keyframes)
   └─ Save as temporary PNG files

3. Audio Extraction
   ├─ FFmpeg: extract audio track as WAV
   └─ No audio track → skip, note in metadata

4. Audio Transcription
   ├─ Whisper API or local Whisper model
   ├─ Output: timestamped transcript
   └─ Low quality → flag in processing_log

5. Keyframe Analysis
   ├─ Claude Vision API on each keyframe
   └─ Output: per-frame structured description

6. Timeline Assembly
   ├─ Merge transcript timestamps with keyframe descriptions
   ├─ Generate timeline summary
   └─ Extract production observations (camera, audio, editing)

7. IR Generation
   └─ Assemble all components into IR JSON
```

### IR Content Fields (Video)

```json
{
  "content": {
    "transcript": "Timestamped transcript...",
    "keyframes": [
      { "timestamp": "00:00:05", "description": "Title screen..." },
      { "timestamp": "00:00:15", "description": "Presenter speaking..." }
    ],
    "timeline_summary": "0-10s intro; 10-60s main content; 60-120s conclusion",
    "production_observations": {
      "camera_stability": "Stable, tripod used",
      "audio_quality": "Clear, no background noise",
      "editing_style": "Moderate pace, subtitles present"
    }
  },
  "metadata": {
    "duration_seconds": 120,
    "resolution": "1920x1080",
    "fps": 30,
    "file_size_mb": 85
  }
}
```

---

## Mixed Modality Handling

For submissions that contain multiple modalities (e.g., a docx report + images,
or an mp4 + docx operation report):

### Processing Strategy

1. Identify all files belonging to one student
2. Route each file to its appropriate pipeline
3. Merge the resulting IR content into a single IR document
4. Set `submission_type: mixed`
5. `source_files` lists all files
6. `content` contains fields from all modalities

### Scoring Mixed Submissions

When the Rubric has dimensions that apply to different modalities:
- The scoring prompt explicitly states which content to evaluate for each
  dimension
- Evidence citations must indicate the source modality ("From the text
  report:" or "From image analysis:")
- Dimensions like "visual_presentation" use image content; dimensions like
  "strategy_logic" use text content

---

## File Organization in Workspace

```
workspace/{batch-id}/
├── raw/                    # Original files (organized by student)
│   ├── anon-001.docx
│   ├── anon-002.docx
│   ├── anon-003-report.docx
│   ├── anon-003-poster.jpg
│   └── ...
├── ir/                     # Preprocessed IR files (one per student)
│   ├── anon-001.json
│   ├── anon-002.json
│   └── ...
├── scores/                 # Scoring results (one per student)
│   ├── anon-001.json
│   ├── anon-002.json
│   └── ...
├── reports/                # Exported reports
│   ├── grades.xlsx
│   └── calibration-report.md
├── logs/                   # Processing logs
│   └── batch.log
├── progress.json           # Batch progress checkpoint
└── student-mapping.csv     # Anonymous ID ↔ real identity (local only)
```

### Student Mapping File

```csv
anon_id,student_number,name
anon-001,20230101,张三
anon-002,20230102,李四
anon-003,20230103,王五
```

This file is:
- Created by the teacher before preprocessing
- Used only during Excel export to restore real identities
- Never uploaded to any API
- Never included in IR files
