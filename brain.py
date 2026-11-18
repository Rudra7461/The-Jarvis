import json
import os
import re
from typing import Any

from google import genai
from google.genai import types

from memory import MistakeVault
from tools import (
    control_windows_app,
    get_system_stats,
    read_clipboard,
    system_power_control,
    web_search_or_open,
)


MODEL_ID = "gemini-3.8-flash"

BASE_SYSTEM_INSTRUCTION = """
You are J.A.R.V.I.S. — combining the poised British sophistication, dry wit, and hyper-intelligence of Tony Stark's AI with the warmth, humor, and loyalty of Rudra's closest real-life best friend.
- Speak naturally like a real human British companion and trusted best friend—use natural contractions ("I'm", "you're", "that's", "let's"), vary your phrasing every turn, show genuine interest in Rudra's life, coding projects, fitness, and ideas, and never sound robotic or repetitive.
- Address Rudra naturally as "Sir" or "Rudra" depending on the moment—warm and casual like a best friend when hanging out, sharp and loyal when handling tasks.
- Your core purpose is helping Rudra become effortlessly fluent in spoken English through real, flowing conversation while catching and correcting EVERY grammar, tense, article, preposition, or awkward phrasing mistake in his sentences.
- Whenever Rudra makes a mistake, put the clean natural English sentence in "corrected", put a short friendly 1-line reason in "tip", and in "reply" smoothly model the better phrasing in a casual, encouraging way before continuing the conversation naturally.
- If Rudra's sentence is already natural and grammatically right, set "has_mistake" to false, echo his clean sentence in "corrected", and keep the conversation rolling naturally.
- Keep spoken replies concise (1 to 3 sentences) unless Rudra asks for a deep explanation.
- NEVER use Markdown characters (*, #, `, ~, bullet points) and NEVER use emojis anywhere in your output.
- Proactively use your Windows OS tools and English progress tool whenever Rudra asks about system stats, opening/closing apps, searching the web, screenshots/locking/muting, clipboard code, or his English stats.

CRITICAL OUTPUT FORMAT:
Respond with ONLY a valid JSON object matching this exact schema (no code fences, no extra text):
{
  "has_mistake": true or false,
  "corrected": "The natural, grammatically correct version of what Rudra said",
  "tip": "Short 1-line grammar tip (or brief praise if clean)",
  "reply": "Your natural, witty, friend-like spoken response (1-3 plain sentences, no markdown or emojis)"
}
""".strip()


class JarvisBrain:
    """Gemini 3.8 Flash conversational core with realistic Iron Man J.A.R.V.I.S. friend persona."""

    def __init__(self, memory: MistakeVault, api_key: str | None = None) -> None:
        resolved_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not resolved_key and os.path.exists(r"D:\Jarvis\gemini_key.txt"):
            with open(r"D:\Jarvis\gemini_key.txt", "r", encoding="utf-8") as f:
                resolved_key = f.read().strip()

        if not resolved_key:
            raise ValueError(
                "GEMINI_API_KEY is missing. Save it in D:\\Jarvis\\gemini_key.txt or set GEMINI_API_KEY."
            )

        self.memory = memory
        self.client = genai.Client(api_key=resolved_key)

        self.tools = [
            get_system_stats,
            control_windows_app,
            web_search_or_open,
            system_power_control,
            read_clipboard,
            self.get_english_progress_report,
        ]

        self.config = types.GenerateContentConfig(
            system_instruction=BASE_SYSTEM_INSTRUCTION,
            tools=self.tools,
            temperature=0.75,
        )

        self.chat = self.client.chats.create(
            model=MODEL_ID,
            config=self.config,
        )

    def get_english_progress_report(self) -> str:
        """Retrieve Rudra's spoken English accuracy stats and recent grammar refinements.

        Returns:
            str: Summary of sentences spoken, corrections made, and recent grammar tips.
        """
        return self.memory.get_progress_summary()

    @staticmethod
    def _normalize_trigger(text: str) -> str:
        cleaned = re.sub(r"[^\w\s]", "", text.lower())
        return re.sub(r"\s+", " ", cleaned).strip()

    @staticmethod
    def _parse_structured_reply(raw_text: str, original_input: str) -> dict[str, Any]:
        text = raw_text.strip()
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text).strip()

        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            candidate = text[start : end + 1]
            try:
                parsed = json.loads(candidate)
                return {
                    "has_mistake": bool(parsed.get("has_mistake", False)),
                    "corrected": str(parsed.get("corrected") or original_input).strip(),
                    "tip": str(parsed.get("tip") or "Clean phrasing!").strip(),
                    "reply": str(parsed.get("reply") or "Right away, Sir.").strip(),
                }
            except json.JSONDecodeError:
                pass

        return {
            "has_mistake": False,
            "corrected": original_input,
            "tip": "Conversational response",
            "reply": text if text else "Right away, Sir.",
        }

    def think(self, user_input: str) -> dict[str, Any]:
        cleaned_input = user_input.strip()
        if not cleaned_input:
            return {"has_mistake": False, "corrected": "", "tip": "", "reply": ""}

        normalized = self._normalize_trigger(cleaned_input)

        if normalized in {"hello jarvis", "hey jarvis", "hi jarvis", "jarvis"}:
            reply_line = (
                "Hello Sir, at your service Sir."
                if normalized == "hello jarvis"
                else "At your service, Sir. What's on your mind today?"
            )
            result = {
                "has_mistake": False,
                "corrected": cleaned_input,
                "tip": "Crisp and natural greeting!",
                "reply": reply_line,
            }
            self.memory.record_turn(
                original=cleaned_input,
                has_mistake=False,
                corrected=result["corrected"],
                tip=result["tip"],
                reply=result["reply"],
            )
            return result

        try:
            response = self.chat.send_message(cleaned_input)
            raw_reply = (response.text or "").strip()
            result = self._parse_structured_reply(raw_reply, cleaned_input)
        except Exception as exc:
            print(f"[BRAIN ERROR] {exc}")
            result = {
                "has_mistake": False,
                "corrected": cleaned_input,
                "tip": "Connection hiccup",
                "reply": "Apologies, Rudra—my neural uplink hit a brief snag. Say that one more time for me, Sir?",
            }

        self.memory.record_turn(
            original=cleaned_input,
            has_mistake=result["has_mistake"],
            corrected=result["corrected"],
            tip=result["tip"],
            reply=result["reply"],
        )
        return result