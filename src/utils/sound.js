/**
 * sound.js — Nudge sound-alert utility
 *
 * Plays short synthesised tones using the Web Audio API.
 * No external audio files are required — tones are generated at runtime,
 * which means zero latency, guaranteed availability, and macOS compatibility
 * inside Tauri without any asset-bundling ceremony.
 *
 * Public API:
 *   playSound(key)   — play a named preset tone  (e.g. "pomodoro_complete")
 *
 * How it works:
 *   1. A shared AudioContext is lazily created on first use.
 *   2. Each preset defines a sequence of { freq, duration } notes.
 *   3. OscillatorNode + GainNode chain produces the tone; gain ramps to 0
 *      at the end to avoid clicks (click = abrupt waveform cutoff).
 *   4. If AudioContext is blocked (autoplay policy) or Web Audio is
 *      unavailable, we fall back gracefully with a console.warn.
 */

// ── Shared AudioContext (lazy singleton) ──────────────────────────────────────
// AudioContext must be created / resumed after a user gesture on some browsers,
// but inside Tauri this restriction is relaxed. We create it on first playSound()
// call so we never block module initialisation.

let _audioCtx = null;

function getAudioContext() {
  if (!_audioCtx) {
    try {
      _audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    } catch {
      return null;
    }
  }
  // Resume in case the context was suspended (e.g. opened before user gesture)
  if (_audioCtx.state === 'suspended') {
    _audioCtx.resume().catch(() => {});
  }
  return _audioCtx;
}

// ── Note player ───────────────────────────────────────────────────────────────

/**
 * Play a single synthesised tone.
 *
 * @param {AudioContext} ctx
 * @param {number} freq        - Frequency in Hz
 * @param {number} startTime   - AudioContext time (seconds) to start
 * @param {number} duration    - Duration in seconds
 * @param {number} [gain=0.4]  - Peak volume (0–1)
 * @param {'sine'|'triangle'|'square'|'sawtooth'} [type='sine']
 */
function playNote(ctx, freq, startTime, duration, gain = 0.4, type = 'sine') {
  const osc = ctx.createOscillator();
  const gainNode = ctx.createGain();

  osc.type = type;
  osc.frequency.setValueAtTime(freq, startTime);

  // Smooth attack + decay to prevent audio clicks
  gainNode.gain.setValueAtTime(0, startTime);
  gainNode.gain.linearRampToValueAtTime(gain, startTime + 0.01);       // 10ms attack
  gainNode.gain.linearRampToValueAtTime(0, startTime + duration - 0.01); // fade out

  osc.connect(gainNode);
  gainNode.connect(ctx.destination);

  osc.start(startTime);
  osc.stop(startTime + duration);
}

// ── Sound presets ─────────────────────────────────────────────────────────────
// Each preset is an array of note descriptors:
//   { freq, duration, gain?, type? }
// Notes are played sequentially; offset accumulates automatically.

const SOUND_PRESETS = {
  /**
   * pomodoro_complete — ascending three-note chime: warm, satisfying.
   * Signals the end of a focus/break session.
   */
  pomodoro_complete: [
    { freq: 523.25, duration: 0.18, gain: 0.35 }, // C5
    { freq: 659.25, duration: 0.18, gain: 0.35 }, // E5
    { freq: 783.99, duration: 0.30, gain: 0.40 }, // G5
  ],

  /**
   * deep_work_start — short descending two-tone "begin" cue:
   * calm but purposeful, signals focus is starting.
   */
  deep_work_start: [
    { freq: 440.00, duration: 0.14, gain: 0.30 }, // A4
    { freq: 349.23, duration: 0.22, gain: 0.35 }, // F4
  ],

  /**
   * summary_generated — bright single chime: light, informational.
   */
  summary_generated: [
    { freq: 880.00, duration: 0.12, gain: 0.28 }, // A5
    { freq: 1046.5, duration: 0.20, gain: 0.32 }, // C6
  ],
};

// ── Public API ────────────────────────────────────────────────────────────────

/**
 * Play a named sound preset.
 *
 * @param {keyof typeof SOUND_PRESETS} key  - Preset name
 * @returns {void}
 *
 * @example
 *   import { playSound } from '../utils/sound';
 *   playSound('pomodoro_complete');
 */
export function playSound(key) {
  // Step 1 — Resolve preset
  const preset = SOUND_PRESETS[key];
  if (!preset) {
    console.warn(`[Nudge/sound] Unknown sound key: "${key}". Valid keys: ${Object.keys(SOUND_PRESETS).join(', ')}`);
    return;
  }

  // Step 2 — Get (or create) the shared AudioContext
  const ctx = getAudioContext();
  if (!ctx) {
    console.warn('[Nudge/sound] Web Audio API not available — skipping sound alert.');
    return;
  }

  // Step 3 — Schedule all notes sequentially
  let cursor = ctx.currentTime + 0.05; // tiny lead-in to avoid first-note click

  for (const note of preset) {
    playNote(ctx, note.freq, cursor, note.duration, note.gain ?? 0.4, note.type ?? 'sine');
    cursor += note.duration + 0.02; // small gap between notes
  }
}
