import openai
import json
import streamlit as st
import re
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

TOGETHER_API_KEY = "61ef3dfc4a2cab4370e88b705cfe12b488dd52b8682d5c2c42baa9a21096f82a"  # Replace with your actual API key

openai.api_base = "https://api.together.xyz/v1"
openai.api_key = TOGETHER_API_KEY

client = MongoClient("mongodb://localhost:27017/")

db = client["database"] 
transcriptions_collection = db["transcriptions"]  # Corrected collection reference
summaries_collection = db["summaries"]  # Corrected collection reference

st.title("Together AI Transcription App")

# Model selection dropdown
model_options = [
    "meta-llama/Llama-3.3-70B-Instruct-Turbo-Free",
    "Qwen/QwQ-32B-Preview",
    "deepseek-ai/DeepSeek-R1-Distill-Llama-70B-free",
    "scb10x/scb10x-llama3-typhoon-v1-5x-4f316"
]
selected_model = st.selectbox("Choose a model:", model_options, index=0, key="model_select", format_func=str)

def summarize_text(text, model):
    """Uses Together AI's OpenAI-compatible API to summarize text in Indonesian."""
    try:
        response = openai.ChatCompletion.create(
            model=model,
            messages=[ 
                {"role": "system", "content": "Anda adalah AI yang merangkum percakapan dalam bahasa Indonesia."},
                {"role": "user", "content": f"Buat ringkasan singkat dari percakapan berikut dalam bahasa Indonesia:\n\n{text}"}
            ],
            max_tokens=200
        )
        return response["choices"][0]["message"]["content"]
    except Exception as e:
        return f"API Error: {str(e)}"

def convert_vtt_to_json(vtt_content):
    """Converts VTT subtitles to JSON format with speaker and text."""
    data = []
    current_speaker = "Unknown"
    entry = {}

    lines = vtt_content.split("\n")

    for i in range(len(lines)):
        line = lines[i].strip()

        if re.match(r"^[\w-]+/\d+-\d+$", line):
            continue
        elif "-->" in line:
            entry = {"speaker": current_speaker, "text": ""}
        elif match := re.match(r"<v\s+([^>]+)>(.+)</v>", line):
            current_speaker, text = match.groups()
            entry["speaker"] = current_speaker
            entry["text"] = text
            data.append(entry)
        elif line and entry:
            entry["text"] += " " + line.strip()

    return json.dumps(data, indent=2, ensure_ascii=False)

# File Upload (JSON or VTT)
uploaded_file = st.file_uploader("Upload a JSON or VTT file", type=["json", "vtt"])

json_text = None
summary = None
if uploaded_file is not None:
    file_type = uploaded_file.name.split(".")[-1]

    try:
        if file_type == "json":
            json_data = json.load(uploaded_file)
            json_text = json.dumps(json_data, indent=2)
        elif file_type == "vtt":
            vtt_content = uploaded_file.read().decode("utf-8")
            json_text = convert_vtt_to_json(vtt_content)

        with st.expander("View JSON Data", expanded=False):
            st.json(json.loads(json_text))
    except Exception as e:
        st.error(f"Error processing file: {e}")

# Summarize button
if json_text is not None:
    if st.button("Summarize"):
        summary = summarize_text(json_text, selected_model)
        st.subheader("Summary")
        st.write(summary)

# Save to MongoDB Button (for Transcription)
if json_text is not None:
    if st.button("Save Transcription to Database"):
        transcription_document = {
            "transcription": json.loads(json_text),
        }
        # Debugging
        st.write(f"Saving transcription: {transcription_document}")
        result = transcriptions_collection.insert_one(transcription_document)  # Corrected collection reference
        if result.inserted_id:
            st.success("Transcription saved to MongoDB!")
        else:
            st.error("Failed to save transcription.")

# Save to MongoDB Button (for Summary)
if summary is not None:
    if st.button("Save Summary to Database"):
        summary_document = {
            "summary": summary
        }
        # Debugging
        st.write(f"Saving summary: {summary_document}")
        result = summaries_collection.insert_one(summary_document)  # Corrected collection reference
        if result.inserted_id:
            st.success("Summary saved to MongoDB!")
        else:
            st.error("Failed to save summary.")