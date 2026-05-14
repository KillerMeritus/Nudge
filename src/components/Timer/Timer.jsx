
import { useState, useEffect, useRef } from 'react';
import styles from './Timer.module.css';
import { sendPreset } from '../../utils/notify';
import { playSound } from '../../utils/sound';
import { invoke } from '@tauri-apps/api/core';
import { listen } from '@tauri-apps/api/event';

const MODES = {
  focus:      { id: 'focus',      label: 'Focus',       duration: 25 * 60 },
  shortBreak: { id: 'shortBreak', label: 'Short Break',  duration: 5  * 60 },
  longBreak:  { id: 'longBreak',  label: 'Long Break',   duration: 15 * 60 },
};

/** Format seconds → "MM:SS" */
function fmt(seconds) {
  const m = Math.floor(seconds / 60).toString().padStart(2, '0');
  const s = (seconds % 60).toString().padStart(2, '0');
  return `${m}:${s}`;
}

export default function Timer() {
  const [mode,     setMode]     = useState(MODES.focus.id);
  const [timeLeft, setTimeLeft] = useState(MODES.focus.duration);
  const [isActive, setIsActive] = useState(false);

  // Refs to hold current values inside event callbacks without stale closures
  const isActiveRef = useRef(isActive);
  const modeRef     = useRef(mode);
  const timeLeftRef = useRef(timeLeft);

  useEffect(() => { isActiveRef.current = isActive; }, [isActive]);
  useEffect(() => { modeRef.current     = mode;      }, [mode]);
  useEffect(() => { timeLeftRef.current = timeLeft;  }, [timeLeft]);

  // ── Countdown tick ──────────────────────────────────────────────────────────
  useEffect(() => {
    let interval = null;
    if (isActive && timeLeft > 0) {
      interval = setInterval(() => {
        setTimeLeft((time) => time - 1);
      }, 1000);
    } else if (timeLeft === 0) {
      setIsActive(false);
      // Notify + sound: session finished.
      sendPreset('POMODORO_COMPLETE');
      playSound('pomodoro_complete');
    }
    return () => clearInterval(interval);
  }, [isActive, timeLeft]);

  // ── Push timer state to tray every tick ────────────────────────────────────
  // The Rust `update_tray_timer` command refreshes the tray menu label so the
  // user can see remaining time without opening the window.
  useEffect(() => {
    if (!window.__TAURI_INTERNALS__) return; // no-op in browser dev

    const label = isActive
      ? `${MODES[mode]?.label ?? mode}: ${fmt(timeLeft)} remaining`
      : timeLeft === MODES[mode]?.duration
        ? '' // idle / reset — show default "Idle" in tray
        : `${MODES[mode]?.label ?? mode}: ${fmt(timeLeft)} (paused)`;

    invoke('update_tray_timer', { label }).catch(() => {
      // Silently ignore — tray label update is non-critical
    });
  }, [timeLeft, isActive, mode]);

  // ── Listen for tray menu events emitted by Rust ────────────────────────────
  useEffect(() => {
    if (!window.__TAURI_INTERNALS__) return;

    // "Start Focus Session" from tray menu
    const unlistenStart = listen('tray-start-focus', () => {
      if (!isActiveRef.current) {
        setMode(MODES.focus.id);
        setTimeLeft(MODES.focus.duration);
        setIsActive(true);
        sendPreset('DEEP_WORK_STARTED');
        playSound('deep_work_start');
      }
    });

    // "Pause Timer" from tray menu
    const unlistenPause = listen('tray-pause-timer', () => {
      if (isActiveRef.current) {
        setIsActive(false);
      }
    });

    // Cleanup listeners on unmount
    return () => {
      unlistenStart.then((fn) => fn());
      unlistenPause.then((fn) => fn());
    };
  }, []); // mount-only — reads live values via refs

  // ── Timer controls ─────────────────────────────────────────────────────────
  const toggleTimer = () => {
    const starting = !isActive;
    setIsActive(starting);
    // Fire notification + sound when kicking off a focus session.
    if (starting && mode === 'focus') {
      sendPreset('DEEP_WORK_STARTED');
      playSound('deep_work_start');
    }
  };

  const changeMode = (newModeId) => {
    setMode(newModeId);
    setTimeLeft(MODES[newModeId].duration);
    setIsActive(false);
  };

  const resetTimer = () => {
    setTimeLeft(MODES[mode].duration);
    setIsActive(false);
  };

  const progressPercentage =
    ((MODES[mode].duration - timeLeft) / MODES[mode].duration) * 100;

  return (
    <div className={styles.container}>

      {/* ── MODE SELECTOR ── */}
      <div className={styles.modeSelector}>
        {Object.values(MODES).map((m) => (
          <button
            key={m.id}
            className={`${styles.modeBtn} ${mode === m.id ? styles.modeBtnActive : ''}`}
            onClick={() => changeMode(m.id)}
          >
            {m.label}
          </button>
        ))}
      </div>

      {/* ── PROGRESS RING & TIME ── */}
      <div
        className={styles.timerRing}
        style={{ '--progress': `${progressPercentage}%` }}
      >
        <div className={styles.timeDisplay}>
          {fmt(timeLeft)}
        </div>
      </div>

      {/* ── CONTROLS ── */}
      <div className={styles.controls}>
        <button className={styles.iconBtn} onClick={resetTimer} title="Reset">
          ↻
        </button>
        <button className={styles.playBtn} onClick={toggleTimer}>
          {isActive ? '⏸' : '▶'}
        </button>
        <button
          className={styles.iconBtn}
          onClick={() => changeMode(mode === 'focus' ? 'shortBreak' : 'focus')}
          title="Skip"
        >
          ⏭
        </button>
      </div>

    </div>
  );
}
