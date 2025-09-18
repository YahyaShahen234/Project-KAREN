# Project K.A.R.E.N.

K.A.R.E.N. is a voice assistant modeled after Karen, Plankton's sarcastic computer wife from SpongeBob SquarePants. This project provides a modular framework for building a voice assistant with pluggable providers for Speech-to-Text (STT), Large Language Models (LLM), and Text-to-Speech (TTS).

This implementation uses OpenAI for all three services.

## Features

- **Wake Word Detection:** Listens for the wake word "Karen".
- **Speech-to-Text:** Transcribes your voice commands.
- **LLM Integration:** Sends your command to a large language model to generate a response.
- **Text-to-Speech:** Speaks the response out loud.
- **Sarcastic Personality:** The system prompt is engineered to give the assistant a witty, bored, and sarcastic personality, just like the real Karen.

## Getting Started

### Prerequisites

- Python 3.11 or later
- An OpenAI API key

### Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/example/project-karen.git
    cd project-karen
    ```

2.  **Create a virtual environment:**
    ```bash
    python -m venv .venv
    source .venv/bin/activate
    ```

3.  **Install the dependencies:**
    ```bash
    pip install .
    ```

### Configuration

1.  **Create a configuration file:**
    -   In the root of the project, you will find a file named `karen.env.example`.
    -   Make a copy of this file and name it `karen.env`.

2.  **Edit the configuration file:**
    -   Open `karen.env` in a text editor.
    -   Set the `STT_PROVIDER`, `LLM_PROVIDER`, and `TTS_PROVIDER` to `openai`.
    -   Add your OpenAI API key to the `OPENAI_API_KEY` field.

    ```
    # karen.env
    STT_PROVIDER="openai"
    LLM_PROVIDER="openai"
    TTS_PROVIDER="openai"
    OPENAI_API_KEY="sk-..."
    ```

### Running the Application

Once you have installed the dependencies and configured your API key, you can run the application with the following command:

```bash
python -m karen.main
```

The application will start and listen for the wake word "Karen".

## How it Works

The application is composed of several modules:

-   `main.py`: The main entry point of the application.
-   `wake.py`: Handles wake word detection (currently a placeholder).
-   `audio_io.py`: Manages microphone input and speaker output.
-   `stt.py`: Converts speech to text.
-   `llm.py`: Generates a response using a large language model.
-   `tts.py`: Converts text to speech.
-   `config.py`: Manages the application's configuration.

The application uses an `asyncio` event loop to handle the various I/O operations (audio, network) concurrently.
