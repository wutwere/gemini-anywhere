# Gemini Chatbot

This project provides a simple way to interact with the Gemini chatbot using a local Markdown file. This is built primarily for my convenience, because I like to stay in the terminal with Neovim.

## Prerequisites

*   Python 3.6+
    - dotenv, requests installed via pip
*   A Gemini API key from Google AI Studio.

## Setup

1.  **Create a `.env` file:**

    In the project directory, create a file named `.env` and add your Gemini API key:

    ```
    GEMINI_API_KEY=YOUR_API_KEY
    ```

2.  **Run the Gemini script in the background:**

    Open your terminal and execute the following command:

    ```bash
    python3 gemini.py
    ```

    This will start the `gemini.py` script in the background. It reads and writes to `chat.md`.

## Usage

1.  **Edit `chat.md`:**

    Open the `chat.md` file in your favorite text editor.  Start typing your message at the end of the file. Save the file. The `gemini.py` script will detect the changes, send your message to the Gemini API, and append the chatbot's response to the file.

2.  **Continue the conversation:**

    Keep editing `chat.md` to continue the conversation.  Each time you save the file, the script will process your new message and update the file with the chatbot's reply.

3. **Clear the chat:**

    Simply remove all of the text inside `chat.md`, and a new conversation will be started with whatever you write.
