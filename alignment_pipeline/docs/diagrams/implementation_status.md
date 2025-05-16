# Implementation Status Diagram

This diagram shows the current status of different components in the system.

```mermaid
graph TB
    classDef implemented fill:#90EE90,stroke:#333,stroke-width:2px
    classDef inprogress fill:#87CEFA,stroke:#333,stroke-width:2px
    classDef notstarted fill:#FFB6C1,stroke:#333,stroke-width:2px
    classDef tbd fill:#FFE4B5,stroke:#333,stroke-width:2px
    classDef needsrefactor fill:#FFA07A,stroke:#333,stroke-width:2px

    %% Implemented Components
    I1[TranscribedSegment]:::implemented
    I2[AlignedTranscript]:::implemented
    I3[AudioSegmenter]:::implemented
    I4[TranscriptAligner]:::implemented
    I5[PyAnnote VAD]:::needsrefactor
    I6[Silero VAD]:::needsrefactor
    I7[I/O Utilities]:::implemented
    I8[Diarization]:::implemented
    I9[Setup.py]:::implemented
    I10[Example Script]:::implemented
    I11[BasePreprocessor]:::implemented
    I12[PDFPreprocessor]:::implemented
    I13[TXTPreprocessor]:::implemented
    I14[SRTPreprocessor]:::implemented
    I16[AlignmentPipeline]:::implemented
    
    %% In Progress Components
    P1[Package Structure]:::inprogress
    
    %% Not Started Components
    N1[ConfigurationManager]:::notstarted
    N2[VAD Interface]:::notstarted
    
    %% Components Requiring Discussion
    T1[CSV Format Adapter]:::tbd

    %% Connections
    I3 --> I1
    I4 --> I2
    I5 --> I3
    I6 --> I3
    I8 --> I3
    N2 -.-> I5
    N2 -.-> I6
    P1 --> I1
    P1 --> I3
    P1 --> I4
    P1 --> I5
    P1 --> I6
    P1 --> I7
    P1 --> I8
    P1 --> I9
    P1 --> I10
    P1 --> I11
    P1 --> I12
    P1 --> I13
    P1 --> I14
    P1 --> I15
    P1 --> I16
    I16 --> I3
    I16 --> I4
    I16 --> I11
    I16 --> I12
    I16 --> I13
    I16 --> I14
    I16 --> I15
    I16 -.-> T1
```

## Status Legend

- 🟢 **Implemented**: Components that have been implemented and moved to the new structure
- 🔵 **In Progress**: Components currently being worked on
- 🔴 **Not Started**: Components that need to be created but haven't been started
- 🟡 **TBD**: Components that require further discussion/specification
- 🟠 **Needs Refactoring**: Components that work but need architectural improvements

## Component Status Details

### Implemented Components (🟢)
- `TranscribedSegment`: Moved to data_models/models.py (direct move)
- `AlignedTranscript`: Moved to data_models/models.py (direct move)
- `AudioSegmenter`: Moved to audio_processing/segmenter.py (fixed missing imports for `silence` and `tqdm`)
- `TranscriptAligner`: Moved to transcript/aligner.py (direct move)
- `I/O Utilities`: Moved to utils/io.py (direct move)
- `Diarization`: Created in audio_processing/diarization.py (extracted from main.py)
- `Setup.py`: Created in root directory with all required dependencies
- `Example Script`: Created new example in examples/basic_alignment.py
- `BasePreprocessor`: Implemented in transcript/preprocessor/base.py
- `PDFPreprocessor`: Implemented in transcript/preprocessor/pdf_preprocessor.py
- `TXTPreprocessor`: Implemented in transcript/preprocessor/txt_preprocessor.py
- `SRTPreprocessor`: Implemented in transcript/preprocessor/srt_preprocessor.py
- `AlignmentPipeline`: Implemented in pipeline/alignment_pipeline.py

### Needs Refactoring (🟠)
- `PyAnnote VAD`: Currently returns a pipeline object instead of detection results
- `Silero VAD`: Returns results directly, creating inconsistency with PyAnnote VAD
  - **Note**: These components need a common interface to be truly modular

### In Progress Components (🔵)
- `Package Structure`: Basic directory structure created and main components implemented

### Not Started Components (🔴)
- `ConfigurationManager`: For managing settings
- `VAD Interface`: Common interface needed for all VAD implementations

### To Be Determined (🟡)
- `CSV Format Adapter`: Need more flexible CSV processing to handle different parliament dataset formats

## Key Changes Made

1. **Fixed Components**:
   - Added missing `from pydub import silence` import in AudioSegmenter
   - Added missing `from tqdm import tqdm` import in AudioSegmenter
   - Fixed progress bar implementation in segment_and_transcribe method
   - Modified `segment_audio` to use Silero VAD directly for non-speech detection

2. **Structural Changes**:
   - Separated VAD implementations into modular components
   - Extracted diarization initialization to standalone module
   - Created proper package structure with __init__.py files

3. **New Components**:
   - Created example script for demonstrating library usage
   - Added setup.py for package installation
   - Created comprehensive documentation and diagrams
   - Implemented transcript preprocessor system with base class and two concrete implementations
   - Implemented alignment pipeline with two-level selection process

## VAD Inconsistency Issue

There's currently an architectural inconsistency between the VAD implementations:

1. `initialize_vad_pipeline()` returns a **VAD pipeline object** that:
   - Is initialized once
   - Is passed to AudioSegmenter
   - Is called to get speech regions

2. `get_silero_vad()` returns the **detection results** directly:
   - Is called each time detection is needed
   - Reinitializes the model on each call
   - Returns the non-speech regions

This inconsistency should be resolved by designing a common VAD interface that all implementations follow, likely with:
- A consistent initialization method
- A consistent detection method 
- Common return types

## CSV Processing Limitations

The current CSV processing implementation in `AlignmentPipeline` has some limitations:
- Basic URL parsing that may not work for all parliamentary websites
- Limited ability to handle diverse CSV formats with different column structures
- No configuration options for mapping different CSV schemas

A more robust approach might include:
- Configurable column mapping
- Enhanced URL parsing for different parliament websites
- Support for custom extraction logic for different datasets

## Next Steps

1. Design and implement a common VAD interface
2. Add configuration management system
3. Create unit tests for all components
4. Add proper logging throughout the library
5. Enhance CSV processing to handle more formats
6. Create more examples of pipeline usage 

## Future To-Dos

1. **Modular ASR and Diarization in AudioSegmenter**:
   - Allow users to provide custom ASR models through dependency injection
   - Enable swapping diarization models with a common interface

2. **Whisper Model Optimization**:
   - Implement batching for Whisper ASR processing
   - Evaluate and integrate faster-whisper implementation

3. **Directory Handling in AlignmentPipeline**:
   - Implement proper directory creation when paths don't exist

4. **Supabase Logging**:
   - Implement basic progress logging to Supabase

5. **Multi-GPU Deployment**:
   - Design parallel processing architecture for multiple GPUs

6. **Enhanced Transcript Preprocessors**:
   - LLM preprocessing: Pass preprocessor output through an LLM with cleaning prompts
   - Regex/rule-based preprocessing: Allow passing pattern rules for text cleaning
   - Provide predefined pattern mappings (e.g., "brackets" → regex to remove all brackets)
   - Create configurable preprocessing pipelines

7. **Library Update Handling**:
   - Investigate how library updates affect existing running processes
   - Implement versioning system to manage compatibility
   - Design migration pathways for existing deployments

8. **Multi-Transcript Alignment Strategy**:
   - Implement the option to merge multiple transcripts that are potential matches for a video
   - the transcriptaligner should find the matching parts of the transcripts automatically already

## Potentially Update Documentation For

1. **SRT Preprocessor**:
   - Add documentation for the SRT preprocessor in the main README
   - Update component diagram to include SRTPreprocessor
   - Add example usage for subtitle files
   - Update supported file types in user documentation 