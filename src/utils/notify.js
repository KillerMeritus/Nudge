/**
 * notify.js — Nudge notification utility
 *
 * Wraps @tauri-apps/plugin-notification to provide a clean, reusable
 * sendNotification() function used across the app (Timer, Summary, etc.)
 *
 * Flow:
 *   1. Check / request notification permission from the OS.
 *   2. If granted, send a native desktop notification.
 *   3. If permission denied or running outside Tauri, fall back gracefully.
 */

import {
  isPermissionGranted,
  requestPermission,
  sendNotification as tauriSendNotification,
} from '@tauri-apps/plugin-notification';

// ── Predefined notification presets ──────────────────────────────────────────
// Export these constants so components can reference them by name instead of
// hard-coding strings, keeping notification copy centralised.

export const NOTIFICATIONS = {
  POMODORO_COMPLETE: {
    title: '🍅 Pomodoro Complete',
    body: 'Great focus session! Time to take a well-earned break.',
    sound: 'default',
  },
  DEEP_WORK_STARTED: {
    title: '🧠 Deep Work Session Started',
    body: 'Distractions off. Let\'s get in the zone.',
    sound: 'default',
  },
  SUMMARY_GENERATED: {
    title: '📊 Summary Generated',
    body: 'Your AI productivity summary is ready to view.',
    sound: 'default',
  },
};

// ── Core notification sender ──────────────────────────────────────────────────

/**
 * Send a native desktop notification via Tauri.
 *
 * @param {object} opts
 * @param {string} opts.title   - Notification headline (required)
 * @param {string} opts.body    - Notification body text
 * @param {string} [opts.sound] - Sound identifier ("default" uses OS default)
 *
 * @returns {Promise<void>}
 */
export async function sendNotification({ title, body, sound }) {
  // Guard: bail gracefully when running in a plain browser (not Tauri).
  if (!window.__TAURI_INTERNALS__) {
    console.warn('[Nudge] Notifications only work inside Tauri.', { title, body });
    return;
  }

  try {
    // Step 1 — Check if the OS has already granted permission.
    let permissionGranted = await isPermissionGranted();

    // Step 2 — If not yet granted, ask the user once.
    if (!permissionGranted) {
      const permission = await requestPermission();
      permissionGranted = permission === 'granted';
    }

    // Step 3 — Only send if permission was confirmed.
    if (permissionGranted) {
      tauriSendNotification({
        title,
        body,
        // sound is optional; pass only if provided to avoid API errors
        ...(sound ? { sound } : {}),
      });
    } else {
      console.warn('[Nudge] Notification permission denied by user.');
    }
  } catch (err) {
    // Non-fatal — log the error but do not crash the calling component.
    console.error('[Nudge] Failed to send notification:', err);
  }
}

/**
 * Convenience helper — send a preset notification by key.
 *
 * @param {keyof typeof NOTIFICATIONS} key - One of the NOTIFICATIONS keys
 * @returns {Promise<void>}
 *
 * @example
 *   import { sendPreset } from '@/utils/notify';
 *   await sendPreset('POMODORO_COMPLETE');
 */
export async function sendPreset(key) {
  const preset = NOTIFICATIONS[key];
  if (!preset) {
    console.warn(`[Nudge] Unknown notification preset: "${key}"`);
    return;
  }
  return sendNotification(preset);
}
