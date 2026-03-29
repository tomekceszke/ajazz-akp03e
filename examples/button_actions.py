#!/usr/bin/env python3
"""Example: assign actions to buttons and knobs."""

import subprocess

from ajazz_akp03e import AKP03E, ButtonPress, KnobTurn


def launch_ghostty(event: ButtonPress):
    print(f"Button {event.key}: launching Ghostty")
    subprocess.Popen(["open", "-a", "Ghostty"])


def volume_control(event: KnobTurn):
    delta = 5 * event.direction
    sign = "+" if delta > 0 else "-"
    script = (
        f"set volume output volume "
        f"((output volume of (get volume settings)) {sign} {abs(delta)})"
    )
    subprocess.Popen(["osascript", "-e", script])
    print(f"Knob {event.knob}: volume {'up' if delta > 0 else 'down'}")


with AKP03E(brightness=60) as deck:
    # Button 0 opens Ghostty
    deck.on_button_press(0, launch_ghostty)

    # Knob 0 controls system volume
    deck.on_knob_turn(0, volume_control)

    deck.start()
    print("Ready! Button 0 = Ghostty, Knob 0 = Volume. Ctrl+C to stop.")
    deck.wait()
