/**
 * NUDGE — API CLIENT
 * All fetch calls to FastAPI (http://localhost:8080) go through here.
 * During Phase 1A development: set USE_MOCKS = true to use mock data.
 * Switch to false once BE-1's server is running.
 */

const BASE_URL = 'http://localhost:8080';
const USE_MOCKS = false; // ← FE-1: flip to false when BE-1 is live

// ─────────────────────────────────────────────
// MOCK DATA  (matches API contract shapes exactly)
// ─────────────────────────────────────────────
const MOCKS = {
  health: { status: 'ok' },

  activity: {
    app_name: 'Google Chrome',
    window_title: 'GitHub - Nudge Project',
    text_elements: ['Pull requests', 'Issues', 'Code'],
    timestamp: new Date().toISOString(),
  },

  tasks: [
    {
      id: 'mock-task-1',
      title: 'Set up FastAPI backend',
      description: 'Scaffold the backend and get /health running',
      estimated_hours: 1,
      estimated_minutes: 0,
      priority: 'High',
      tags: ['backend', 'setup'],
      status: 'In Progress',
      is_recurring: false,
      created_at: new Date().toISOString(),
      completed_at: null,
    },
    {
      id: 'mock-task-2',
      title: 'Build Timer UI',
      description: 'Circular countdown ring with start/pause/reset',
      estimated_hours: 2,
      estimated_minutes: 30,
      priority: 'High',
      tags: ['frontend'],
      status: 'Todo',
      is_recurring: false,
      created_at: new Date().toISOString(),
      completed_at: null,
    },
    {
      id: 'mock-task-3',
      title: 'Write README',
      description: '',
      estimated_hours: 0,
      estimated_minutes: 30,
      priority: 'Low',
      tags: ['docs'],
      status: 'Done',
      is_recurring: false,
      created_at: new Date().toISOString(),
      completed_at: new Date().toISOString(),
    },
  ],

  timerStatus: {
    status: 'idle',
    session_type: 'focus',
    remaining_seconds: 1500,
    session_count: 0,
  },

  summary: {
    summary: null,
    score: null,
    generated_at: null,
  },

  settings: {
    gemini_api_key: '',
    work_duration_minutes: 25,
    short_break_minutes: 5,
    long_break_minutes: 15,
    long_break_after_cycles: 4,
    long_break_enabled: true,
    launch_on_startup: true,
    distraction_detection_enabled: true,
    idle_threshold_seconds: 120,
    distraction_whitelist: [],
  },
};

// ─────────────────────────────────────────────
// HELPERS
// ─────────────────────────────────────────────
async function request(method, path, body) {
  const res = await fetch(`${BASE_URL}${path}`, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

// ─────────────────────────────────────────────
// HEALTH
// ─────────────────────────────────────────────
export async function getHealth() {
  if (USE_MOCKS) return MOCKS.health;
  return request('GET', '/health');
}

// ─────────────────────────────────────────────
// ACTIVITY
// ─────────────────────────────────────────────
export async function getCurrentActivity() {
  if (USE_MOCKS) return { ...MOCKS.activity, timestamp: new Date().toISOString() };
  return request('GET', '/activity/current');
}

// ─────────────────────────────────────────────
// TASKS
// ─────────────────────────────────────────────
export async function getTasks() {
  if (USE_MOCKS) return [...MOCKS.tasks];
  return request('GET', '/tasks');
}

export async function createTask(task) {
  if (USE_MOCKS) {
    const newTask = {
      id: `mock-${Date.now()}`,
      ...task,
      created_at: new Date().toISOString(),
      completed_at: null,
    };
    MOCKS.tasks.unshift(newTask);
    return newTask;
  }
  return request('POST', '/tasks', task);
}

export async function updateTask(id, changes) {
  if (USE_MOCKS) {
    const idx = MOCKS.tasks.findIndex((t) => t.id === id);
    if (idx === -1) throw new Error('Task not found');
    if (changes.status === 'Done' && MOCKS.tasks[idx].status !== 'Done') {
      changes.completed_at = new Date().toISOString();
    }
    MOCKS.tasks[idx] = { ...MOCKS.tasks[idx], ...changes };
    return MOCKS.tasks[idx];
  }
  return request('PUT', `/tasks/${id}`, changes);
}

export async function deleteTask(id) {
  if (USE_MOCKS) {
    const idx = MOCKS.tasks.findIndex((t) => t.id === id);
    if (idx !== -1) MOCKS.tasks.splice(idx, 1);
    return { deleted: true };
  }
  return request('DELETE', `/tasks/${id}`);
}

// ─────────────────────────────────────────────
// TIMER
// ─────────────────────────────────────────────
export async function getTimerStatus() {
  if (USE_MOCKS) return { ...MOCKS.timerStatus };
  return request('GET', '/timer/status');
}

export async function startTimer() {
  if (USE_MOCKS) {
    MOCKS.timerStatus = { status: 'running', session_type: 'focus', remaining_seconds: 1500, session_count: MOCKS.timerStatus.session_count };
    return { ...MOCKS.timerStatus };
  }
  return request('POST', '/timer/start');
}

export async function pauseTimer() {
  if (USE_MOCKS) {
    MOCKS.timerStatus.status = 'paused';
    return { status: 'paused', remaining_seconds: MOCKS.timerStatus.remaining_seconds };
  }
  return request('POST', '/timer/pause');
}

export async function resetTimer() {
  if (USE_MOCKS) {
    MOCKS.timerStatus = { status: 'idle', session_type: 'focus', remaining_seconds: 1500, session_count: 0 };
    return { status: 'idle' };
  }
  return request('POST', '/timer/reset');
}

// ─────────────────────────────────────────────
// SUMMARY
// ─────────────────────────────────────────────
export async function generateSummary() {
  if (USE_MOCKS) {
    const mock = {
      summary: `NUDGE DAILY SUMMARY — ${new Date().toLocaleDateString()}\n━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\nProductivity Score: 7.4 / 10\n\nWhat You Worked On:\n- VS Code (coding) — 3h 20m\n- Google Chrome (docs, GitHub) — 1h 10m\n\nDeep Work Time: 3 hours 20 minutes\nDistraction Time: 40 minutes\n\nTop Distractions:\n- YouTube — 25 minutes\n- Twitter — 15 minutes\n\nBiggest Distraction Pattern:\n- You switched to YouTube consistently after 45 minutes of coding.\n\nOne Suggestion for Tomorrow:\n- Set a browser blocker for the first 2 hours of your workday.`,
      score: 7.4,
      generated_at: new Date().toISOString(),
    };
    MOCKS.summary = mock;
    return mock;
  }
  return request('POST', '/summary/generate');
}

export async function getLatestSummary() {
  if (USE_MOCKS) return { ...MOCKS.summary };
  return request('GET', '/summary/latest');
}

// ─────────────────────────────────────────────
// SETTINGS
// ─────────────────────────────────────────────
export async function getSettings() {
  if (USE_MOCKS) return { ...MOCKS.settings };
  return request('GET', '/settings');
}

export async function saveSettings(changes) {
  if (USE_MOCKS) {
    MOCKS.settings = { ...MOCKS.settings, ...changes };
    return { ...MOCKS.settings };
  }
  return request('POST', '/settings', changes);
}
