
import { useState } from 'react';
import styles from './Tasks.module.css';

export default function TaskList() {
  const [tasks, setTasks] = useState([
    { id: '1', title: 'Finish Phase 1A UI', completed: false, tags: ['nudge', 'frontend'] },
    { id: '2', title: 'Review API Contract', completed: true, tags: ['docs'] },
  ]);
  const [newTaskTitle, setNewTaskTitle] = useState('');

  const addTask = (e) => {
    e.preventDefault();
    if (!newTaskTitle.trim()) return;
    
    const newTask = {
      id: Date.now().toString(),
      title: newTaskTitle.trim(),
      completed: false,
      tags: [],
    };
    
    setTasks([newTask, ...tasks]);
    setNewTaskTitle('');
  };

  const toggleTask = (id) => {
    setTasks(tasks.map(t => 
      t.id === id ? { ...t, completed: !t.completed } : t
    ));
  };

  const deleteTask = (id) => {
    setTasks(tasks.filter(t => t.id !== id));
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
          <p style={{ color: 'var(--text-muted)', textAlign: 'center', marginTop: 'var(--space-8)' }}>
            No tasks yet. Enjoy your day! 🎉
          </p>
        ) : (
          tasks.map(task => (
            <div 
              key={task.id} 
              className={`${styles.taskItem} ${task.completed ? styles.taskItemCompleted : ''}`}
            >
              <input 
                type="checkbox" 
                className={styles.checkbox}
                checked={task.completed}
                onChange={() => toggleTask(task.id)}
              />
              <div className={styles.taskContent}>
                <div className={styles.taskTitle}>{task.title}</div>
                {task.tags.length > 0 && (
                  <div className={styles.taskTags}>
                    {task.tags.map(tag => (
                      <span key={tag} className={styles.tag}>#{tag}</span>
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
