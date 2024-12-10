from flask import Flask, render_template, request, jsonify, url_for, send_from_directory, redirect
import fitz  # PyMuPDF
from google.cloud import texttospeech
from google.oauth2 import service_account
import os

app = Flask(__name__)

def is_readable_pdf(file_path):
    try:
        doc = fitz.open(file_path)
        return doc.page_count > 0
    except Exception as e:
        print(f"Error checking PDF readability: {e}")
        return False

def extract_text(file_path):
    doc = fitz.open(file_path)
    full_text = ""
    for page_number, page in enumerate(doc):
        blocks = page.get_text("blocks")
        page_text = ""
        for block in blocks:
            text = block[4].strip()
            if text and len(text.split()) >= 200:
                print(f"Found valid text block on page {page_number + 1}: {text[:100]}...")
                page_text += text + " "
        if not page_text:
            text = page.get_text("text")
            if text:
                page_text += text + " "
                print(f"Extracted full page text on page {page_number + 1}: {text[:100]}...")
        full_text += page_text + "\n"
    return full_text

def synthesize_text(text):
    credentials_path = 'c:/AppKeys/speech-441818-b5a90780ba1f.json'
    credentials = service_account.Credentials.from_service_account_file(credentials_path)
    client = texttospeech.TextToSpeechClient(credentials=credentials)

    input_text = texttospeech.SynthesisInput(text=text)
    voice = texttospeech.VoiceSelectionParams(
        language_code="en-US",
        ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
    )
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3
    )

    response = client.synthesize_speech(
        input=input_text, voice=voice, audio_config=audio_config
    )
    return response.audio_content

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if 'file' not in request.files:
            return jsonify({'error': 'No file part'})
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No selected file'})

        upload_path = os.path.join(app.root_path, 'uploads', file.filename)
        if not os.path.exists(os.path.dirname(upload_path)):
            os.makedirs(os.path.dirname(upload_path))
        file.save(upload_path)

        text = extract_text(upload_path)
        if not text.strip():
            return jsonify({'error': 'No valid text found in the PDF'})

        audio_content = synthesize_text(text)
        audio_file_path = os.path.join(app.root_path, 'output', 'output.mp3')
        if not os.path.exists(os.path.dirname(audio_file_path)):
            os.makedirs(os.path.dirname(audio_file_path))
        with open(audio_file_path, "wb") as out:
            out.write(audio_content)

        return jsonify({'audio_url': url_for('play_audio')})

    return render_template('index.html')

@app.route('/play_audio')
def play_audio():
    return send_from_directory(os.path.join(app.root_path, 'output'), 'output.mp3')

@app.route('/restart')
def restart_audio():
    # This endpoint doesn't need to do anything since restarting is handled by the client
    return jsonify({'status': 'restarted'})

@app.route('/load_new')
def load_new():
    return redirect(url_for('index'))

if __name__ == "__main__":
    app.run(debug=True)
