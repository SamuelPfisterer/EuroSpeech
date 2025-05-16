# Parliament Transcript Aligner

A Python library for aligning parliamentary audio recordings with their corresponding transcripts.

## Project Status: In Development 🚧

This project is currently being refactored from a monolithic script into a modular library.

## Architecture

The library consists of several key components:

### Existing Components (Ready to Move)
- `AudioSegmenter`: Handles audio file segmentation and transcription
- `TranscriptAligner`: Aligns transcribed segments with human transcripts
- Data Models: `TranscribedSegment` and `AlignedTranscript`
- Basic I/O utilities

### Components to Create
1. `AlignmentPipeline`: Main orchestrator class
   - Coordinates the entire alignment process
   - Handles multiple transcript processing
   - Manages CER-based transcript selection

2. `TranscriptPreprocessor` System
   - Base preprocessor interface
   - Implementations for different transcript formats (PDF, TXT, MD)
   - Extensible for new formats

3. Configuration Management
   - Settings for VAD, diarization
   - Preprocessing parameters
   - CER thresholds
   - Cache configuration

### Open Questions/TODOs

#### Critical Path Items
- [ ] Define interface for transcript preprocessors
- [ ] Specify CER calculation and transcript selection logic
- [ ] Determine caching strategy for intermediate results
- [ ] Design error handling and logging system

#### Implementation Questions
1. Transcript Processing:
   - What formats need to be supported initially?
   - Are there specific preprocessing requirements for each format?

2. CER Calculation:
   - Should we store alignments for all transcripts or only the best match?
   - What is the threshold for acceptable CER?

3. Performance:
   - Do we need parallel processing for multiple transcripts?
   - What should be cached and for how long?

## Installation & Usage

TBD - Will be added once the library structure is finalized.

## Contributing

TBD - Will be added once the initial implementation is complete.

## License

TBD - License needs to be determined.
