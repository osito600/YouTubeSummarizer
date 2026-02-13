import os
import re
import time
import sys
from urllib.parse import urlparse
from collections import Counter

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager

# --- Configuration ---
MAX_TRANSCRIPT_CHARS = 20000
DEFAULT_OUTPUT_FILE = "output.txt"
SUMMARY_RATIO = 0.3  # Extract 30% of sentences as summary


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

        # Scroll down to ensure info panel is visible
        driver.execute_script("window.scrollBy(0, 300);")
        time.sleep(1)

        # List of XPath selectors to try in order - Updated for current YouTube UI
        transcript_selectors = [
            # New selectors for current YouTube UI
            "//button[contains(translate(@aria-label, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'show transcript')]",
            "//yt-formatted-string[@role='button' or @role='menuitem'][contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'transcript')]",
            "//ytd-menu-service-item-renderer//yt-formatted-string[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'transcript')]",
            "//div[@role='button'][contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'transcript')]",
            "//button//span[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'transcript')]",
            # Legacy selectors as fallback
            "//button[contains(@aria-label, 'transcript')]",
            "//button[contains(., 'Transcript')]",
            # Try finding ANY element containing transcript text (case-insensitive)
            "//*[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'show transcript')]",
            "//*[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'transcript')]",
        ]

        transcript_found = False
        for selector in transcript_selectors:
            try:
                print(f"DEBUG: Trying selector: {selector}")
                elements = driver.find_elements(By.XPATH, selector)
                print(
                    f"DEBUG: Found {len(elements)} elements matching selector")
                for transcript_button in elements:
                    try:
                        if transcript_button.is_displayed():
                            print(
                                f"DEBUG: Found visible transcript button with selector: {selector}")
                            driver.execute_script(
                                "arguments[0].scrollIntoView(true);", transcript_button)
                            time.sleep(0.5)
                            driver.execute_script(
                                "arguments[0].click();", transcript_button)
                            transcript_found = True
                            break
                    except:
                        continue
                if transcript_found:
                    break
            except Exception as e:
                print(f"DEBUG: Selector '{selector}' failed: {str(e)[:100]}")
                continue

        if not transcript_found:
            print(
                "DEBUG: Could not find/click 'Show transcript' button with any selector.")
            print("DEBUG: Saving debugging information...")
            try:
                driver.save_screenshot("youtube_debug.png")
                print("DEBUG: Screenshot saved as 'youtube_debug.png'")

                # Save a portion of page HTML to inspect button structure
                try:
                    description_html = driver.execute_script(
                        "return document.getElementById('description-inline-expander').outerHTML;")
                    with open("youtube_description_html.txt", "w", encoding="utf-8") as f:
                        f.write(description_html)
                    print(
                        "DEBUG: Description HTML saved as 'youtube_description_html.txt'")
                except:
                    pass

                # Try to find any element with transcript and dump its HTML
                try:
                    transcript_elements = driver.find_elements(
                        By.XPATH, "//*[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'transcript')]")
                    if transcript_elements:
                        print(
                            f"DEBUG: Found {len(transcript_elements)} elements containing 'transcript' text")
                        with open("youtube_transcript_elements.txt", "w", encoding="utf-8") as f:
                            for idx, elem in enumerate(transcript_elements[:5]):
                                try:
                                    f.write(f"--- Element {idx} ---\n")
                                    f.write(f"Tag: {elem.tag_name}\n")
                                    f.write(
                                        f"Displayed: {elem.is_displayed()}\n")
                                    f.write(
                                        f"HTML: {elem.get_attribute('outerHTML')}\n\n")
                                except:
                                    pass
                        print(
                            "DEBUG: Transcript elements info saved as 'youtube_transcript_elements.txt'")
                except:
                    pass

            except:
                pass
            return None

        # 4. Extract text (ROBUST METHOD)
        print("DEBUG: Extracting text...")
        try:
            # Wait for transcript panel to appear and be interactive
            time.sleep(3)

            # Use JavaScript to extract transcript text - more reliable than XPath
            # YouTube's transcript panel uses various structures, so we'll try multiple approaches

            transcript_text = None

            # Approach 1: Try to find the transcript panel container and get all text
            script1 = """
            // Look for transcript segment containers
            let segments = document.querySelectorAll('[data-segment-index]');
            if (segments.length > 0) {
                let text = [];
                segments.forEach(seg => {
                    let content = seg.innerText.trim();
                    if (content && !content.match(/^\\d{1,2}:\\d{2}/)) {
                        text.push(content);
                    }
                });
                return text.join(' ');
            }
            
            // Fallback: look for any transcript container
            let container = document.querySelector('ytd-transcript-body-section-renderer') || 
                           document.querySelector('[role="presentation"] [role="tabpanel"]') ||
                           document.body;
            let allText = container.innerText;
            // Remove timestamps and clean up
            let lines = allText.split('\\n').filter(line => {
                line = line.trim();
                return line && !line.match(/^\\d{1,2}:\\d{2}(:\\d{2})?$/);
            });
            return lines.join(' ');
            """

            try:
                result = driver.execute_script(script1)
                if result and len(str(result).strip()) > 100:
                    transcript_text = result
                    print(
                        f"DEBUG: Successfully extracted {len(transcript_text)} characters using JS method 1")
            except Exception as e:
                print(f"DEBUG: JS method 1 failed: {e}")

            # Approach 2: Direct DOM search for transcript text
            if not transcript_text:
                script2 = """
                // Find all p tags and span tags in the transcript area
                let allElements = document.querySelectorAll('[role="tabpanel"] p, [role="tabpanel"] span, ytd-formatted-string');
                let texts = [];
                allElements.forEach(el => {
                    let text = el.innerText.trim();
                    if (text && text.length > 2 && !text.match(/^\\d{1,2}:\\d{2}/)) {
                        texts.push(text);
                    }
                });
                return texts.filter((t, i, arr) => arr.indexOf(t) === i).join(' ');
                """
                try:
                    result = driver.execute_script(script2)
                    if result and len(str(result).strip()) > 100:
                        transcript_text = result
                        print(
                            f"DEBUG: Successfully extracted {len(transcript_text)} characters using JS method 2")
                except Exception as e:
                    print(f"DEBUG: JS method 2 failed: {e}")

            # Approach 3: Brute force - get inner text of body and filter
            if not transcript_text:
                script3 = """
                // Get body text and hope transcript is there
                let bodyText = document.body.innerText;
                let lines = bodyText.split('\\n').filter(line => {
                    line = line.trim();
                    // Filter out common YouTube UI elements and metadata
                    return line && line.length > 3 && 
                           !line.match(/^\\d{1,2}:\\d{2}(:\\d{2})?$/) &&
                           !line.match(/views|subscribers|likes|Share|Subscribe|comments/i) &&
                           !line.includes('YouTube') && 
                           !line.includes('Visit site') &&
                           !line.includes('Premiered') &&
                           !line.includes('Reply') &&
                           !line.includes('views •') &&
                           !line.includes('views • ') &&
                           !line.match(/^[A-Z][a-z0-9_]*\\s+\\d+K.*views/);
                });
                // Get unique lines preserving order but removing duplicates
                let seen = new Set();
                let result = [];
                lines.forEach(line => {
                    if (!seen.has(line) && line.length < 500) {
                        seen.add(line);
                        result.push(line);
                    }
                });
                return result.join(' ');
                """
                try:
                    result = driver.execute_script(script3)
                    if result and len(str(result).strip()) > 100:
                        transcript_text = result
                        print(
                            f"DEBUG: Successfully extracted {len(transcript_text)} characters using JS method 3")
                except Exception as e:
                    print(f"DEBUG: JS method 3 failed: {e}")

            if transcript_text and len(str(transcript_text).strip()) > 50:
                # Clean up the text
                text_str = str(transcript_text).strip()
                # Remove multiple spaces
                text_str = " ".join(text_str.split())
                return text_str
            else:
                print("DEBUG: Could not extract transcript text - all methods failed")
                try:
                    driver.save_screenshot("youtube_extract_final_error.png")
                    print(
                        "DEBUG: Screenshot saved as 'youtube_extract_final_error.png'")
                except:
                    pass
                return None

        except Exception as e:
            print(f"DEBUG: Error in text extraction: {e}")
            try:
                driver.save_screenshot("youtube_extract_error.png")
                print("DEBUG: Screenshot saved as 'youtube_extract_error.png'")
            except:
                pass
            return None

    except Exception as e:
        print(f"An error occurred with Selenium: {e}")
        return None
    finally:
        driver.quit()


def summarize_text(text):
    """
    Extractive summarization using sentence scoring based on word frequency.
    No API calls needed - runs entirely locally.
    """
    if not text:
        return None

    if len(text) > MAX_TRANSCRIPT_CHARS:
        print(
            f"Note: Transcript is {len(text)} chars. Using first {MAX_TRANSCRIPT_CHARS} chars for summary.")
        text = text[:MAX_TRANSCRIPT_CHARS]

    try:
        # Split into sentences
        sentences = re.split(r'(?<=[.!?])\s+', text.strip())
        if len(sentences) == 0:
            return text

        # If very short, return as-is
        if len(sentences) <= 3:
            return "\n".join(s.strip() for s in sentences if s.strip())

        # Tokenize and filter stopwords
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'is', 'are', 'was', 'were', 'be', 'been',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
            'should', 'may', 'might', 'must', 'can', 'that', 'this', 'it', 'i',
            'you', 'he', 'she', 'we', 'they', 'what', 'which', 'who', 'when',
            'where', 'why', 'how', 'as', 'if', 'so', 'no', 'not', 'up', 'out',
            'just', 'like', 'very', 'more', 'into', 'through', 'during', 'before'
        }

        # Score sentences based on word frequency
        word_freq = Counter()
        for sentence in sentences:
            words = re.findall(r'\w+', sentence.lower())
            for word in words:
                if word not in stop_words and len(word) > 2:
                    word_freq[word] += 1

        # Score each sentence
        sentence_scores = {}
        for i, sentence in enumerate(sentences):
            words = re.findall(r'\w+', sentence.lower())
            score = sum(word_freq[word]
                        for word in words if word not in stop_words)
            sentence_scores[i] = score

        # Select top sentences (maintain original order)
        num_sentences = max(1, int(len(sentences) * SUMMARY_RATIO))
        top_sentence_indices = sorted(
            sorted(sentence_scores.items(), key=lambda x: x[1], reverse=True)[
                :num_sentences],
            key=lambda x: x[0]  # Sort back to original order
        )

        # Build summary with proper formatting
        summary_sentences = [sentences[i].strip()
                             for i, _ in top_sentence_indices if sentences[i].strip()]
        # Create formatted output with proper line breaks
        formatted_summary = "\n".join(summary_sentences)
        return formatted_summary.strip()

    except Exception as e:
        print(f"Error during summarization: {e}")
        return None


def save_to_file(summary, filename=DEFAULT_OUTPUT_FILE):
    try:
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        formatted_output = f"""
{'='*70}
YOUTUBE VIDEO SUMMARY
{'='*70}

Generated: {timestamp}

SUMMARY:
{'-'*70}

{summary}

{'-'*70}
End of Summary
{'='*70}
"""

        with open(filename, "w", encoding="utf-8") as f:
            f.write(formatted_output)
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
