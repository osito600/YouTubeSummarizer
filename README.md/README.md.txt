# YouTube Video Summarizer

A robust Python tool that automatically extracts transcripts from YouTube videos and generates concise summaries using OpenAI's GPT-4.

## Features

- **Selenium Automation**: Uses a real browser instance to navigate YouTube, handling dynamic content, popups, and "Show Transcript" buttons that standard scrapers miss.
- **AI-Powered Summaries**: Leverages OpenAI's `gpt-4-turbo` model to understand and summarize long video content.
- **Robust Error Handling**: Includes logic to handle timeouts, cookie popups, and different YouTube UI layouts.
- **Input Validation**: Ensures only valid YouTube URLs are processed.

## Prerequisites

- Python 3.8+
- Google Chrome installed
- An OpenAI API Key

## Installation

1. Clone the repository:
   