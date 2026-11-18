# J.A.R.V.I.S. — AI English Fluency Buddy & Desktop Companion

**J.A.R.V.I.S.** is a real-time, voice-first AI companion built in Python. Combining the poised British wit of Tony Stark's AI with the warmth of a supportive best friend, J.A.R.V.I.S. helps you master spoken English through natural daily conversation—catching every grammatical mistake in real time while also automating your desktop.

---

## Key Features

* **Wake Once, Converse Freely:** Say **"Hey Jarvis"** once to wake him up (*"At your service, Sir."*). Enjoy continuous, natural back-and-forth conversation without repeating the wake word—then simply say **"Bye Jarvis"** to put him back into standby.
* **Real-Time Grammar Polish:** Every sentence you speak is analyzed instantly. If there is a grammar, tense, or phrasing mistake, the HUD highlights the natural corrected version live at the bottom of the screen while J.A.R.V.I.S. gently models it in conversation.
* **Neural British Voice (`en-GB-RyanNeural`):** Powered by Microsoft Edge Neural TTS (`edge-tts`) with low-latency `sounddevice` playback and an automatic offline `pyttsx3` fallback.
* **Minimalist Round Reactor HUD:** A borderless, dark-mode `tkinter` concentric ring interface (`460x520`) that dynamically shifts color and motion across `IDLE` (Cyan), `LISTENING` (Crimson), `THINKING` (Amber), and `SPEAKING` (Emerald) states.
* **Auto-Saved Conversations & Mistake Vault:**
  * Daily readable conversation transcripts automatically saved to `conversations/chat_YYYY-MM-DD.txt`.
  * Lifetime grammar refinements and accuracy stats tracked in `mistakes_log.json`.
* **Desktop OS Voice Control:** Check live CPU/RAM/battery stats, open or close apps (`Chrome`, `VS Code`, `XAMPP`, `Notepad`, `Calculator`, `CMD`, `Task Manager`), search Google/YouTube/GitHub, lock/mute/capture screenshots, and explain code copied to your clipboard.

---

## Project Architecture

```text
The-Jarvis/
├── main.py          # Entry point & multi-threaded session coordinator
├── ui.py            # Round concentric ring HUD & live grammar display (Tkinter)
├── ears.py          # Dynamic VAD microphone capture & Speech-to-Text (zero PyAudio)
├── voice.py         # Speech sanitizer & British Neural TTS engine
├── brain.py         # Gemini 3.8 Flash conversational core, English coach & tool router
├── tools.py         # Local OS automation & system telemetry functions
├── memory.py        # Automatic conversation transcript & grammar vault persistence
├── .gitignore       # Excludes API keys, logs, and local caches from Git
└── README.md        # Multi-platform setup instructions & roadmap
```

---

## Tech Stack

* **AI Core:** Google GenAI SDK (`gemini-3.8-flash`)
* **Speech-to-Text (STT):** `sounddevice` (`int16` @ `16kHz`) + `scipy` + `numpy` + `SpeechRecognition`
* **Text-to-Speech (TTS):** `edge-tts` (`en-GB-RyanNeural`) + `soundfile` + `sounddevice` (`pyttsx3` offline fallback)
* **Desktop UI:** Python `tkinter` (33 FPS vector canvas animation)
* **OS Automation:** `psutil`, `Pillow`, `ctypes`

---

## How to Run (Platform-by-Platform Guide)

### 1. Windows (Windows 10 / 11 — Recommended)

1. **Clone the Repository:**
   ```powershell
   git clone [https://github.com/Rudra7461/The-Jarvis.git](https://github.com/Rudra7461/The-Jarvis.git)
   cd The-Jarvis
   ```

2. **Install Python Dependencies (Python 3.10 – 3.14 compatible, zero `pyaudio`):**
   ```powershell
   pip install sounddevice scipy numpy SpeechRecognition edge-tts soundfile pyttsx3 google-genai psutil pillow
   ```

3. **Configure Your Gemini API Key:**
   Get a free key from [Google AI Studio](https://aistudio.google.com/apikey) and save it in PowerShell:
   ```powershell
   setx GEMINI_API_KEY "your_api_key_here"
   ```
   *(Close and reopen PowerShell or VS Code after running `setx`.)*

4. **Launch J.A.R.V.I.S.:**
   ```powershell
   python main.py
   ```

---

### 2. Ubuntu & Kali Linux (Debian-Based Distributions)

Ubuntu and Kali Linux require system-level audio/GUI libraries (`portaudio`, `libsndfile`, `python3-tk`) and a Python virtual environment (`venv`) due to PEP 668 environment protection.

1. **Install Required System Packages:**
   ```bash
   sudo apt update
   sudo apt install -y git python3 python3-pip python3-venv python3-tk libportaudio2 libsndfile1 espeak-ng
   ```

2. **Clone the Repository & Create a Virtual Environment:**
   ```bash
   git clone [https://github.com/Rudra7461/The-Jarvis.git](https://github.com/Rudra7461/The-Jarvis.git)
   cd The-Jarvis
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install Python Libraries:**
   ```bash
   pip install sounddevice scipy numpy SpeechRecognition edge-tts soundfile pyttsx3 google-genai psutil pillow
   ```

4. **Export Your Gemini API Key:**
   ```bash
   export GEMINI_API_KEY="your_api_key_here"
   ```
   *(To make it permanent, add that line to `~/.bashrc` or `~/.zshrc` and run `source ~/.bashrc`.)*

5. **Run J.A.R.V.I.S.:**
   ```bash
   python3 main.py
   ```

> **Linux Note:** The HUD (`ui.py`), microphone listener (`ears.py`), neural voice (`voice.py`), and English grammar coach (`brain.py`) run natively on Ubuntu and Kali Linux. Windows-specific OS commands inside `tools.py` (such as `LockWorkStation` or `taskkill`) are designed for Windows and can be swapped with Linux equivalents (`xdg-open`, `pkill`) if needed.

---

### 3. iOS (iPhone & iPad)

Apple's iOS sandbox does not allow desktop Python GUI libraries (`tkinter`) or low-level PortAudio drivers (`sounddevice`) to run directly on an iPhone. You can run J.A.R.V.I.S. on iOS using either of these two approaches:

#### Option A: Run Today via Apple Shortcuts + Local/Cloud API Bridge
1. Run the J.A.R.V.I.S. Python backend (`brain.py` + `memory.py`) on your laptop or a cloud server wrapped in a lightweight **FastAPI** or **Flask** `/chat` endpoint.
2. Open the built-in **Shortcuts** app on your iPhone and create a new shortcut:
   * **Dictate Text** (captures your spoken English sentence via iOS native speech recognition).
   * **Get Contents of URL** (sends your dictated text to your J.A.R.V.I.S. server endpoint).
   * **Speak Text** (speaks J.A.R.V.I.S.'s corrected English response aloud using iOS British Siri voice).
3. Say *"Hey Siri, Talk to Jarvis"* from anywhere on your iPhone or AirPods.

#### Option B: Native iOS App (Planned Phase 3 Build)
* Port the `brain.py` prompt logic and `MistakeVault` progress tracker into a cross-platform **Flutter** or **React Native (Expo)** mobile app using native iOS `AVFoundation` audio APIs for App Store / TestFlight deployment.

---

## Voice Commands

| Command | Action |
| :--- | :--- |
| **"Hey Jarvis"** / **"Hello Jarvis"** | Wakes J.A.R.V.I.S. up into continuous conversation mode |
| **"Bye Jarvis"** / **"Go to sleep"** | Ends active chat and returns J.A.R.V.I.S. to standby |
| **"Check my CPU and RAM usage"** | Reports live processor, memory, and battery levels |
| **"Open VS Code / Chrome / XAMPP"** | Launches or closes supported desktop applications |
| **"Explain what's on my clipboard"** | Reads copied code/text and explains or debugs it aloud |
| **"Take a screenshot"** | Captures your screen into `screenshots/` |

---

## Long-Term Product Roadmap

* **Phase 1 — Desktop Companion (Completed):** Real-time voice conversation, round sci-fi HUD, instant English grammar correction, auto-saved transcripts, and OS automation tools.
* **Phase 2 — Deep Fluency Analytics:** Topic-based roleplay scenarios (Tech Interviews, Client Calls, Daily Hangouts) and weekly weak-spot grammar summaries.
* **Phase 3 — Cross-Platform Mobile App (iOS & Android):** Native mobile client built with Flutter / React Native for hands-free spoken English practice on the go.