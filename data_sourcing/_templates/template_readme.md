# [Country] Parliament Session Scraper

[Brief description of what this scraper does and what type of data it collects]

## 1. Website Structure and Data Organization

### Content Hierarchy
[Describe how the parliament website organizes its content. Include:
- Main organizational units (e.g., terms, convocations, sessions, etc.)
- How sessions are grouped and accessed
- Any special categorization or filtering systems]

### Access Points
[List the main URLs and patterns used to access different types of content:
- Base URLs for different sections
- URL patterns for sessions, terms, etc.
- Any special access requirements or authentication]

## 2. Data Sources

### Media Content
[Describe the source of video/audio content:
- Platform hosting the media (e.g., YouTube, custom video player, etc.)
- File formats supported
- How media files are organized and accessed
- Any special requirements for accessing media]

### Transcripts
[Describe the source of transcripts:
- Format of transcripts (e.g., HTML, PDF, DOCX, etc.)
- How transcripts are organized
- Access method and any special requirements
- Any interactive elements that need to be handled]

## 3. Technical Implementation

### Protection Measures
[Document implemented protection against blocking:
- Rate limiting
- Request delays
- Authentication handling
- Any special bypass mechanisms]

## 4. Output Format

### Data Structure
[Describe the structure of output files:
- CSV formats
- Column descriptions
- Data types and formats]

### ID Generation
[Explain the ID generation scheme:
- Format: `[prefix]_[term]_[session]_[date]`
- Components explanation
- Examples]

### Output Files
[List all generated files:
- Media links file
- Transcript links file
- Merged data file
- Any log files]

## 5. Data Processing Pipeline

### Collection Process
[Describe the three main stages:
1. Media collection
2. Transcript collection
3. Data merging]

### Error Handling
[Document how the system handles:
- Missing data
- Failed requests
- Incomplete sessions
- Data mismatches]

### Data Quality
[Explain measures taken to ensure data quality:
- Validation steps
- Consistency checks
- Error logging]

## Known Issues

[List any known limitations or issues:
- Missing data periods
- Access restrictions
- Technical limitations
- Edge cases]

## Usage

[Basic instructions for running the scraper]

## Notes

[Any additional important information]