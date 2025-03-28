#!/usr/bin/env python3

import os
import sys
import time
import json
import requests
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

# === Configuration ===
TARGET_FILE = "chat.md"

POLL_INTERVAL = 2  # Check every 2 seconds

# Best practice: Load API key from environment variable, don't hardcode
API_KEY = os.getenv("GEMINI_API_KEY")

MODEL = "gemini-2.0-flash" # Use a recommended model, adjust if needed
# gemini-2.5-pro-exp-03-25

SYSTEM_PROMPT = """
You are Gemini. You are a helpful assistant.
Stay concise and clear in your responses. Explain complicated details simply when needed.
Use $ for inline math expressions, and $$ for math blocks. This is Markdown.
"""
# === End Configuration ===

# === Logging Function ===
def log(message):
    """Prints a timestamped log message."""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {message}")

# === Gemini API Call ===
def call_gemini_api(latest_input: str) -> str | None:
    """
    Calls the Google Gemini API with the provided text content.

    Args:
        latest_input: The new text content from the file.

    Returns:
        The text response from the API, or None if an error occurs.
    """
    if not API_KEY or API_KEY == "YOUR_DEFAULT_API_KEY_HERE":
        log("ERROR: API_KEY environment variable is not set or is using the default placeholder.")
        sys.stderr.write("ERROR: API_KEY environment variable is not set or is using the default placeholder.\n")
        return None

    if not latest_input:
        log("WARNING: Content provided to call_gemini_api is empty.")
        # sys.stderr.write("WARNING: Content provided to call_gemini_api is empty.\n") # Optional stderr warning
        return "" # Return empty string for empty input, consistent with Bash handling

    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={API_KEY}"

    headers = {
        "Content-Type": "application/json"
    }

    # Construct JSON Payload (Python handles JSON escaping)
    payload = {
        "systemInstruction": {
            "role": "user",
            "parts": [ { "text": SYSTEM_PROMPT } ]
        },
        "contents": [
            {
                "role": "user",
                "parts": [{"text": latest_input}]
            }
        ],
        "generationConfig": {
            "temperature": 1,
            "topK": 40,
            "topP": 0.95,
            "maxOutputTokens": 8192,
            "responseMimeType": "text/plain" # Request plain text, but API often still wraps it
        }
    }

    try:
        log(f"Sending request to Gemini model: {MODEL}")
        response = requests.post(api_url, headers=headers, json=payload, timeout=60) # Added timeout
        response.raise_for_status()  # Raises HTTPError for bad responses (4xx or 5xx)

        # Attempt to parse JSON, even if text/plain was requested, as API often wraps it
        try:
            response_data = response.json()
            # Navigate the expected structure
            candidates = response_data.get("candidates", [])
            if candidates:
                content = candidates[0].get("content", {})
                parts = content.get("parts", [])
                if parts:
                    text = parts[0].get("text")
                    if text is not None:
                        # Python's json loading handles basic escapes like \n
                        return text
            # If parsing failed to find text, log the structure
            log(f"WARNING: Could not find text in expected JSON structure. Response: {response.text[:500]}...") # Log snippet
            # Fallback: Maybe it's truly plain text (less common for generateContent)
            if "text/plain" in response.headers.get("Content-Type", "").lower() and not response.text.strip().startswith('{'):
                 log("Treating response as raw plain text.")
                 return response.text
            else:
                 log(f"ERROR: Unexpected API response format. Cannot extract text.")
                 sys.stderr.write(f"ERROR: Unexpected API response format. Raw response: {response.text}\n")
                 return None


        except json.JSONDecodeError:
            # Handle cases where response isn't valid JSON (e.g., truly plain text or error message)
             if "text/plain" in response.headers.get("Content-Type", "").lower():
                 log("Received non-JSON response, treating as plain text.")
                 return response.text # Return raw text if parsing fails but content-type is plain
             else:
                 log(f"ERROR: Failed to decode JSON response. Status: {response.status_code}, Response: {response.text[:500]}...")
                 sys.stderr.write(f"ERROR: Non-JSON response received. Status: {response.status_code}. Body: {response.text}\n")
                 return None

    except requests.exceptions.RequestException as e:
        log(f"ERROR: API request failed: {e}")
        sys.stderr.write(f"ERROR: API request failed: {e}\n")
        # If the error has a response body (like a 400 Bad Request with details), show it
        if hasattr(e, 'response') and e.response is not None:
             sys.stderr.write(f"API Response Body on Error: {e.response.text}\n")
        return None

    except Exception as e: # Catch any other unexpected errors during API call/parsing
        log(f"ERROR: An unexpected error occurred during API call: {e}")
        sys.stderr.write(f"ERROR: An unexpected error occurred during API call: {e}\n")
        return None


# === Main Script Logic ===
def main():
    # Check if target file exists
    if not os.path.exists(TARGET_FILE):
        log(f"Error: Target file '{TARGET_FILE}' not found. Please create it.")
        sys.exit(1)

    log(f"Watching '{TARGET_FILE}' for modifications (polling every {POLL_INTERVAL}s)...")

    try:
        last_mod_time = os.path.getmtime(TARGET_FILE)
        with open(TARGET_FILE, 'r', encoding='utf-8') as f:
            last_content = f.read()
    except Exception as e:
        log(f"Error reading initial state of '{TARGET_FILE}': {e}")
        sys.exit(1)

    writing_in_progress = False

    while True:
        try:
            # Check if we are currently writing - skip check if so
            if writing_in_progress:
                time.sleep(POLL_INTERVAL)
                continue

            # Check for file existence and modification time
            if not os.path.exists(TARGET_FILE):
                log(f"Warning: Target file '{TARGET_FILE}' disappeared. Stopping watch.")
                break # Or sys.exit(1) depending on desired behavior

            current_mod_time = os.path.getmtime(TARGET_FILE)

            # Check if modification time has changed
            if current_mod_time != last_mod_time:
                log(f"Modification detected in '{TARGET_FILE}'.")

                # Read current content safely
                try:
                    with open(TARGET_FILE, 'r', encoding='utf-8') as f:
                        current_content = f.read()
                except Exception as e:
                    log(f"Error reading modified file '{TARGET_FILE}': {e}. Skipping this change.")
                    last_mod_time = current_mod_time # Update time to avoid re-triggering on the failed read
                    time.sleep(POLL_INTERVAL)
                    continue

                # Check if content actually changed
                if current_content != last_content:
                    if not current_content.strip(): # Check if file is effectively empty
                        log("File content is empty, skipping API call.")
                        last_mod_time = current_mod_time
                        last_content = current_content
                    else:
                        log("Content changed. Sending to Gemini...")

                        current_content += f"\n---\n**{MODEL}:**\n\n"

                        api_response = call_gemini_api(current_content)

                        # Check response carefully (None indicates error, "" is valid empty response)
                        if api_response is None:
                            log("Error: Received None (error state) from Gemini API. Check logs.")
                            # Update state to avoid re-processing the same failed state immediately
                            last_mod_time = os.path.getmtime(TARGET_FILE) # Re-read time
                            try:
                                with open(TARGET_FILE, 'r', encoding='utf-8') as f:
                                    last_content = f.read() # Re-read content
                            except Exception as e:
                                 log(f"Error re-reading file after API error: {e}")
                                 # Decide how to handle this - maybe stop? For now, just log.
                        else:
                            log("Received response from Gemini. Writing back to file...")
                            writing_in_progress = True
                            try:
                                new_content = current_content + api_response + "\n\n---\n\n"
                                with open(TARGET_FILE, 'w', encoding='utf-8') as f:
                                    f.write(new_content)

                                # Update last known state *after* successful write
                                last_mod_time = os.path.getmtime(TARGET_FILE)
                                last_content = new_content
                                log("Update complete. Resuming watch...")

                            except IOError as e:
                                log(f"Error writing response back to '{TARGET_FILE}': {e}")
                                # If write failed, don't update last_content/last_mod_time to retry
                            finally:
                                # IMPORTANT: Always unset the flag
                                writing_in_progress = False
                else:
                    log("Timestamp changed but content identical, skipping API call.")
                    last_mod_time = current_mod_time # Only update timestamp

            # Wait before checking again
            time.sleep(POLL_INTERVAL)

        except FileNotFoundError:
             log(f"Warning: Target file '{TARGET_FILE}' disappeared during check. Stopping watch.")
             break # Exit loop if file is gone
        except Exception as e:
             log(f"An unexpected error occurred in the main loop: {e}")
             log("Attempting to recover and continue watching...")
             # Reset state cautiously or decide to exit
             try: # Try to reset state to avoid rapid error loops
                 last_mod_time = os.path.getmtime(TARGET_FILE)
                 with open(TARGET_FILE, 'r', encoding='utf-8') as f:
                     last_content = f.read()
             except Exception as reset_e:
                 log(f"Failed to reset state after error: {reset_e}. Stopping.")
                 sys.exit(1)
             time.sleep(POLL_INTERVAL * 2) # Wait a bit longer after an error


if __name__ == "__main__":
    main()
