import os
import io
import wave
from dotenv import load_dotenv
from openai import OpenAI
import streamlit as st
from langsmith import traceable

load_dotenv()

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

@traceable(name="recordAudio")
def record_audio():
    audio = st.audio_input(
        "Record emergency message",
        sample_rate=16000
    )

    if audio is None:
        return None, 0

    audio_bytes = audio.getvalue()

    with wave.open(io.BytesIO(audio_bytes), "rb") as audio_file:
        actual_duration = (
            audio_file.getnframes()
            / audio_file.getframerate()
        )

    return audio, actual_duration

@traceable(name="speechToText")
def speech_to_text(audio):
    audio.seek(0)

    transcript = client.audio.translations.create(
        model="whisper-1",
        file=audio
    )

    return transcript.text.strip()