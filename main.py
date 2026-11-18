import threading
import time

from brain import JarvisBrain
from ears import JarvisEars
from memory import MistakeVault
from ui import NeuralStudioHUD
from voice import speak


def assistant_loop(
    hud: NeuralStudioHUD,
    ears: JarvisEars,
    brain: JarvisBrain,
    memory: MistakeVault,
) -> None:
    """Background daemon loop managing Wake Once -> Continuous Chat -> Sleep ('Bye Jarvis')."""
    hud.set_state("THINKING", "CALIBRATING SENSORS...")
    ears.calibrate_ambient_noise(duration=0.5)

    # Startup greeting, then enter standby until you say 'Hey Jarvis'
    hud.set_awake_state(False)
    hud.reset_grammar_banner(
        "Systems online, Sir. Say 'Hey Jarvis' whenever you want to talk.",
        "Say 'Bye Jarvis' anytime to put me back to sleep",
    )
    speak(
        "All systems online, Sir. Good to see you, Rudra. Say Hey Jarvis whenever you want to chat.",
        hud,
        next_state="IDLE",
    )

    def on_wake_greet(phrase: str) -> None:
        hud.set_awake_state(True)
        hud.reset_grammar_banner(
            "I'm listening, Rudra — speak naturally!",
            "Continuous chat active • Say 'Bye Jarvis' to end",
        )
        speak(phrase, hud, next_state="LISTENING")
        time.sleep(0.2)

    while True:
        spoken_text = ears.listen(
            on_state_change=hud.set_state,
            on_wake_greet=on_wake_greet,
        )

        # Ensure HUD pill reflects active conversation state if woken via inline phrase
        hud.set_awake_state(ears.is_awake)

        if not spoken_text:
            if ears.is_awake:
                hud.set_state("LISTENING", "LISTENING // SPEAK FREELY")
            else:
                hud.set_state("IDLE", "STANDBY // SAY 'HEY JARVIS'")
            time.sleep(0.25)
            continue

        print(f"[RUDRA] {spoken_text}")

        # Check for sleep command ("Bye Jarvis" / "Go to sleep")
        if ears.is_sleep_command(spoken_text):
            ears.set_awake(False)
            hud.set_awake_state(False)
            farewell = "Going into standby, Sir. Just say Hey Jarvis whenever you need me again."
            memory.record_turn(
                original=spoken_text,
                has_mistake=False,
                corrected=spoken_text,
                tip="Session ended",
                reply=farewell,
            )
            hud.reset_grammar_banner(
                "Standing by — Conversation saved automatically.",
                "Say 'Hey Jarvis' to wake me up again",
            )
            speak(farewell, hud, next_state="IDLE")
            continue

        # Process sentence through Gemini 3.8 Flash & auto-save conversation
        hud.set_state("THINKING", "NEURAL CORE // POLISHING...")
        result = brain.think(spoken_text)

        # Update bottom real-time corrected English grammar display
        hud.show_grammar_polish(
            has_mistake=result["has_mistake"],
            corrected=result["corrected"],
            tip=result["tip"],
        )

        # Speak reply and stay directly in LISTENING mode for smooth back-and-forth chat
        next_hud_state = "LISTENING" if ears.is_awake else "IDLE"
        speak(result["reply"], hud, next_state=next_hud_state)
        time.sleep(0.25)  # Brief acoustic buffer so mic never picks up speaker tail


def main() -> None:
    memory = MistakeVault()
    ears = JarvisEars()

    try:
        brain = JarvisBrain(memory=memory)
    except ValueError as err:
        hud = NeuralStudioHUD()
        hud.set_state("THINKING", "API KEY REQUIRED")
        hud.reset_grammar_banner(str(err))
        hud.run()
        return

    def on_ui_awake_toggle(awake: bool) -> None:
        ears.set_awake(awake)
        if awake:
            hud.set_state("LISTENING", "LISTENING // SPEAK FREELY")
            hud.reset_grammar_banner("Session active — speak freely, Rudra!")
        else:
            hud.set_state("IDLE", "STANDBY // SAY 'HEY JARVIS'")
            hud.reset_grammar_banner("Standing by — Say 'Hey Jarvis' to wake up.")

    hud = NeuralStudioHUD(on_awake_toggle=on_ui_awake_toggle)

    worker = threading.Thread(
        target=assistant_loop,
        args=(hud, ears, brain, memory),
        daemon=True,
    )
    worker.start()

    hud.run()


if __name__ == "__main__":
    main()