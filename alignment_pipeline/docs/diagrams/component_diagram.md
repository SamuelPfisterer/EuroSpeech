# Component Interaction Diagram

This diagram shows how the main components of the system interact with each other.

```mermaid
graph TB
    subgraph Pipeline
        AP[AlignmentPipeline]
    end
    
    subgraph Audio Processing
        AS[AudioSegmenter]
        VAD[VAD Providers]
        AS --> VAD
    end
    
    subgraph Transcript Processing
        TP[TranscriptPreprocessor]
        TA[TranscriptAligner]
        TPB[BasePreprocessor]
        TPP[PDFPreprocessor]
        TPT[TXTPreprocessor]
        TPM[MDPreprocessor]
        TPB --> TPP
        TPB --> TPT
        TPB --> TPM
        TP --> |uses| TPB
    end
    
    subgraph Data Models
        TS[TranscribedSegment]
        AT[AlignedTranscript]
    end
    
    AP --> AS
    AP --> TP
    AP --> TA
    AS --> TS
    TA --> AT
```

## Component Descriptions

### Pipeline
- `AlignmentPipeline`: Main orchestrator that coordinates the entire alignment process

### Audio Processing
- `AudioSegmenter`: Handles audio file segmentation and transcription
- `VAD Providers`: Different Voice Activity Detection implementations

### Transcript Processing
- `TranscriptPreprocessor`: Manages different transcript format preprocessing
- `TranscriptAligner`: Aligns transcribed segments with human transcripts
- Various preprocessor implementations for different formats

### Data Models
- `TranscribedSegment`: Represents a transcribed audio segment
- `AlignedTranscript`: Represents an aligned transcript segment 