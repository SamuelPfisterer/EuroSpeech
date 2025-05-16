# Directory Structure Explanation

```
parliament_transcript_aligner/
├── parliament_transcript_aligner/        # Main package directory
│   ├── __init__.py                      # Package initialization
│   ├── audio_processing/                # Audio processing components
│   │   ├── __init__.py
│   │   ├── segmenter.py                # AudioSegmenter class
│   │   └── vad/                        # Voice Activity Detection implementations
│   │       ├── __init__.py
│   │       ├── pyannote_vad.py         # PyAnnote VAD implementation
│   │       └── silero_vad.py           # Silero VAD implementation
│   ├── transcript/                      # Transcript processing components
│   │   ├── __init__.py
│   │   ├── preprocessor/               # Transcript preprocessing system
│   │   │   ├── __init__.py
│   │   │   ├── base.py                # Base preprocessor interface
│   │   │   ├── pdf_preprocessor.py    # PDF-specific preprocessor
│   │   │   ├── txt_preprocessor.py    # Text-specific preprocessor
│   │   │   └── md_preprocessor.py     # Markdown-specific preprocessor
│   │   └── aligner.py                 # TranscriptAligner implementation
│   ├── data_models/                    # Data structures and models
│   │   ├── __init__.py
│   │   └── models.py                  # TranscribedSegment and AlignedTranscript
│   ├── pipeline/                       # Pipeline orchestration
│   │   ├── __init__.py
│   │   └── alignment_pipeline.py      # Main pipeline implementation
│   ├── config/                         # Configuration management
│   │   ├── __init__.py
│   │   └── settings.py                # Configuration settings and defaults
│   └── utils/                         # Utility functions
│       ├── __init__.py
│       ├── io.py                      # I/O operations
│       └── cache.py                   # Caching utilities
├── tests/                             # Test directory
├── docs/                              # Documentation
│   ├── diagrams/                      # Mermaid diagrams
│   └── api/                           # API documentation
├── setup.py                           # Package setup file
├── README.md                          # Main documentation
└── LICENSE                            # License file
```

## Directory Structure Rationale

### 1. Audio Processing (`audio_processing/`)
- Separates VAD implementations to allow easy switching between providers
- Keeps audio segmentation logic isolated from transcript processing
- Makes it easy to add new VAD providers in the future

### 2. Transcript Processing (`transcript/`)
- Modular preprocessor system with a base interface
- Each format has its own implementation file
- Aligner is separate from preprocessors for clear separation of concerns

### 3. Data Models (`data_models/`)
- Central location for all data structures
- Makes it easy to maintain data consistency across the package
- Simplifies type hints and documentation

### 4. Pipeline (`pipeline/`)
- Contains the main orchestration logic
- Coordinates between audio processing and transcript handling
- Manages the flow of data through the system

### 5. Configuration (`config/`)
- Centralized configuration management
- Easy to modify settings without changing code
- Supports different environments (development, production)

### 6. Utils (`utils/`)
- Common utilities used across the package
- Separates I/O operations from business logic
- Dedicated caching system for performance optimization

### 7. Tests and Documentation
- Separate test directory for unit tests
- Documentation organized by type (diagrams, API docs)
- Easy to maintain and extend documentation 