import { useState } from 'react';
import './styles/global.css';
import Timer from './components/Timer/Timer';
import TaskList from './components/Tasks/TaskList';
import Summary from './components/Summary/Summary';
import Settings from './components/Settings/Settings';
import styles from './App.module.css';

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
