"""Entry point for the Blox Fruits automation tool (educational demo).

Initialises logging, checks dependencies, registers global hotkeys,
and manages the macro recorder / player and ESP helper lifecycles.
"""

import sys
import time
import logging
from typing import Optional

import keyboard

from config import Config
from utils import setup_logger, print_dependency_report, is_admin
from macro import MacroRecorder, MacroPlayer
from esp_helper import ESPHelper

# ── Global state ─────────────────────────────────────────────────────────────
logger: logging.Logger = logging.getLogger("blox_fruits_tool")
recorder: Optional[MacroRecorder] = None
player: Optional[MacroPlayer] = None
esp: Optional[ESPHelper] = None
esp_enabled: bool = False


# ── Hotkey handlers ──────────────────────────────────────────────────────────

def handle_start() -> None:
    """Start macro playback with the last recorded events."""
    global player
    if player and player.is_playing:
        logger.warning("Playback is already running.")
        return
    if recorder is None or not recorder.get_events():
        logger.error("No recorded events. Press %s to record first.", Config.HOTKEY_RECORD)
        return
    events = recorder.get_events()
    player = MacroPlayer(
        events=events,
        loop_count=Config.LOOP_COUNT,
        click_delay=Config.CLICK_DELAY,
        key_delay=Config.KEY_DELAY,
        loop_delay=Config.LOOP_DELAY,
    )
    # Run in a daemon thread so hotkeys remain responsive
    import threading
    thread = threading.Thread(target=player.play, daemon=True)
    thread.start()
    logger.info("Macro playback started in background thread.")


def handle_stop() -> None:
    """Stop any active macro playback or recording."""
    global player
    if recorder and recorder.is_recording:
        recorder.stop()
        logger.info("Recording stopped by user.")
    if player and player.is_playing:
        player.stop()
        logger.info("Playback stopped by user.")


def handle_record() -> None:
    """Toggle macro recording on/off."""
    if recorder is None:
        return
    if recorder.is_recording:
        recorder.stop()
    else:
        if player and player.is_playing:
            logger.warning("Stop playback before starting a new recording.")
            return
        recorder.start()


def handle_replay() -> None:
    """Replay the last recorded macro once (single iteration)."""
    global player
    if not recorder or not recorder.get_events():
        logger.error("Nothing to replay. Record a macro first.")
        return
    if player and player.is_playing:
        logger.warning("Stop current playback first.")
        return
    player = MacroPlayer(
        events=recorder.get_events(),
        loop_count=1,
        click_delay=Config.CLICK_DELAY,
        key_delay=Config.KEY_DELAY,
        loop_delay=Config.LOOP_DELAY,
    )
    import threading
    thread = threading.Thread(target=player.play, daemon=True)
    thread.start()


def handle_toggle_esp() -> None:
    """Toggle the ESP scanning loop on/off."""
    global esp_enabled
    esp_enabled = not esp_enabled
    status = "enabled" if esp_enabled else "disabled"
    logger.info("ESP scanning %s.", status)
    if esp_enabled and esp:
        import threading
        thread = threading.Thread(target=_esp_loop, daemon=True)
        thread.start()


def _esp_loop() -> None:
    """Background loop that performs ESP scans and logs detections."""
    if esp is None:
        return
    logger.info("ESP background scan started.")
    try:
        while esp_enabled:
            results = esp.scan_screen(region=Config.CAPTURE_REGION)
            for r in results:
                logger.info("  [ESP] %s at %s (conf=%.2f)", r.label, r.center, r.confidence)
            time.sleep(Config.SCREEN_CAPTURE_INTERVAL)
    except Exception as exc:
        logger.error("ESP loop error: %s", exc)
    logger.info("ESP background scan stopped.")


# ── Main function ────────────────────────────────────────────────────────────

def main() -> None:
    """Application entry point."""
    global recorder, esp

    # 1. Logger
    logger = setup_logger(
        name="blox_fruits_tool",
        level=Config.LOG_LEVEL,
        log_to_file=Config.LOG_TO_FILE,
        log_file_path=Config.LOG_FILE_PATH,
    )
    logger.info("=" * 60)
    logger.info("Blox Fruits Automation Tool – Educational Demo")
    logger.info("=" * 60)

    # 2. Privilege check (informational only)
    if is_admin():
        logger.info("Running with elevated privileges.")
    else:
        logger.info("Running without elevated privileges (some features may be limited).")

    # 3. Dependency check
    logger.info("Checking dependencies...")
    if not print_dependency_report(logger):
        logger.error(
            "Missing dependencies detected. Install them with: pip install -r requirements.txt"
        )
        sys.exit(1)

    # 4. Initialise components
    recorder = MacroRecorder(max_duration=Config.MAX_RECORDING_DURATION)
    esp = ESPHelper(
        templates_dir="templates",
        confidence_threshold=Config.CONFIDENCE_THRESHOLD,
        scale_range=Config.TEMPLATE_SCALE_RANGE,
    )

    # 5. Register hotkeys
    hotkey_map = {
        Config.HOTKEY_START: handle_start,
        Config.HOTKEY_STOP: handle_stop,
        Config.HOTKEY_RECORD: handle_record,
        Config.HOTKEY_REPLAY: handle_replay,
        Config.HOTKEY_TOGGLE_ESP: handle_toggle_esp,
    }
    for key, handler in hotkey_map.items():
        try:
            keyboard.add_hotkey(key, handler)
            logger.info("Hotkey registered: %s", key)
        except Exception as exc:
            logger.error("Failed to register hotkey %s: %s", key, exc)

    # 6. Print usage summary
    logger.info("-" * 60)
    logger.info("Hotkeys:")
    logger.info("  %s – Start macro loop", Config.HOTKEY_START)
    logger.info("  %s – Stop recording / playback", Config.HOTKEY_STOP)
    logger.info("  %s – Start / stop recording", Config.HOTKEY_RECORD)
    logger.info("  %s – Replay once", Config.HOTKEY_REPLAY)
    logger.info("  %s – Toggle ESP scan", Config.HOTKEY_TOGGLE_ESP)
    logger.info("-" * 60)
    logger.info("Press Ctrl+C to exit.")
    logger.info("-" * 60)

    # 7. Block main thread
    try:
        keyboard.wait()  # Blocks until a registered exit key or Ctrl+C
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        handle_stop()
        esp_enabled = False
        logger.info("Goodbye.")


if __name__ == "__main__":
    main()
