const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const api = {
  // Health
  async getHealth() {
    const res = await fetch(`${API_BASE_URL}/health`);
    if (!res.ok) throw new Error('Failed to fetch health status');
    return res.json();
  },

  // Models
  async getModelsConfig() {
    const res = await fetch(`${API_BASE_URL}/api/models/config`);
    if (!res.ok) throw new Error('Failed to fetch models configuration');
    return res.json();
  },

  async getModelsStatus() {
    const res = await fetch(`${API_BASE_URL}/api/models/status`);
    if (!res.ok) throw new Error('Failed to fetch models status');
    return res.json();
  },

  // Tasks
  async getTasks() {
    const res = await fetch(`${API_BASE_URL}/api/tasks`);
    if (!res.ok) throw new Error('Failed to fetch tasks');
    return res.json();
  },

  async getTask(taskId) {
    const res = await fetch(`${API_BASE_URL}/api/tasks/${taskId}`);
    if (!res.ok) throw new Error(`Failed to fetch task ${taskId}`);
    return res.json();
  },

  // Experiments
  async runExperiment(params) {
    const res = await fetch(`${API_BASE_URL}/api/experiments`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Failed to run experiment' }));
      throw new Error(err.detail || 'Experiment execution failed');
    }
    return res.json();
  },

  async runBatchExperiments(params) {
    const res = await fetch(`${API_BASE_URL}/api/experiments/batch`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Batch execution failed' }));
      throw new Error(err.detail || 'Batch execution failed');
    }
    return res.json();
  },

  async getExperiments(topology = null, success = null) {
    const query = new URLSearchParams();
    if (topology) query.append('topology', topology);
    if (success !== null) query.append('success', success);
    const res = await fetch(`${API_BASE_URL}/api/experiments?${query.toString()}`);
    if (!res.ok) throw new Error('Failed to list experiments');
    return res.json();
  },

  async getExperiment(experimentId) {
    const res = await fetch(`${API_BASE_URL}/api/experiments/${experimentId}`);
    if (!res.ok) throw new Error(`Failed to fetch experiment ${experimentId}`);
    return res.json();
  },

  async getExperimentMessages(experimentId) {
    const res = await fetch(`${API_BASE_URL}/api/experiments/${experimentId}/messages`);
    if (!res.ok) throw new Error('Failed to fetch messages');
    return res.json();
  },

  async getExperimentNetwork(experimentId) {
    const res = await fetch(`${API_BASE_URL}/api/experiments/${experimentId}/network`);
    if (!res.ok) throw new Error('Failed to fetch network graph');
    return res.json();
  },

  async deleteExperiment(experimentId) {
    const res = await fetch(`${API_BASE_URL}/api/experiments/${experimentId}`, {
      method: 'DELETE',
    });
    if (!res.ok) throw new Error('Failed to delete experiment');
    return res.json();
  },

  async clearAllExperiments() {
    const res = await fetch(`${API_BASE_URL}/api/experiments`, {
      method: 'DELETE',
    });
    if (!res.ok) throw new Error('Failed to clear experiments');
    return res.json();
  },

  // Results & Statistics
  async getResultsSummary() {
    const res = await fetch(`${API_BASE_URL}/api/results/summary`);
    if (!res.ok) throw new Error('Failed to fetch results summary');
    return res.json();
  },

  async getStatisticalAnalysis() {
    const res = await fetch(`${API_BASE_URL}/api/results/statistics`);
    if (!res.ok) throw new Error('Failed to fetch statistical analysis');
    return res.json();
  },

  async exportResearchDataset() {
    const res = await fetch(`${API_BASE_URL}/api/results/export`);
    if (!res.ok) throw new Error('Failed to export research dataset');
    return res.json();
  },
};
