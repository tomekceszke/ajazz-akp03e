# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-03-29

### Added
- Initial release
- `AKP03E` device class with context manager support
- Callback-based event handling: `on_button_press`, `on_button_release`, `on_knob_turn`, `on_knob_press`, `on_knob_release`, `on_event`
- Button display image support via `set_key_image` (PIL Image, file path, or raw JPEG bytes)
- `set_brightness`, `clear_all_images`, `clear_key_image`
- Auto-reconnect on USB errors
- Thread-safe background event reader
- Full type annotations and `py.typed` marker

[Unreleased]: https://github.com/tomekceszke/ajazz-akp03e/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/tomekceszke/ajazz-akp03e/releases/tag/v0.1.0
