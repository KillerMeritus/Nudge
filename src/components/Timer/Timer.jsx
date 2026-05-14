
import { useState, useEffect } from 'react';
import styles from './Timer.module.css';
import { sendPreset } from '../../utils/notify';
import { playSound } from '../../utils/sound';

const MODES = {
  focus: { id: 'focus', label: 'Focus', duration: 25 * 60 },
  shortBreak: { id: 'shortBreak', label: 'Short Break', duration: 5 * 60 },
  longBreak: { id: 'longBreak', label: 'Long Break', duration: 15 * 60 },
};

export default function Timer() {
  const [mode, setMode] = useState(MODES.focus.id);
  const [timeLeft, setTimeLeft] = useState(MODES.focus.duration);
  const [isActive, setIsActive] = useState(false);

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

  const formatTime = (seconds) => {
    const m = Math.floor(seconds / 60).toString().padStart(2, '0');
    const s = (seconds % 60).toString().padStart(2, '0');
    return `${m}:${s}`;
  };

  const progressPercentage = ((MODES[mode].duration - timeLeft) / MODES[mode].duration) * 100;

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
          {formatTime(timeLeft)}
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
        <button className={styles.iconBtn} onClick={() => changeMode(mode === 'focus' ? 'shortBreak' : 'focus')} title="Skip">
          ⏭
        </button>
      </div>

    </div>
  );
}
