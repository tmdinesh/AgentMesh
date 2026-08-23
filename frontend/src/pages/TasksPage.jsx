import React, { useState, useEffect } from 'react';
import { BookOpen, PlayCircle, Search, Filter, CheckCircle2, HelpCircle } from 'lucide-react';
import { api } from '../services/api';

export default function TasksPage({ onRunTask }) {
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedCategory, setSelectedCategory] = useState('ALL');
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    const fetchTasks = async () => {
      setLoading(true);
      try {
        const data = await api.getTasks();
        setTasks(data);
      } catch (err) {
        console.error('Failed to load tasks:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchTasks();
  }, []);

  const filteredTasks = tasks.filter((t) => {
    if (selectedCategory !== 'ALL' && t.category !== selectedCategory) return false;
    if (searchTerm && !t.title.toLowerCase().includes(searchTerm.toLowerCase()) && !t.question.toLowerCase().includes(searchTerm.toLowerCase())) {
      return false;
    }
    return true;
  });

  const getDifficultyBadge = (diff) => {
    if (diff === 'Easy') return <span className="badge badge-success">Easy</span>;
    if (diff === 'Hard') return <span className="badge badge-danger">Hard</span>;
    return <span className="badge badge-warning">Medium</span>;
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 16 }}>
        <div>
          <h1 style={{ fontSize: 24, fontWeight: 800, letterSpacing: '-0.02em', marginBottom: 4 }}>Benchmark Tasks Library</h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: 14 }}>
            Curated scientific evaluation benchmarks across Reasoning, Question Answering, and Strategic Decision/Summary domains.
          </p>
        </div>
      </div>

      {/* Filter Toolbar */}
      <div
        className="card"
        style={{
          padding: '14px 20px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: 12,
        }}
      >
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          {['ALL', 'Reasoning', 'Question Answering', 'Decision/Summary'].map((cat) => (
            <button
              key={cat}
              onClick={() => setSelectedCategory(cat)}
              className={`btn ${selectedCategory === cat ? 'btn-primary' : 'btn-secondary'}`}
              style={{ fontSize: 12, padding: '6px 14px' }}
            >
              {cat}
            </button>
          ))}
        </div>

        <div style={{ position: 'relative' }}>
          <Search size={14} style={{ position: 'absolute', left: 10, top: 11, color: '#64748b' }} />
          <input
            type="text"
            placeholder="Search tasks..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="form-input"
            style={{ paddingLeft: 32, fontSize: 12, width: 230 }}
          />
        </div>
      </div>

      {/* Task Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(420px, 1fr))', gap: 20 }}>
        {filteredTasks.map((task) => (
          <div
            key={task.id}
            className="card"
            style={{ display: 'flex', flexDirection: 'column', gap: 14, justifyContent: 'space-between' }}
          >
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 10, marginBottom: 6 }}>
                <div>
                  <span style={{ fontSize: 11, color: 'var(--accent-star)', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                    {task.category}
                  </span>
                  <h3 style={{ fontSize: 16, fontWeight: 700, marginTop: 2 }}>{task.title}</h3>
                </div>
                {getDifficultyBadge(task.difficulty)}
              </div>

              <p style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.6, marginBottom: 12, whiteSpace: 'pre-wrap' }}>
                {task.question}
              </p>

              {/* Expected & Criteria */}
              <div className="bezel-screen" style={{ padding: 12, fontSize: 12 }}>
                <div style={{ color: 'var(--text-muted)', marginBottom: 4 }}>
                  <strong style={{ color: 'var(--text-secondary)' }}>Evaluation Criteria:</strong> {task.evaluation_criteria}
                </div>
                <div style={{ color: 'var(--text-secondary)' }}>
                  <strong style={{ color: 'var(--text-muted)' }}>Expected Reference:</strong> {task.expected_answer.substring(0, 140)}...
                </div>
              </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderTop: '1px solid var(--border-color)', paddingTop: 12 }}>
              <span className="mono" style={{ fontSize: 11, color: 'var(--text-muted)' }}>ID: {task.id}</span>
              <button
                onClick={() => onRunTask(task.id)}
                className="btn btn-primary"
                style={{ fontSize: 12, padding: '7px 16px' }}
              >
                <PlayCircle size={14} />
                <span>Launch Trial</span>
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
