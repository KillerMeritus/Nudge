
import { useState } from 'react';
import styles from './Summary.module.css';

export default function Summary() {
  const [isGenerating, setIsGenerating] = useState(false);

  const handleGenerate = () => {
    setIsGenerating(true);
    // TODO: Connect to backend Gemini API in Phase 1B
    setTimeout(() => {
      setIsGenerating(false);
    }, 1500);
  };

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h2 className={styles.title}>Daily Summary</h2>
        <button 
          className={styles.generateBtn} 
          onClick={handleGenerate}
          disabled={isGenerating}
        >
          {isGenerating ? 'Generating...' : '✨ Generate Now'}
        </button>
      </div>

      <div className={styles.summaryCard}>
        <div className={styles.cardHeader}>
          <div className={styles.cardTitle}>
            <span>🤖</span> AI Insights
          </div>
          <div className={styles.date}>
            {new Date().toLocaleDateString('en-US', { weekday: 'long', month: 'short', day: 'numeric' })}
          </div>
        </div>

        <div className={styles.content}>
          <p>
            You had a highly productive morning, focusing heavily on frontend development. 
            However, there was a noticeable drop in focus during the mid-afternoon where 
            you switched between 5 different applications frequently.
          </p>
          <ul>
            <li>Longest focus streak: 85 minutes (VS Code)</li>
            <li>Most distracting app: Discord (opened 14 times)</li>
            <li>Completed 3 major tasks from your checklist.</li>
          </ul>
          <p>
            <strong>Tip for tomorrow:</strong> Try scheduling your hardest tasks before 1 PM 
            when your focus metrics are highest!
          </p>
        </div>

        <div className={styles.metrics}>
          <div className={styles.metricBox}>
            <div className={styles.metricValue}>3h 45m</div>
            <div className={styles.metricLabel}>Deep Work</div>
          </div>
          <div className={styles.metricBox}>
            <div className={styles.metricValue}>72%</div>
            <div className={styles.metricLabel}>Focus Score</div>
          </div>
        </div>
      </div>
    </div>
  );
}
