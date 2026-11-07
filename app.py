import os
import json
import tempfile
import requests

from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv
from pydub import AudioSegment

load_dotenv()

app = Flask(__name__)

# --------------------------------------------------
# Configuration
# --------------------------------------------------

app.config["MAX_CONTENT_LENGTH"] = 500 * 1024 * 1024

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

PRISMA_URL = "https://api.vachana.ai/stt/v3"
GNANI_API_KEY = os.getenv("GNANI_API_KEY")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv(
    "GROQ_MODEL",
    "llama-3.3-70b-versatile"
)

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

# --------------------------------------------------
# Prisma: Transcribe one audio chunk
# --------------------------------------------------

def prisma_transcribe_chunk(audio_path):
    """
    Send one audio chunk to Prisma Speech-to-Text API.
    Each chunk must be shorter than 30 seconds.
    """

    if not GNANI_API_KEY:
        raise ValueError("GNANI_API_KEY is missing in the .env file.")

    headers = {
        "X-API-Key-ID": GNANI_API_KEY
    }

    data = {
        "format": "transcribe",
        "language_code": "en-IN"
    }

    with open(audio_path, "rb") as audio_file:
        files = {
            "audio_file": (
                os.path.basename(audio_path),
                audio_file,
                "audio/wav"
            )
        }

        response = requests.post(
            PRISMA_URL,
            headers=headers,
            data=data,
            files=files,
            timeout=180
        )

    if not response.ok:
        raise RuntimeError(
            f"Prisma API Error ({response.status}): {response.text}"
        )

    result = response.json()

    # Handle common Prisma response formats
    if isinstance(result, dict):
        transcript = (
            result.get("transcript")
            or result.get("text")
            or result.get("transcription")
        )

        if transcript:
            return transcript

        # Some APIs return nested result objects
        nested_result = result.get("result")

        if isinstance(nested_result, dict):
            transcript = (
                nested_result.get("transcript")
                or nested_result.get("text")
            )

            if transcript:
                return transcript

    raise RuntimeError(
        f"Could not find transcript in Prisma response: {result}"
    )


# --------------------------------------------------
# Prisma: Split long audio into 25-second chunks
# --------------------------------------------------

def prisma_transcribe(audio_path):
    """
    Split audio into 25-second WAV chunks and transcribe
    them sequentially to avoid the 30-second API limit.
    """

    audio = AudioSegment.from_file(audio_path)

    duration_ms = len(audio)
    chunk_duration_ms = 25 * 1000

    transcripts = []

    for start_ms in range(0, duration_ms, chunk_duration_ms):
        end_ms = min(
            start_ms + chunk_duration_ms,
            duration_ms
        )

        chunk = audio[start_ms:end_ms]

        temp_chunk_path = None

        try:
            with tempfile.NamedTemporaryFile(
                suffix=".wav",
                dir=UPLOAD_FOLDER,
                delete=False
            ) as temp_file:
                temp_chunk_path = temp_file.name

            chunk.export(
                temp_chunk_path,
                format="wav"
            )

            print(
                f"Transcribing chunk "
                f"{start_ms // 1000}s - {end_ms // 1000}s"
            )

            chunk_transcript = prisma_transcribe_chunk(
                temp_chunk_path
            )

            if chunk_transcript:
                transcripts.append(chunk_transcript)

        finally:
            if (
                temp_chunk_path
                and os.path.exists(temp_chunk_path)
            ):
                os.remove(temp_chunk_path)

    return " ".join(transcripts).strip()


# --------------------------------------------------
# Groq: Summarize transcript
# --------------------------------------------------

def groq_summarize(transcript):
    """
    Generate meeting notes from the transcript using Groq.
    """

    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY is missing in the .env file.")

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    system_prompt = """
You are an AI meeting assistant.

Analyze the meeting transcript and return valid JSON only.
Do not include Markdown code fences.

Use this exact JSON structure:

{
  "summary": "Short meeting summary",
  "key_points": ["Important point 1", "Important point 2"],
  "decisions": ["Decision 1"],
  "action_items": [
    {
      "task": "Task description",
      "owner": "Person responsible, or Not specified",
      "deadline": "Deadline, or Not specified"
    }
  ],
  "open_questions": ["Unresolved question 1"]
}

Do not invent information that is not present in the transcript.
If a section has no information, return an empty array.
"""

    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": transcript
            }
        ],
        "temperature": 0.2,
        "response_format": {
            "type": "json_object"
        }
    }

    response = requests.post(
        GROQ_URL,
        headers=headers,
        json=payload,
        timeout=180
    )

    if not response.ok:
        raise RuntimeError(
            f"Groq API Error ({response.status}): {response.text}"
        )

    result = response.json()

    try:
        content = result["choices"][0]["message"]["content"]
        return json.loads(content)

    except (KeyError, IndexError, json.JSONDecodeError) as error:
        raise RuntimeError(
            f"Could not parse Groq response: {result}"
        ) from error


# --------------------------------------------------
# Home page
# --------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


# --------------------------------------------------
# API: Upload and transcribe audio
# --------------------------------------------------

@app.route("/api/transcribe", methods=["POST"])
def transcribe_audio():

    if "audio" not in request.files:
        return jsonify({
            "error": "No audio file was provided."
        }), 400

    audio_file = request.files["audio"]

    if not audio_file.filename:
        return jsonify({
            "error": "Please select an audio file."
        }), 400

    temp_audio_path = None

    try:
        suffix = os.path.splitext(audio_file.filename)[1]

        with tempfile.NamedTemporaryFile(
            suffix=suffix,
            dir=UPLOAD_FOLDER,
            delete=False
        ) as temp_file:
            temp_audio_path = temp_file.name

        audio_file.save(temp_audio_path)

        transcript = prisma_transcribe(temp_audio_path)

        if not transcript:
            return jsonify({
                "error": "No speech was detected in the audio."
            }), 400

        return jsonify({
            "success": True,
            "transcript": transcript
        })

    except Exception as error:
        print("Transcription error:", str(error))

        return jsonify({
            "error": str(error)
        }), 500

    finally:
        if (
            temp_audio_path
            and os.path.exists(temp_audio_path)
        ):
            os.remove(temp_audio_path)


# --------------------------------------------------
# API: Summarize transcript
# --------------------------------------------------

@app.route("/api/summarize", methods=["POST"])
def summarize_transcript():

    data = request.get_json(silent=True) or {}

    transcript = data.get("transcript", "").strip()

    if not transcript:
        return jsonify({
            "error": "Transcript is required."
        }), 400

    try:
        summary = groq_summarize(transcript)

        return jsonify({
            "success": True,
            "summary": summary
        })

    except Exception as error:
        print("Summarization error:", str(error))

        return jsonify({
            "error": str(error)
        }), 500


# --------------------------------------------------
# Run Flask application
# --------------------------------------------------

if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )

