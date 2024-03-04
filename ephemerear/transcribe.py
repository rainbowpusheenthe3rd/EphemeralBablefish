### Imports ###

# Standard Library Imports
from datetime import datetime
import os

# Third party library imports
import requests
from pydub import AudioSegment
import whisper
import yaml

# Imports from within the directory
from .documentModification import test_for_word
from EphemerEar import *

### End of Imports ###


## Function Definiton ##

# Assuming the whisper_local_transcribe function is defined elsewhere or here
def whisper_local_transcribe(file_path, model="base", custom_prompt="Here is the full text, in English:"):

    # Load whisper with the model, which defaults to 'base', and transcribe the target file at the filepath.
    model = whisper.load_model(model)
    result = model.transcribe(file_path, language='en', initial_prompt=custom_prompt)

    # Return the text of the model transcription
    return result["text"]


def split_audio(file_path, target_length_ms=10*60*1000, cache_dir="path/to/cache"):

    audio = AudioSegment.from_file(file_path)
    chunks = []

    # If there is no cache directory, make one.
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)
    for i, chunk in enumerate(audio[::target_length_ms]):
        chunk_name = os.path.join(cache_dir, f"{os.path.basename(file_path)}_chunk{i}.mp3")
        chunk.export(chunk_name, format="mp3")
        chunks.append(chunk_name)
    return chunks


def whisper_api_transcribe(chunks, api_key, custom_prompt="Here is the full text, in English:"):

    # Container for transcription results.
    transcriptions = []

    # Headers for request we will make to OpenAI's audio transcription API
    headers = {"Authorization": f"Bearer {api_key}"}

    # Iterable over the iterable, chunks, and for each chunk, transcribe it with the OpenAI transcription API
    for chunk in chunks:
        print(f"Transcribing {chunk}")
        with open(chunk, 'rb') as audio_file:
            files = {"file": audio_file}
            data = {"model": "whisper-1", "prompt": custom_prompt}
            response = requests.post("https://api.openai.com/v1/audio/transcriptions",
                                     headers=headers, files=files, data=data)
            # Append a successful transcription with the text response of the returned JSON.
            if response.status_code == 200:
                transcript = response.json()['text']
                transcriptions.append(transcript)
            # Append an error message if we could not get a successful 200 response text with valid response.json.
            else:
                print(f"Error transcribing {chunk}: {response.text}")
                transcriptions.append(f"[Error transcribing {chunk}]")

    # Piece the transcriptions back together, with a space between them.
    return " ".join(transcriptions)

def transcribe_audio(file_path,
                     api_key,
                     custom_prompt="Here is the full text, in English:",
                     cache_dir="path/to/cache",
                     width = 1024,
                     length = 1024):


    file_size_mb = os.path.getsize(file_path) / (width * length)
    if file_size_mb > 25:
        print("File is larger than 25MB, splitting into chunks...")
        chunks = split_audio(file_path, cache_dir=cache_dir)
    else:
        chunks = [file_path]

    # Use the whisper API to transcribe the chunks.
    transcription = whisper_api_transcribe(chunks, api_key, custom_prompt)
    return transcription

def handle_audio(audio_filepath,
                 api_key,
                 custom_prompt,
                 transcript_output_dir,
                 cache_dir="path/to/cache",
                 config_file=".ephemerear.config.yaml"):

    with open(config_file, 'r') as file:
        config = yaml.safe_load(file)

    stt_engine = config.get('bot', {}).get('stt_engine', 'openai')
    audio_filename = os.path.basename(audio_filepath)
    # Extract the date and time from the filename before any '-' character
    simplified_filename = audio_filename.split('-')[0]

    print(f"Handling file: {audio_filename}")

    now = datetime.now()
    current_year = now.strftime("%Y")
    current_month = now.strftime("%m")
    year_month_path = os.path.join(transcript_output_dir, current_year, current_month)
    os.makedirs(year_month_path, exist_ok=True)

    # Construct the path for the potential transcript file
    transcript_filename = f"{simplified_filename}.md"
    transcript_path = os.path.join(year_month_path, transcript_filename)

    # Check if a transcript file already exists for this audio file
    if os.path.exists(transcript_path):
        print(f"Skipping duplicate file: {audio_filename}")
        return
    
    # Perform transcription based on the configured STT engine
    if stt_engine == "whisper":
        transcription_result = whisper_local_transcribe(audio_filepath, custom_prompt = custom_prompt)
    else:
        transcription_result = whisper_api_transcribe([audio_filepath], api_key, custom_prompt)

    # Handle the transcript text for output
    handle_transcript(transcription_result, transcript_output_dir, simplified_filename, config_file = config_file)

    print(f"Processed and handled file: {audio_filename}")

#
def handle_transcript(transcript_text,
                      transcript_output_dir,
                      simplified_filename,
                      year_month_folders=True,
                      config_file=".ephemerear.config.yaml"):

    with open(config_file, 'r') as file:
        config = yaml.safe_load(file)
    #
    if year_month_folders:
        now = datetime.now()
        current_year = now.strftime("%Y")
        current_month = now.strftime("%m")
        year_dir = os.path.join(transcript_output_dir, current_year)
        month_dir = os.path.join(year_dir, current_month)
        os.makedirs(month_dir, exist_ok=True)
        transcript_output_dir = month_dir

    transcript_filename = f"{simplified_filename}.md"
    transcript_path = os.path.join(transcript_output_dir, transcript_filename)

    with open(transcript_path, 'w', encoding='utf-8') as transcript_file:
        transcript_file.write(transcript_text)

    print(f"Transcript written to {transcript_path}")

    if test_for_word(transcript_text, "prompt|from|prom"):
        print("Transcript contains prompt")
        prompt = transcript_text.lower().split("prompt")[1]

        # Remove any . or , characters from the prompt
        prompt = prompt.replace(".", "").replace(",", "").strip()
        message = prompt.lstrip()
        ee = EphemerEar(config_file)

        # Generates a chat with gpt
        ee.gpt_chat(message, model=config['model'])

    return transcript_text

