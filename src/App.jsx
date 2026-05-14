import { useState } from 'react';
import './styles/global.css';
import Timer from './components/Timer/Timer';
import TaskList from './components/Tasks/TaskList';
import Summary from './components/Summary/Summary';
import Settings from './components/Settings/Settings';
import styles from './App.module.css';
// [DEV] Notification utility — remove demo button before shipping v1
import { sendPreset } from './utils/notify';

const TABS = [
  { id: 'timer',    label: '⏱ Timer' },
  { id: 'tasks',    label: '✅ Tasks' },
  { id: 'summary',  label: '📊 Summary' },
  { id: 'settings', label: '⚙️ Settings' },
];

export default function App() {
  const [activeTab, setActiveTab] = useState('timer');

  return (
    <div className={styles.shell}>
      {/* ── NAV BAR ── */}
      <nav className={styles.nav}>
        <span className={styles.logo}>Nudge</span>
        <div className={styles.tabs} role="tablist">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              id={`tab-${tab.id}`}
              role="tab"
              aria-selected={activeTab === tab.id}
              className={`${styles.tab} ${activeTab === tab.id ? styles.tabActive : ''}`}
              onClick={() => setActiveTab(tab.id)}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* [DEV] Temporary — test all three notification presets. Remove before v1 release. */}
        <button
          id="dev-test-notifications"
          title="Dev: test notifications"
          style={{
            marginLeft: 'auto',
            padding: '4px 10px',
            fontSize: '11px',
            opacity: 0.5,
            cursor: 'pointer',
            borderRadius: '6px',
            border: '1px solid currentColor',
            background: 'transparent',
            color: 'inherit',
          }}
          onClick={async () => {
            // Fire each preset with a 1-second gap so macOS groups them separately.
            await sendPreset('DEEP_WORK_STARTED');
            setTimeout(() => sendPreset('POMODORO_COMPLETE'), 1000);
            setTimeout(() => sendPreset('SUMMARY_GENERATED'), 2000);
          }}
        >
          🔔 Test
        </button>
      </nav>

      {/* ── CONTENT ── */}
      <main className={styles.content}>
        {activeTab === 'timer'    && <Timer />}
        {activeTab === 'tasks'    && <TaskList />}
        {activeTab === 'summary'  && <Summary />}
        {activeTab === 'settings' && <Settings />}
      </main>
    </div>
  );
}
