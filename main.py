import os
import re
import time
import sys
from urllib.parse import urlparse
from openai import OpenAI

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager

# --- Configuration ---
API_KEY = os.environ.get("OPENAI_API_KEY")
if not API_KEY:
    print("ERROR: OPENAI_API_KEY environment variable is not set. Exiting.")
    sys.exit(1)

client = OpenAI(api_key=API_KEY)

# Configuration constants
MAX_TRANSCRIPT_CHARS = 20000
DEFAULT_MODEL = "gpt-4-turbo"
DEFAULT_OUTPUT_FILE = "output.txt"


def get_transcript_selenium(url):
    """
    Fetches the transcript for a given video URL using Selenium.
    """
    # Setup Selenium
    options = webdriver.ChromeOptions()
    options.add_argument("--log-level=3")
    options.add_argument("--start-maximized")
    # Disable extensions to speed up
    options.add_argument("--disable-extensions")
    # Disable GPU to prevent rendering hangs
    options.add_argument("--disable-gpu")
    options.page_load_strategy = 'eager'

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    # FORCE TIMEOUT: Don't wait more than 15 seconds for the page to load
    driver.set_page_load_timeout(15)

    try:
        print("DEBUG: Loading video page...")
        try:
            driver.get(url)
        except TimeoutException:
            print(
                "DEBUG: Page load timed out (this is expected for YouTube). Continuing anyway...")
            driver.execute_script("window.stop();")  # Force stop loading

        time.sleep(2)  # Give it a moment to settle
        wait = WebDriverWait(driver, 10)

        # 1. Handle "Accept Cookies" popup
        try:
            cookie_button = driver.find_element(
                By.XPATH, '//button[contains(@aria-label, "Accept") or contains(@aria-label, "Reject")]')
            if cookie_button.is_displayed():
                cookie_button.click()
                time.sleep(1)
        except Exception as e:
            print(f"DEBUG: Cookie popup not found or already dismissed: {e}")

        # 2. Expand the description
        print("DEBUG: Expanding description...")
        try:
            # We look for the ID "expand" which is the button container
            expand_button = wait.until(
                EC.presence_of_element_located((By.ID, "expand")))
            # Scroll to it
            driver.execute_script(
                "arguments[0].scrollIntoView(true);", expand_button)
            time.sleep(1)
            # Click it
            driver.execute_script("arguments[0].click();", expand_button)
            time.sleep(1)
        except Exception as e:
            print(f"DEBUG: Failed to click expand button: {e}")

        # 3. Click "Show transcript"
        print("DEBUG: Clicking 'Show transcript'...")

        # List of XPath selectors to try in order
        transcript_selectors = [
            "//button[contains(@aria-label, 'Show transcript')]",
            "//button[contains(., 'transcript')]",
            "//yt-formatted-string[contains(text(), 'transcript')]",
            "//*[contains(@aria-label, 'transcript')]",
            "//button[@aria-label='Show transcript']",
            "//ytd-menu-renderer//button[contains(@aria-label, 'transcript')]",
        ]

        transcript_found = False
        for selector in transcript_selectors:
            try:
                print(f"DEBUG: Trying selector: {selector}")
                transcript_button = driver.find_element(By.XPATH, selector)
                if transcript_button and transcript_button.is_displayed():
                    print(
                        f"DEBUG: Found transcript button with selector: {selector}")
                    driver.execute_script(
                        "arguments[0].scrollIntoView(true);", transcript_button)
                    time.sleep(1)
                    driver.execute_script(
                        "arguments[0].click();", transcript_button)
                    transcript_found = True
                    break
            except Exception as e:
                print(f"DEBUG: Selector '{selector}' failed: {str(e)[:100]}")
                continue

        if not transcript_found:
            print(
                "DEBUG: Could not find/click 'Show transcript' button with any selector.")
            print("DEBUG: Attempting to save page screenshot for debugging...")
            try:
                driver.save_screenshot("youtube_debug.png")
                print("DEBUG: Screenshot saved as 'youtube_debug.png'")
            except:
                pass
            return None

        # 4. Extract text (BULK METHOD)
        print("DEBUG: Extracting text...")
        try:
            # Wait for the main container that holds all segments
            # It usually has the ID 'segments-container'
            container = wait.until(EC.presence_of_element_located(
                (By.ID, "segments-container")))

            # Grab ALL text inside it at once
            full_raw_text = container.get_attribute("innerText")

            print(
                f"DEBUG: Successfully grabbed {len(full_raw_text)} characters of raw text.")

            # Process the text to remove timestamps
            lines = full_raw_text.split('\n')
            clean_lines = []

            for line in lines:
                line = line.strip()
                if not line:
                    continue
                # Skip timestamps
                if re.match(r'^\d+:\d+$', line):
                    continue

                clean_lines.append(line)

            return " ".join(clean_lines)

        except Exception as e:
            print(f"DEBUG: Error extracting text from panel: {e}")
            return None

    except Exception as e:
        print(f"An error occurred with Selenium: {e}")
        return None
    finally:
        driver.quit()


def summarize_text(text, model=DEFAULT_MODEL):
    if not text:
        return None

    if len(text) > MAX_TRANSCRIPT_CHARS:
        print(
            f"Warning: Transcript is long ({len(text)} chars). Truncating to {MAX_TRANSCRIPT_CHARS}.")
        text = text[:MAX_TRANSCRIPT_CHARS]

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that summarizes YouTube videos. Provide a clear, concise summary with key points."},
                {"role": "user", "content": f"Please provide a concise summary of the following video transcript:\n\n{text}"}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error during summarization: {e}")
        return None


def save_to_file(summary, filename=DEFAULT_OUTPUT_FILE):
    try:
        with open(filename, "w", encoding="utf-8") as f:
            f.write(summary)
        print(f"Summary successfully saved to {filename}")
    except Exception as e:
        print(f"Error saving file: {e}")


def is_valid_youtube_url(url):
    """Validate that the URL is a YouTube video URL."""
    try:
        parsed = urlparse(url)
        # Check for youtube.com or youtu.be domains
        if 'youtube.com' in parsed.netloc or 'youtu.be' in parsed.netloc:
            return True
        return False
    except:
        return False


def main():
    print("--- YouTube Video Summarizer (Selenium Edition v7 - Improved) ---")
    url = input("Enter YouTube URL: ").strip()

    # Validate URL
    if not url:
        print("ERROR: URL cannot be empty.")
        return

    if not is_valid_youtube_url(url):
        print(
            "ERROR: Invalid YouTube URL. Please enter a valid youtube.com or youtu.be link.")
        return

    try:
        print("Fetching transcript...")
        transcript = get_transcript_selenium(url)

        if transcript:
            print("Transcript fetched. Summarizing...")
            summary = summarize_text(transcript)

            if summary:
                print("\n--- Summary ---")
                print(summary)
                print("---------------")
                save_to_file(summary)
            else:
                print("Failed to generate summary.")
        else:
            print("Could not retrieve transcript.")

    except Exception as e:
        print(f"An unexpected error occurred: {e}")


if __name__ == "__main__":
    main()
