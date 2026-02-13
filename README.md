# YouTube Summarizer

A robust Python tool that automatically extracts transcripts from YouTube videos and generates concise summaries using **local extractive summarization** (no API keys needed).

## Features

- **Selenium Automation**: Uses a real browser instance to navigate YouTube, handling dynamic content, popups, and "Show Transcript" buttons.
- **Local Summarization**: Uses sentence scoring based on word frequency to extract key points - runs entirely on your machine.
- **No API Dependencies**: No need for OpenAI, Claude, or any external API - completely free to use.
- **Robust Error Handling**: Filters YouTube UI elements (comments, recommendations, metadata) from transcripts.
- **Professional Output**: Generates formatted summaries with timestamps.
- **Input Validation**: Ensures only valid YouTube URLs are processed.

## Prerequisites

- Python 3.8+
- Google Chrome installed
- No API keys or external services required

## Installation

1. Clone the repository:


2. Install the required dependencies:

     pip install -r requirements.txt
                  or    
     python -m pip install -r requirements.txt


## Configuration

No configuration needed! The script works out of the box. 

**Optional**: Adjust the `SUMMARY_RATIO` in `main.py` to control summary length:
- `0.3` = 30% of sentences (default, most concise)
- `0.5` = 50% of sentences (more detailed)


## Usage

Run the script:

```powershell
python main.py
```

1. Paste the YouTube URL when prompted.
2. The script will launch a browser window to fetch the transcript.
3. The summary will be printed to the console and saved to `output.txt`.

## How It Works

1. **Transcript Extraction**: Uses Selenium to navigate YouTube, click the "Show Transcript" button, and extract the full video transcript using JavaScript.
2. **Filtering**: Removes timestamps, comments, recommendations, and other UI elements to isolate the actual video content.
3. **Summarization**: Scores each sentence based on word frequency (ignoring common stopwords) and extracts the most important sentences.
4. **Output**: Generates a professionally formatted summary with timestamp and saves to `output.txt`.

## Dependencies

- `selenium`: Browser automation for YouTube navigation
- `webdriver-manager`: Automatic Chrome driver management
- `Counter` (Python built-in): For word frequency analysis

   
   