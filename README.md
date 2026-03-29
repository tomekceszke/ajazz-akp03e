# ajazz-akp03e

Python SDK for the [Ajazz AKP03E](https://www.ajazz.com/) stream deck — 9 programmable buttons (6 with LCD displays) and 3 rotary encoders.

Communicates directly via USB HID. No vendor software required.

## Installation

From GitHub:

```bash
pip install git+https://github.com/tomekceszke/ajazz-akp03e.git
# or
uv pip install git+https://github.com/tomekceszke/ajazz-akp03e.git
```

From a downloaded wheel (see [Releases](https://github.com/tomekceszke/ajazz-akp03e/releases)):

```bash
pip install ajazz_akp03e-0.1.0-py3-none-any.whl
# or
uv pip install ajazz_akp03e-0.1.0-py3-none-any.whl
```

From a local clone:

```bash
pip install .
# or
uv pip install .
```

For development:

```bash
pip install -e ".[dev]"
# or
uv pip install -e ".[dev]"
```

## Quick start

```python
from ajazz_akp03e import AKP03E, ButtonPress, KnobTurn

def on_press(event: ButtonPress):
    print(f"Button {event.key} pressed!")

def on_turn(event: KnobTurn):
    direction = "clockwise" if event.direction > 0 else "counter-clockwise"
    print(f"Knob {event.knob} turned {direction}")

with AKP03E() as deck:
    deck.on_button_press(0, on_press)
    deck.on_knob_turn(1, on_turn)
    deck.start()
    deck.wait()  # blocks until Ctrl+C
```

## Device layout

```
 [Knob 0]   [Knob 1]   [Knob 2]      ← rotary encoders (twist + press)
+---------+---------+---------+
|  Key 0  |  Key 1  |  Key 2  |       ← display keys (60×60 LCD)
+---------+---------+---------+
|  Key 3  |  Key 4  |  Key 5  |       ← display keys (60×60 LCD)
+---------+---------+---------+
  [Key 6]   [Key 7]   [Key 8]         ← side buttons (no display)
```

## API

### Connecting

```python
from ajazz_akp03e import AKP03E

# As context manager (recommended)
with AKP03E(brightness=80) as deck:
    ...

# Manual lifecycle
deck = AKP03E()
deck.open()
# ... use the deck ...
deck.close()
```

#### Constructor parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `brightness` | `int` | `0` | Initial display brightness (0–100). Displays start dark. |
| `auto_reconnect` | `bool` | `True` | Reconnect automatically on USB errors |
| `reconnect_delay` | `float` | `2.0` | Seconds between reconnection attempts |

### Registering callbacks

Each method takes a **key/knob index** and a **callback function**. The callback receives a typed event object with a `.device` reference back to the deck.

```python
# Buttons (keys 0–8)
deck.on_button_press(key, callback)    # ButtonPress event
deck.on_button_release(key, callback)  # ButtonRelease event

# Knobs (0–2)
deck.on_knob_turn(knob, callback)      # KnobTurn event (has .direction: -1 or +1)
deck.on_knob_press(knob, callback)     # KnobPress event
deck.on_knob_release(knob, callback)   # KnobRelease event

# Catch-all
deck.on_event(callback)               # receives any Event subclass
```

### Event types

All events carry a `.device` reference to the `AKP03E` instance.

| Event | Attributes | Description |
|---|---|---|
| `ButtonPress` | `.key` (0–8) | Button pressed down |
| `ButtonRelease` | `.key` (0–8) | Button released |
| `KnobTurn` | `.knob` (0–2), `.direction` (-1/+1) | Encoder twisted |
| `KnobPress` | `.knob` (0–2) | Encoder pressed down |
| `KnobRelease` | `.knob` (0–2) | Encoder released |

### Setting button images

Display keys (0–5) have 60×60 pixel LCD screens. Pass a PIL Image, a file path, or raw JPEG bytes:

```python
from PIL import Image

# From a file path — also enable the display
deck.set_key_image(0, "icon.jpg", brightness=50)

# From a file path — image set, brightness unchanged
deck.set_key_image(0, "icon.jpg")

# From a PIL Image
img = Image.new("RGB", (60, 60), (255, 0, 0))
deck.set_key_image(1, img, brightness=80)

# From raw JPEG bytes (must be pre-rotated 270°)
with open("icon.jpg", "rb") as f:
    deck.set_key_image(2, f.read())
```

> **Note:** The SDK automatically resizes to 60×60 and applies the required 270° rotation. When passing raw bytes, they are sent as-is — you must pre-rotate the JPEG yourself.
>
> Displays start dark (`brightness=0`). Pass `brightness=` to `set_key_image()` or call `set_brightness()` to turn them on.

### Other controls

```python
deck.set_brightness(75)     # 0–100
deck.clear_all_images()     # clear all display keys
deck.clear_key_image(0)     # clear a single display key
```

### Display power

```python
deck.sleep()        # displays off, device enters low-power standby
deck.wake()         # wake from standby, restore brightness
deck.keep_alive()   # heartbeat — call periodically to prevent auto-sleep
```

### Running the event loop

```python
deck.start()   # starts background reader thread (non-blocking)
deck.wait()    # blocks until deck.stop() or Ctrl+C
deck.stop()    # signals the reader thread to stop
```

## Full example: home automation controller

```python
import subprocess
from ajazz_akp03e import AKP03E, ButtonPress, KnobTurn

def launch_app(event: ButtonPress):
    subprocess.Popen(["open", "-a", "Ghostty"])

def volume_control(event: KnobTurn):
    delta = 5 * event.direction
    sign = "+" if delta > 0 else "-"
    script = f"set volume output volume ((output volume of (get volume settings)) {sign} {abs(delta)})"
    subprocess.Popen(["osascript", "-e", script])

with AKP03E(brightness=60) as deck:
    deck.on_button_press(0, launch_app)
    deck.on_knob_turn(0, volume_control)
    deck.start()
    deck.wait()
```

## Updating images from callbacks

Since every event carries a `.device` reference, you can update button images directly from within a callback:

```python
from ajazz_akp03e import AKP03E, ButtonPress

light_on = False

def toggle(event: ButtonPress):
    global light_on
    light_on = not light_on
    icon = "on.jpg" if light_on else "off.jpg"
    event.device.set_key_image(event.key, icon)

with AKP03E() as deck:
    deck.on_button_press(1, toggle)
    deck.start()
    deck.wait()
```

## Requirements

- Python 3.11+
- macOS (tested), Linux, Windows
- [hid](https://pypi.org/project/hid/) (installed automatically)
- [Pillow](https://pypi.org/project/Pillow/) (installed automatically)

## Author

[Tomek Ceszke](https://github.com/tomekceszke)

## Acknowledgments

Protocol details were informed by the [ajazz-sdk](https://github.com/mishamyrt/ajazz-sdk) Rust implementation by Misha Myrt.

## License

MIT
