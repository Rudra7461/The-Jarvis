from datetime import datetime
import json
import os
from typing import Any


DEFAULT_LOG_PATH = r"D:\Jarvis\mistakes_log.json"
CONVERSATIONS_DIR = r"D:\Jarvis\conversations"


class MistakeVault:
    """
    Automatically saves:
    1. Every full conversation turn to readable daily transcripts in D:\\Jarvis\\conversations\\
    2. Grammar corrections and fluency metrics to D:\\Jarvis\\mistakes_log.json
    """

    def __init__(
        self,
        log_path: str = DEFAULT_LOG_PATH,
        conversations_dir: str = CONVERSATIONS_DIR,
    ) -> None:
        self.log_path = log_path
        self.conversations_dir = conversations_dir
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)
        os.makedirs(self.conversations_dir, exist_ok=True)
        self.data: dict[str, Any] = self._load()

    def _load(self) -> dict[str, Any]:
        if not os.path.exists(self.log_path):
            return {"total_spoken": 0, "total_corrected": 0, "entries": []}
        try:
            with open(self.log_path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                if isinstance(loaded, dict):
                    loaded.setdefault("total_spoken", 0)
                    loaded.setdefault("total_corrected", 0)
                    loaded.setdefault("entries", [])
                    return loaded
        except Exception as exc:
            print(f"[MEMORY] Fresh log initialized: {exc}")

        return {"total_spoken": 0, "total_corrected": 0, "entries": []}

    def _save_json(self) -> None:
        try:
            with open(self.log_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
        except Exception as exc:
            print(f"[MEMORY] JSON save error: {exc}")

    def _append_conversation_transcript(
        self,
        original: str,
        has_mistake: bool,
        corrected: str,
        tip: str,
        reply: str,
    ) -> None:
        """Automatically append every spoken exchange to today's conversation text file."""
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%I:%M:%S %p")
        file_path = os.path.join(self.conversations_dir, f"chat_{date_str}.txt")

        lines = [f"[{time_str}] RUDRA  : {original}"]
        if has_mistake:
            lines.append(f"[{time_str}] POLISH : {corrected} ({tip})")
        else:
            lines.append(f"[{time_str}] POLISH : ✓ Natural English")
        lines.append(f"[{time_str}] JARVIS : {reply}")
        lines.append("-" * 64)

        try:
            with open(file_path, "a", encoding="utf-8") as f:
                f.write("\n".join(lines) + "\n")
        except Exception as exc:
            print(f"[MEMORY] Transcript write error: {exc}")

    def record_turn(
        self,
        original: str,
        has_mistake: bool,
        corrected: str,
        tip: str,
        reply: str = "",
        mode: str = "FRIEND",
    ) -> None:
        """Persist both the full conversation transcript and grammar stats automatically."""
        self.data["total_spoken"] = int(self.data.get("total_spoken", 0)) + 1

        if has_mistake:
            self.data["total_corrected"] = int(self.data.get("total_corrected", 0)) + 1
            entry = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "mode": mode,
                "original": original,
                "corrected": corrected,
                "tip": tip,
            }
            self.data["entries"].append(entry)
            if len(self.data["entries"]) > 300:
                self.data["entries"] = self.data["entries"][-300:]

        self._save_json()
        self._append_conversation_transcript(original, has_mistake, corrected, tip, reply)

    def get_counts(self) -> tuple[int, int]:
        return int(self.data.get("total_spoken", 0)), int(self.data.get("total_corrected", 0))

    def get_progress_summary(self) -> str:
        spoken, corrected = self.get_counts()
        if spoken == 0:
            return "We have not logged any spoken sentences yet, Sir."

        accuracy = max(0.0, ((spoken - corrected) / spoken) * 100.0)
        recent = self.data.get("entries", [])[-3:]

        summary = (
            f"You have spoken {spoken} sentences so far with {corrected} grammar refinements, "
            f"giving you a fluency accuracy of {accuracy:.0f} percent."
        )
        if recent:
            examples = "; ".join(
                f"instead of '{item['original']}', say '{item['corrected']}'"
                for item in recent
            )
            summary += f" Recent refinements include: {examples}."
        return summary