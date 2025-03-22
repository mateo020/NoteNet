from openai import OpenAI

# Initialize the OpenAI client
client = OpenAI(api_key="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")  # Replace with your actual OpenAI API key

def transcribe_audio(file_path):
    try:
        # Open the audio file in binary mode
        with open(file_path, "rb") as audio_file:
            # Transcribe the audio using the latest OpenAI API syntax
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
            )
            print("Transcription:\n", transcript.text)
    except Exception as e:
        if "insufficient_quota" in str(e):
            print("Error: You have exceeded your API quota. Please check your billing and plan details.")
        else:
            print(f"Error transcribing audio: {e}")

if __name__ == "__main__":
    audio_file_path = "C:/Users/moham/Downloads/GunsForHire.mp3"  # Update with your audio file path
    transcribe_audio(audio_file_path)