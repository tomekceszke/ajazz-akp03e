#!/usr/bin/env python3
"""Minimal example: connect to the AKP03E and print all events."""

from ajazz_akp03e import AKP03E, Event

def on_event(event: Event):
    print(event)

with AKP03E() as deck:
    deck.on_event(on_event)
    deck.start()
    print("Listening for events... Press Ctrl+C to stop.")
    deck.wait()
