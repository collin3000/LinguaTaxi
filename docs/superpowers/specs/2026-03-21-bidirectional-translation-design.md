# Bi-Directional Translation — Design Spec

## Problem

LinguaTaxi currently supports one-way captioning: a single input language is transcribed and translated to up to 5 target languages. Real-world scenarios require simultaneous back-and-forth translation between two languages — e.g., one person speaks Arabic, another responds in English, and both need to see captions in their own language.

## Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Display output | Two zones, one per language, color-coded original vs translated | Clear separation for each audience |
| Language detection | Hybrid: auto-detect with operator override via speaker buttons | Hands-free default with safety net |
| Display presentation | Both split-screen (single page) and separate windows available | Flexibility for different venue setups |
| CPU language detector | Silero lang_detector_95 (ONNX, MIT, 4.7MB, <1ms) | Best speed/size/license/accuracy balance |
| Translation slots | Auto-manage 2 slots for reverse translations; 3 more available for observers | Keeps existing slot system working |
| Whisper model strategy | Single base model by default; optional tuned model hot-swap (operator toggle) | Smooth default experience with opt-in accuracy |
| Vosk model availability | Integrated with installer + launcher download dialogs; bi-directional greyed out if missing | Follows existing download patterns |
| Operator UI | Toggle switch revealing input language selectors and controls | Discoverable, clear state |

## Architecture

### Approach: Detection-First with Lazy Model Loading

Audio flows through the existing buffer loop. When bi-directional mode is enabled, language detection runs on the first ~1-1.5s of each speech segment during the silence-detection phase. The detected language is attached as metadata to the segment, routing it to the correct transcription model and triggering the appropriate reverse translation.

```
Audio → Buffer Loop → Silence Detected → Detect Language → Tag Segment
  → Transcription (correct model/language) → Auto-translate to other input language
  → Broadcast with language metadata → Display renders with color coding
```

Silero runs on CPU alongside any backend (<1ms overhead). For GPU/Whisper users, faster-whisper's built-in detection is also available. Detection is narrowed to the operator's 2 selected input languages for higher effective accuracy.

### End-to-End Data Flow (detected_lang propagation)

The `detected_lang` parameter must be threaded through the entire call chain:

```
_buffer_audio_loop:  detect_language(audio) → detected_lang
  → _transcription_queue.put((source, buf, detected_lang))
    → _transcription_worker:  source, buf, detected_lang = queue.get()
      → transcribe_fn(buf, lang=detected_lang)  [signature change: add lang param]
        → _broadcast_final(text, loop, source, detected_lang)  [signature change]
          → WebSocket msg: {"type":"final", ..., "detected_lang":"ar"}
          → _translate_all(text, line_id, loop, source_lang=detected_lang)  [signature change]
            → _do_translate(text, slot, line_id, loop, source_lang=detected_lang)  [signature change]
              → translate_text(text, target_lang, source_lang=detected_lang, mode=mode)
```

When bi-directional mode is off, `detected_lang` defaults to `None` at every hop, and each function falls back to `config.get("input_lang")` — preserving existing behavior. The queue tuple always uses 3 elements; the worker always unpacks 3.

### Simultaneous Speech (Known Limitation)

When both speakers talk at the same time over a single microphone, the audio contains mixed languages. Silero's detection on mixed audio will return low confidence. Behavior:
- If confidence < 0.6: fall back to the last known language for that source
- The resulting transcription may be partially garbled regardless of language choice — this is inherent to overlapping speech in any single-mic setup
- **Best practice:** use separate microphones per speaker (separate audio sources), which isolates each language stream entirely. The operator panel already supports multiple audio sources.
- This is documented as a known limitation in the operator guide, not a bug to fix.

## Section 1: Language Detection Layer

### Silero Integration (CPU path — all backends)

- New module `lang_detect.py` wraps Silero lang_detector_95
- Loads ONNX model (~4.7MB) on first use, stays in memory
- Exposes `detect_language(audio_chunk, candidates=["ar","en"]) → (lang_code, confidence)`
- The `candidates` parameter restricts detection to the operator's 2 selected input languages, boosting effective accuracy well above the baseline 85%
- Runs on the first ~1-1.5s of audio accumulated in the buffer loop, during the silence-detection phase before the segment is submitted for transcription

### Whisper Integration (GPU path — additional)

- When Whisper is the backend, faster-whisper's built-in `detect_language()` can serve as primary or cross-check detector
- Silero still loads as fallback (e.g., if Whisper model is being swapped)

### Detection Trigger

- Detection runs once per speech segment — when the buffer loop first accumulates >=1s of speech audio after silence
- Result is attached to the segment as metadata: `(source_id, audio_buffer, detected_lang)`
- If confidence is below a threshold (e.g., <0.6), fall back to the last known language for that source

### Vosk Model Management

- Both Vosk language models stay loaded in memory (~40-80MB each)
- Each gets its own `KaldiRecognizer` instance, pre-initialized
- Detection result routes audio to the correct recognizer
- If the language changes between segments, the old recognizer is reset and the new one receives the audio
- Model loading: both Vosk models are loaded when bi-directional mode is enabled (not at server startup). Loading a Vosk model takes 1-3 seconds — the operator panel shows a brief "Loading models..." status during this time
- With 8 max sources × 2 recognizers = 16 KaldiRecognizer instances possible, but memory impact is minimal since recognizers share the underlying model object
- When bi-directional mode is toggled off, the second Vosk model and its recognizers are unloaded to free memory

## Section 2: Transcription Pipeline Changes

### Buffer Loop Modifications (`_buffer_audio_loop`)

- When bi-directional mode is enabled, after silence detection triggers and >=1s of audio is accumulated, call `detect_language()` before submitting to the transcription queue
- The segment tuple on the queue changes from `(source, buffer)` to `(source, buffer, detected_lang)` — backwards compatible by defaulting `detected_lang=None` when bi-directional is off
- The detected language is also stored on the `AudioSource` object as `source.current_lang` so interim transcriptions can use the right language

### Whisper Transcription Worker

- Currently passes hardcoded `config.get("input_lang")` to `model.transcribe(language=...)`
- In bi-directional mode, uses the segment's `detected_lang` instead
- Base model (default): just passes the detected language code — no model swap needed, large-v3-turbo handles both
- Tuned model mode (operator opt-in): if detected language differs from currently loaded model's language, triggers hot-swap via existing `tuned_models.py` infrastructure, then transcribes. Swap takes ~1-1.5s

### Vosk Transcription

- Vosk uses per-source streaming, not the shared queue — it processes audio continuously
- In bi-directional mode, each source maintains two `KaldiRecognizer` instances (one per language)
- When Silero detects a language change: force-finalize the current recognizer (same pattern used for speaker changes today), then route subsequent audio to the other recognizer
- This reuses the existing Vosk force-finalize mechanism from speaker change handling

### Segment Metadata

- Final transcription results now carry `lang` field alongside existing `speaker`, `source_id`, etc.
- This flows through to translation and display broadcasting

## Section 3: Translation Routing

### Auto-managed Bi-directional Slots

- When bi-directional mode is enabled, the system auto-creates 2 translation slots at positions 0 and 1:
  - Slot 0: translates to Language A (for segments detected as Language B)
  - Slot 1: translates to Language B (for segments detected as Language A)
- These slots are locked in the operator UI — the operator cannot delete or reconfigure them while bi-directional mode is on

### Smart Translation per Segment

- When a final caption arrives with `detected_lang`, the translation router checks:
  - If segment is Language A → translate to Language B (slot 1) — skip slot 0 (already in Language A)
  - If segment is Language B → translate to Language A (slot 0) — skip slot 1 (already in Language B)
- Each segment only triggers one bi-directional translation, not two — halving the translation load

### Observer Slots

- Slots 2+ remain available for the operator to configure additional target languages (e.g., French, German for observers)
- Observer slots translate every segment regardless of detected language — they always translate from whatever was spoken to their target language
- The translation engine needs the correct source language per segment, which is now available from `detected_lang`

### Translation Engine Selection

- Bi-directional slots use the same engine selection as today (DeepL, offline-OPUS, offline-M2M)
- The source language parameter is now dynamic per segment instead of the static `config.input_lang`
- `translate_text()` already accepts `source_lang` — the full call chain (`_broadcast_final` → `_translate_all` → `_do_translate` → `translate_text`) must thread `source_lang=detected_lang` at every hop (see End-to-End Data Flow above)
- For DeepL target codes that require variants (e.g., EN→EN-US, PT→PT-BR, ZH→ZH-HANS): auto-managed bi-directional slots default to the most common variant; operator can override in the slot config if needed. The variant mapping is defined in a `DEEPL_TARGET_DEFAULTS` dict in `server.py`

## Section 4: Display & Broadcasting

### WebSocket Message Changes

- Final/interim messages gain two new fields:
  - `detected_lang`: the language code of the original speech (e.g., `"ar"`, `"en"`)
  - `is_translation`: boolean — `false` for original transcription, `true` for translated text
- Translation messages already carry `slot` and `lang` — no changes needed there
- These fields enable the display to color-code original vs translated text

### Bi-directional Display Page (`bidirectional.html`)

- New HTML page served from the existing display app on `:3000` at path `/bidirectional`
- Supports two modes via URL parameters:
  - `?lang=EN` — single-language mode: shows all captions in English (originals + translations), color-coded to distinguish native speech from translated
  - `?mode=split` — split-screen mode: left/right (or top/bottom) zones, one per input language, each showing everything translated into that language
- Both modes receive the same WebSocket messages — the rendering logic differs

### Color Coding

- Each display zone has two colors:
  - Primary color: text that was originally spoken in this zone's language
  - Secondary color (e.g., dimmer/italic): text that was translated into this zone's language
- Colors configurable from the operator panel (extends existing style controls)

### Operator Panel Integration

- Operator panel shows a detection indicator — which language is currently detected per source
- The existing display/extended windows continue working for observer translation slots
- Operator can open `bidirectional.html` windows from a new button in the browser section

## Section 5: Operator Panel UI

### Bi-directional Toggle

- New "Bi-directional Mode" toggle switch in the operator panel, placed above the existing translation slot controls
- When toggled on, reveals:
  - Two dropdowns: "Input Language A" and "Input Language B" (populated from the same language list used for translation targets)
  - A checkbox: "Use tuned model when available (adds ~1s swap delay)" — only visible when Whisper backend is active and a tuned model is installed for one of the selected languages
  - A live detection indicator per source showing which language is currently detected with a small confidence badge

### Speaker Button Language Assignment

- Existing speaker buttons gain an optional language dropdown (hidden by default, shown in bi-directional mode)
- When a speaker is assigned a language, that overrides auto-detection for that speaker — when the operator presses that speaker button, the system skips Silero/Whisper detection and uses the assigned language
- When no language is assigned (default), auto-detection is used — the hybrid approach

### Translation Slot Changes

- When bi-directional mode is on, slots 0-1 show as locked/auto-managed with labels like "Arabic → English (auto)" and "English → Arabic (auto)"
- The "Add Translation" controls start from slot 2, with the operator able to add up to 3 more observer languages
- When bi-directional mode is toggled off, the auto-managed slots are removed and full manual control returns
- In-flight translations in auto-managed slots are allowed to complete; no new translations are started for those slots after toggle-off
- Existing caption lines on displays remain visible; only new segments follow the updated mode
- Segments in the transcription queue with `detected_lang` set are still transcribed normally — the lang parameter is valid regardless of mode

### Config Persistence

- Bi-directional settings saved in `config.json`: `bidirectional_enabled`, `bidirectional_langs` (array of 2), `bidirectional_tuned_swap`, speaker language assignments
- WebSocket broadcasts config changes to all clients as today

## Section 6: Vosk Model Download System

### Installer Integration (Windows)

- Add Vosk language models as optional install tasks in `installer.iss`, following the existing pattern for tuned Whisper models and offline translation models
- New task group "Vosk Language Models" with checkboxes per language
- Models downloaded from the Vosk model repository during install

### Launcher Download Dialog

- New "Download Vosk Models" button in the launcher settings (alongside existing "Download tuned models" and "Download offline models" buttons)
- Dialog lists available Vosk language models with size estimates, installed status, and checkboxes
- Download runs in background thread with progress tracking — same pattern as the tuned models dialog

### Bi-directional Mode Availability Check

- When the operator enables bi-directional mode and selects two input languages, the system checks:
  - Whisper backend: always available (base model handles all languages)
  - Vosk backend: checks if both language models are installed in `MODELS_DIR/`
- If a Vosk model is missing, the operator sees a message: "Vosk model for [language] not installed. Download from launcher settings." Bi-directional mode stays disabled until both models are available.

### Model Storage

- Vosk models stored at `MODELS_DIR/vosk-model-{lang}-{size}/` — same pattern as the existing English model
- `server.py` discovers available Vosk models at startup and reports them via a `/api/vosk-models` endpoint for the operator panel to query

## Section 7: New Files & Module Boundaries

### New files

- `lang_detect.py` (~100-150 lines) — Silero wrapper: load ONNX model, `detect_language(audio, candidates)`, model download helper
- `bidirectional.html` (~300-400 lines) — new display page with split-screen and single-language modes, WebSocket client, color-coded rendering

### Modified files

- `server.py` — buffer loop detection hook, transcription queue metadata, translation routing logic, bi-directional config endpoints, Vosk dual-recognizer management, WebSocket message fields
- `operator.html` — bi-directional toggle, input language selectors, speaker language assignment, locked slot display, detection indicator
- `launcher.pyw` — Vosk model download dialog button and dialog
- `installer.iss` — Vosk language model optional tasks
- `download_models.py` — Vosk multi-language model download support

### Not modified

- `display.html` — existing display continues to work as-is for observer slots
- `offline_translate.py` — already accepts dynamic source language, no changes needed
- `tuned_models.py` — hot-swap infrastructure already exists, no changes needed

### Dependencies added

- `onnxruntime` — for Silero ONNX inference (lightweight, no PyTorch needed on CPU edition)
- Silero lang_detector_95 ONNX model (~4.7MB) — stored in `MODELS_DIR/silero-lang-detect/`, downloaded on first use or bundled in installer
- `onnxruntime` version floor: `>=1.16.0` (supports ONNX opset used by Silero). Use `onnxruntime` (CPU), not `onnxruntime-gpu`
- If `onnxruntime` is unavailable at runtime: Whisper users fall back to faster-whisper's built-in `detect_language()`; Vosk-only users see an error prompting them to install onnxruntime
