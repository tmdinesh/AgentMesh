import React, { useState, useEffect } from 'react';
import Navbar from './components/Navbar';
import DashboardPage from './pages/DashboardPage';
import RunExperimentPage from './pages/RunExperimentPage';
import ExperimentDetailPage from './pages/ExperimentDetailPage';
import ComparisonPage from './pages/ComparisonPage';
import TasksPage from './pages/TasksPage';
import { api } from './services/api';

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [selectedExperimentId, setSelectedExperimentId] = useState(null);
  const [preselectedTaskId, setPreselectedTaskId] = useState(null);
  const [healthInfo, setHealthInfo] = useState(null);
  const [theme, setTheme] = useState(() => localStorage.getItem('mast_theme') || 'dark');

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('mast_theme', theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme((prev) => (prev === 'dark' ? 'light' : 'dark'));
  };

  // Poll backend health
  useEffect(() => {
    const checkHealth = async () => {
      try {
        const info = await api.getHealth();
        setHealthInfo(info);
      } catch (err) {
        setHealthInfo(null);
      }
    };
    checkHealth();
    const interval = setInterval(checkHealth, 15000);
    return () => clearInterval(interval);
  }, []);

  const handleSelectExperiment = (expId) => {
    setSelectedExperimentId(expId);
    setActiveTab('details');
  };

  const handleRunTask = (taskId) => {
    setPreselectedTaskId(taskId);
    setActiveTab('run');
  };

  const handleExperimentCompleted = (expId) => {
    if (expId) {
      setSelectedExperimentId(expId);
      setActiveTab('details');
    } else {
      setActiveTab('dashboard');
    }
  };

  return (
    <div className="app-container">
      <Navbar
        activeTab={activeTab}
        setActiveTab={(tab) => {
          setActiveTab(tab);
          if (tab !== 'details') setSelectedExperimentId(null);
        }}
        healthInfo={healthInfo}
        theme={theme}
        onToggleTheme={toggleTheme}
      />

      <main className="main-content">
        {activeTab === 'dashboard' && (
          <DashboardPage
            onSelectExperiment={handleSelectExperiment}
            onRunNew={() => setActiveTab('run')}
          />
        )}

        {activeTab === 'run' && (
          <RunExperimentPage
            preselectedTaskId={preselectedTaskId}
            onExperimentCompleted={handleExperimentCompleted}
          />
        )}

        {activeTab === 'details' && selectedExperimentId && (
          <ExperimentDetailPage
            experimentId={selectedExperimentId}
            onBack={() => setActiveTab('dashboard')}
          />
        )}

        {activeTab === 'compare' && (
          <ComparisonPage
            onRunBatch={() => setActiveTab('run')}
          />
        )}

        {activeTab === 'tasks' && (
          <TasksPage
            onRunTask={handleRunTask}
          />
        )}
      </main>
    </div>
  );
}
