# Serve Command Documentation

The `serve` command starts a FastAPI web server that provides both a web interface and HTTP API for text-to-speech generation.

## Basic Usage

```bash
uvx pocket-tts serve
# or if installed manually:
pocket-tts serve
```

This starts a server on `http://localhost:8000` with the default voice model.

## Command Options

- `--voice VOICE`: Path to voice prompt audio file (voice to clone) (default: "hf://kyutai/tts-voices/alba-mackenna/casual.wav")
- `--host HOST`: Host to bind to (default: "localhost")
- `--port PORT`: Port to bind to (default: 8000)
- `--reload`: Enable auto-reload for development

## Examples

### Basic Server

```bash
# Start with default settings
pocket-tts serve

# Custom host and port
pocket-tts serve --host "localhost" --port 8080
```

### Custom Voice

```bash
# Use different voice
pocket-tts serve --default-voice "hf://kyutai/tts-voices/jessica-jian/casual.wav"

# Use local voice file
pocket-tts serve --default-voice "./my_voice.wav"
```

## Web Interface

Once the server is running, navigate to `http://localhost:8000` to access the web interface.

### Timeline Mixer (Web UI)
The web UI includes a timeline-based mixer at the bottom that lets you:
- Trim each generated TTS segment or imported music file with draggable in/out handles
- Drag clips horizontally to position them on a timeline (supports overlaps for real mixing)
- Import an external music/audio file via the “Add Music” button
- Render the final mix to MP3 entirely client-side (no server changes needed)

Basic workflow:
1) Add one or more segments and click Generate (or Generate & Play)
2) Each generated segment appears as a clip in the Timeline Mixer
3) Optionally import a background track using “Add Music”
4) Drag clips to set timing; drag handles to trim starts/ends
5) Click “Render Mix (MP3)” to export a mixed MP3

Note: Mixing is currently mono for consistency and simplicity. External audio is downmixed and resampled client-side to match the model’s sample rate.

For more advanced usage, see the [Python API documentation](python-api.md) for direct integration with the TTS model.