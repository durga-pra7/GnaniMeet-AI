# GnaniMeet AI — Meeting Summarizer Starter

A Flask web app starter for the Gnani AI build challenge. The intended pipeline is:

1. Upload a meeting audio recording.
2. Transcribe it with Gnani Prisma.
3. Review/edit the transcript.
4. Generate meeting summary, key points, decisions, action items, and open questions with a reasoning model (Evon-compatible endpoint).
5. Copy or download Markdown meeting notes.

## Requirements

- Python 3.10+
- VS Code
- Gnani Prisma API key from the Gnani console
- A hosted or locally served OpenAI-compatible inference endpoint for Evon

> Evon is a 30B model. Running it locally requires suitable GPU/server resources. Do not assume it will run on a typical student laptop. For a local vLLM setup, see the official Evon Hugging Face model card.

## Setup on Windows

Open this folder in VS Code, then in the integrated terminal:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` and add your credentials and endpoint settings.

Run:

```powershell
python app.py
```

Open http://127.0.0.1:5000

## API configuration

### Prisma

The starter uses `https://api.vachana.ai/stt/v3` as the default Prisma endpoint and sends a multipart audio field named `audio_file`, with `model` and `mode` form values. Gnani's published API pages can change; verify the exact endpoint, authentication scheme, multipart field names, and response schema from your account's current API docs. Update `prisma_transcribe()` in `app.py` if the console docs specify a different shape.

Variables:
- `GNANI_API_KEY`
- `PRISMA_URL`
- `PRISMA_MODEL`
- `PRISMA_MODE`

### Evon / reasoning model

The summarizer sends an OpenAI-compatible chat-completions request to `EVON_BASE_URL`.

For example, if you have vLLM running at localhost port 8000:
- `EVON_BASE_URL=http://localhost:8000/v1/chat/completions`
- `EVON_MODEL=gnani/gnani-evon-v3.3-30B-A3B`

An authenticated hosted endpoint can be configured with `EVON_API_KEY`. Confirm its URL and model name with the hosting provider.

## Demo without API credentials

You can show the interface and paste a transcript, but generation requires a configured reasoning endpoint. Transcription requires the Gnani Prisma API key. Do not represent mock output as actual Gnani model output.

## Privacy and safety

- The app deletes the uploaded audio file after the transcription request completes.
- This is a starter app; it does not implement user authentication, database storage, or production-grade privacy controls.
- Use recordings only when you have permission from participants.
- Review AI-generated notes for accuracy before sending them to others.
- Never commit `.env` or API keys to GitHub.

## Suggested demo

Use a consented, short sample meeting recording:
- Upload audio and click **Transcribe with Prisma**
- Correct the transcript if needed
- Click **Generate meeting notes**
- Show summary, key points, decisions, action items
- Download the `.md` notes
- Mention that Prisma is the STT model and Evon is the reasoning model

## Submission write-up

**Problem:** Meeting notes are time-consuming to create, and decisions or action items can be missed.

**Solution:** GnaniMeet AI turns meeting recordings into editable transcripts and structured notes using Gnani Prisma and a reasoning model.

**Target users:** Project teams, startups, enterprise teams, faculty, and student groups.

**Core models:** Gnani Prisma (speech-to-text); Gnani Evon (reasoning / structured summarization).

**Impact:** Reduces manual note-taking and makes action items easier to review. Do not claim measured time savings unless you test and quantify them.


## API configuration notes

- `GNANI_API_KEY` is used for the Prisma speech-to-text request.
- `EVON_BASE_URL` must point to an actual OpenAI-compatible chat-completions endpoint. The starter does not launch an Evon model server itself.
- `EVON_API_KEY` is optional only if the configured endpoint does not require authentication.
- Do not share your `.env` file or API keys in screenshots, GitHub, or chat.


## AI service configuration

- **Prisma** is used for audio transcription. Set `GNANI_API_KEY` with your Prisma speech-to-text key.
- **Groq** is used for transcript summarization. Set `GROQ_API_KEY` with a key from your Groq Console.
- `GROQ_BASE_URL` and `GROQ_MODEL` can be changed in `.env` if your account uses another supported endpoint/model.
- Never commit or share your `.env` file. Keep API keys private.
