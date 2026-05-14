import { useState, useEffect } from 'react';
import styles from './Tasks.module.css';

export default function TaskList() {
  const [tasks, setTasks] = useState([]);
  const [newTaskTitle, setNewTaskTitle] = useState('');

  // Load tasks from backend on startup
  useEffect(() => {
    fetchTasks();
  }, []);

  const fetchTasks = async () => {
    try {
      const response = await fetch("http://localhost:8080/tasks");
      const data = await response.json();
      setTasks(data);
    } catch (error) {
      console.error("Failed to fetch tasks:", error);
    }
  };

  // Add task
  const addTask = async (e) => {
    e.preventDefault();

    if (!newTaskTitle.trim()) return;

    try {
      const response = await fetch("http://localhost:8080/tasks", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          title: newTaskTitle.trim(),
          tags: [],
        }),
      });

      const newTask = await response.json();

      setTasks([newTask, ...tasks]);
      setNewTaskTitle('');
    } catch (error) {
      console.error("Failed to add task:", error);
    }
  };

  // Toggle task complete/incomplete
  const toggleTask = async (id) => {
    const task = tasks.find(t => t.id === id);

    if (!task) return;

    const updatedStatus =
      task.status === "Done" ? "Todo" : "Done";

    try {
      const response = await fetch(`http://localhost:8080/tasks/${id}`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          status: updatedStatus,
        }),
      });

      const updatedTask = await response.json();

      setTasks(tasks.map(t =>
        t.id === id ? updatedTask : t
      ));
    } catch (error) {
      console.error("Failed to update task:", error);
    }
  };

  // Delete task
  const deleteTask = async (id) => {
    try {
      await fetch(`http://localhost:8080/tasks/${id}`, {
        method: "DELETE",
      });

      setTasks(tasks.filter(t => t.id !== id));
    } catch (error) {
      console.error("Failed to delete task:", error);
    }
  };

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h2 className={styles.title}>Tasks</h2>
      </div>

      <form className={styles.taskInputWrapper} onSubmit={addTask}>
        <input
          type="text"
          className={styles.taskInput}
          placeholder="What needs to be done?"
          value={newTaskTitle}
          onChange={(e) => setNewTaskTitle(e.target.value)}
        />

        <button
          type="submit"
          className={styles.addBtn}
          disabled={!newTaskTitle.trim()}
        >
          Add
        </button>
      </form>

      <div className={styles.taskList}>
        {tasks.length === 0 ? (
          <p
            style={{
              color: 'var(--text-muted)',
              textAlign: 'center',
              marginTop: 'var(--space-8)',
            }}
          >
            No tasks yet. Enjoy your day! 🎉
          </p>
        ) : (
          tasks.map(task => (
            <div
              key={task.id}
              className={`${styles.taskItem} ${
                task.status === "Done"
                  ? styles.taskItemCompleted
                  : ''
              }`}
            >
              <input
                type="checkbox"
                className={styles.checkbox}
                checked={task.status === "Done"}
                onChange={() => toggleTask(task.id)}
              />

              <div className={styles.taskContent}>
                <div className={styles.taskTitle}>
                  {task.title}
                </div>

                {task.tags && task.tags.length > 0 && (
                  <div className={styles.taskTags}>
                    {task.tags.map(tag => (
                      <span key={tag} className={styles.tag}>
                        #{tag}
                      </span>
                    ))}
                  </div>
                )}
              </div>

              <button
                className={styles.deleteBtn}
                onClick={() => deleteTask(task.id)}
                title="Delete task"
              >
                ✕
              </button>
            </div>
          ))
        )}
      </div>
    </div>
  );
}