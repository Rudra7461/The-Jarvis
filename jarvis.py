import speech_recognition as sr
import pyttsx3
import google.generativeai as genai
import sounddevice as sd
import scipy.io.wavfile as wav
import os
import datetime
import webbrowser
import subprocess

# 1. Configure Jarvis's Voice
engine = pyttsx3.init()
voices = engine.getProperty('voices')
engine.setProperty('voice', voices[0].id) 
engine.setProperty('rate', 170) 

def speak(text):
    print(f"Jarvis: {text}")
    engine.say(text)
    engine.runAndWait()

# 2. Define OS Automation Tools (Jarvis's Hands)
def get_current_time():
    """Returns the current time on the system."""
    return datetime.datetime.now().strftime("%I:%M %p")

def open_website(url: str):
    """Opens a specified website URL in the default browser. Ensure URL has https://"""
    webbrowser.open(url)
    return f"I have opened {url} in your browser."

def open_application(app_name: str):
    """Opens basic Windows applications."""
    app_name = app_name.lower()
    if "notepad" in app_name:
        subprocess.Popen("notepad.exe")
        return "Notepad opened."
    elif "calculator" in app_name or "calc" in app_name:
        subprocess.Popen("calc.exe")
        return "Calculator opened."
    elif "cmd" in app_name or "command" in app_name:
        subprocess.Popen("cmd.exe")
        return "Command prompt opened."
    else:
        return f"Application {app_name} not found or supported yet."

# 3. Configure Jarvis's Brain with Tools
# (Paste your API key here again)
genai.configure(api_key="YOUR_GEMINI_API_KEY_HERE")

system_instruction = (
    "You are Jarvis, a highly intelligent and friendly AI assistant. "
    "Your creator is Rudra. Keep your answers conversational, concise, and helpful. "
    "Do not use markdown, bolding, or special characters in your response."
)

# We pass the functions we created into the 'tools' parameter
model = genai.GenerativeModel(
    'gemini-1.5-flash',
    tools=[get_current_time, open_website, open_application], 
    system_instruction=system_instruction
)

# enable_automatic_function_calling allows Gemini to run the Python functions itself!
chat = model.start_chat(enable_automatic_function_calling=True)

# 4. Configure Jarvis's Ears 
def listen():
    fs = 44100 
    duration = 5 
    filename = 'temp_audio.wav'
    
    print(f"\nListening for {duration} seconds...")
    
    recording = sd.rec(int(duration * fs), samplerate=fs, channels=1)
    sd.wait() 
    
    wav.write(filename, fs, recording)
    
    r = sr.Recognizer()
    with sr.AudioFile(filename) as source:
        audio = r.record(source)
        
    if os.path.exists(filename):
        os.remove(filename)
        
    try:
        query = r.recognize_google(audio)
        print(f"Rudra: {query}")
        return query.lower()
    except sr.UnknownValueError:
        return ""
    except sr.RequestError:
        speak("I am having trouble connecting to the speech recognition service.")
        return ""

# 5. Main Execution Loop
def main():
    speak("Hello Rudra How can I help you today?")
    
    while True:
        query = listen()
        
        if query == "":
            continue
            
        if "sleep" in query or "exit" in query or "goodbye" in query:
            speak("Goodbye, Rudra. Let me know if you need anything else.")
            break
            
        try:
            # Send the voice query. If you ask for the time, Gemini will silently 
            # run the get_current_time() function, get the result, and speak it back to you.
            response = chat.send_message(query)
            speak(response.text)
        except Exception as e:
            speak("I encountered an error connecting to my brain.")
            print(f"Error: {e}")

if __name__ == "__main__":
    main()