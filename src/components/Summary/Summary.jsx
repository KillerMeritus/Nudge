import { useState, useEffect } from 'react';
import styles from './Summary.module.css';
import { sendPreset } from '../../utils/notify';

export default function Summary() {
  const [isGenerating, setIsGenerating] = useState(false);

  const [summaryData, setSummaryData] = useState({
    summary: null,
    score: null,
    generated_at: null,
  });

  // Load latest summary on startup
  useEffect(() => {
    fetchLatestSummary();
  }, []);

  const fetchLatestSummary = async () => {
    try {
      const response = await fetch("http://localhost:8080/summary/latest");
      const data = await response.json();

      setSummaryData(data);
    } catch (error) {
      console.error("Failed to fetch latest summary:", error);
    }
  };

  // Generate summary
  const handleGenerate = async () => {
    setIsGenerating(true);

    try {
      const response = await fetch(
        "http://localhost:8080/summary/generate",
        {
          method: "POST",
        }
      );

      const data = await response.json();

      console.log("Generated summary:", data);

      setSummaryData(data);

      // Notify the user that their AI summary is ready.
      await sendPreset('SUMMARY_GENERATED');
    } catch (error) {
      console.error("Summary generation failed:", error);

      alert(
        "Failed to generate summary. Make sure Gemini API key is added in Settings."
      );
    } finally {
      setIsGenerating(false);
    }
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
          {isGenerating ? "Generating..." : "✨ Generate Now"}
        </button>
      </div>

      <div className={styles.summaryCard}>
        <div className={styles.cardHeader}>
          <div className={styles.cardTitle}>
            <span>🤖</span> AI Insights
          </div>

          <div className={styles.date}>
            {summaryData.generated_at
              ? new Date(summaryData.generated_at).toLocaleDateString(
                  "en-US",
                  {
                    weekday: "long",
                    month: "short",
                    day: "numeric",
                  }
                )
              : "No summary yet"}
          </div>
        </div>

        <div className={styles.content}>
          {summaryData.summary ? (
            <pre
              style={{
                whiteSpace: "pre-wrap",
                fontFamily: "inherit",
                lineHeight: "1.6",
              }}
            >
              {summaryData.summary}
            </pre>
          ) : (
            <p>
              No summary generated yet. Click{" "}
              <strong>Generate Now</strong> to create your AI productivity
              summary.
            </p>
          )}
        </div>

        <div className={styles.metrics}>
          <div className={styles.metricBox}>
            <div className={styles.metricValue}>
              {summaryData.score
                ? `${summaryData.score}/10`
                : "--"}
            </div>

            <div className={styles.metricLabel}>
              Productivity Score
            </div>
          </div>

          <div className={styles.metricBox}>
            <div className={styles.metricValue}>
              {summaryData.generated_at
                ? "Generated"
                : "Waiting"}
            </div>

            <div className={styles.metricLabel}>
              Summary Status
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}