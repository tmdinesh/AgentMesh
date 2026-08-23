import React, { useState } from 'react';
import { ArrowRight, Filter, MessageSquare, Search, Cpu } from 'lucide-react';

export default function MessageFeed({ messages = [] }) {
  const [filterRole, setFilterRole] = useState('ALL');
  const [searchTerm, setSearchTerm] = useState('');

  const roles = Array.from(new Set(messages.map((m) => m.sender_role))).filter(Boolean);

  const filteredMessages = messages.filter((m) => {
    if (filterRole !== 'ALL' && m.sender_role !== filterRole && m.receiver_role !== filterRole) {
      return false;
    }
    if (searchTerm && !m.content.toLowerCase().includes(searchTerm.toLowerCase())) {
      return false;
    }
    return true;
  });

  const getRoleColor = (role) => {
    switch (role) {
      case 'Coordinator': return '#38bdf8';
      case 'Solver': return '#818cf8';
      case 'Critic': return '#f43f5e';
      case 'Fact Checker': return '#fbbf24';
      case 'Alternative Solver': return '#34d399';
      case 'Final Reviewer': return '#c084fc';
      default: return '#94a3b8';
    }
  };

  const getProviderBadgeStyle = (provider) => {
    const p = (provider || '').toLowerCase();
    if (p === 'ollama') {
      return { bg: 'rgba(245, 158, 11, 0.15)', text: '#fbbf24', border: 'rgba(245, 158, 11, 0.35)' };
    }
    if (p === 'aicredits') {
      return { bg: 'rgba(56, 189, 248, 0.15)', text: '#38bdf8', border: 'rgba(56, 189, 248, 0.35)' };
    }
    if (p === 'openai') {
      return { bg: 'rgba(16, 185, 129, 0.15)', text: '#34d399', border: 'rgba(16, 185, 129, 0.35)' };
    }
    if (p === 'groq') {
      return { bg: 'rgba(249, 115, 22, 0.15)', text: '#fb923c', border: 'rgba(249, 115, 22, 0.35)' };
    }
    if (p === 'gemini') {
      return { bg: 'rgba(56, 189, 248, 0.15)', text: '#38bdf8', border: 'rgba(56, 189, 248, 0.35)' };
    }
    if (p === 'mistral') {
      return { bg: 'rgba(168, 85, 247, 0.15)', text: '#c084fc', border: 'rgba(168, 85, 247, 0.35)' };
    }
    if (p === 'openrouter') {
      return { bg: 'rgba(236, 72, 153, 0.15)', text: '#f472b6', border: 'rgba(236, 72, 153, 0.35)' };
    }
    return { bg: 'rgba(148, 163, 184, 0.15)', text: '#94a3b8', border: 'rgba(148, 163, 184, 0.35)' };
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      {/* Controls bar */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: 12,
          padding: '12px 16px',
          background: 'var(--bg-inner)',
          borderRadius: 8,
          border: '1px solid var(--border-color)',
          boxShadow: 'var(--inset-shadow)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <MessageSquare size={16} color="var(--accent-star)" />
          <span style={{ fontSize: 13, fontWeight: 700, letterSpacing: '-0.01em' }}>
            Dialogue Transcript ({filteredMessages.length} / {messages.length} messages)
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          {/* Search box */}
          <div style={{ position: 'relative' }}>
            <Search size={13} style={{ position: 'absolute', left: 10, top: 10, color: 'var(--text-muted)' }} />
            <input
              type="text"
              placeholder="Search transcript..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="form-input"
              style={{ paddingLeft: 30, paddingRight: 10, paddingTop: 6, paddingBottom: 6, fontSize: 12, width: 180 }}
            />
          </div>

          {/* Role Filter */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <Filter size={13} color="var(--text-muted)" />
            <select
              value={filterRole}
              onChange={(e) => setFilterRole(e.target.value)}
              className="form-select"
              style={{ padding: '6px 10px', fontSize: 12 }}
            >
              <option value="ALL">All Roles</option>
              {roles.map((r) => (
                <option key={r} value={r}>
                  {r}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Message List */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12, maxHeight: 580, overflowY: 'auto', paddingRight: 4 }}>
        {filteredMessages.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '36px 0', color: 'var(--text-muted)', fontSize: 13 }}>
            No messages matching the filter criteria.
          </div>
        ) : (
          filteredMessages.map((msg, index) => {
            const senderColor = getRoleColor(msg.sender_role);
            const receiverColor = getRoleColor(msg.receiver_role);
            const badgeStyle = getProviderBadgeStyle(msg.provider);

            return (
              <div
                key={msg.id || index}
                className="card"
                style={{
                  padding: 16,
                  borderLeft: `4px solid ${senderColor}`,
                  background: 'var(--bg-card)',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 10,
                  boxShadow: '0 2px 8px rgba(0,0,0,0.3)',
                }}
              >
                {/* Message Header */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                    <span
                      className="mono"
                      style={{
                        fontSize: 11,
                        background: 'var(--bg-inner)',
                        color: 'var(--text-secondary)',
                        padding: '2px 7px',
                        borderRadius: 4,
                        fontWeight: 700,
                        border: '1px solid var(--border-color)',
                        boxShadow: 'var(--inset-shadow)',
                      }}
                    >
                      Turn {msg.turn}
                    </span>

                    {/* Sender */}
                    <span style={{ fontSize: 13, fontWeight: 700, color: senderColor }}>
                      {msg.sender_role}
                    </span>

                    {/* Model Provider / Model Name Badge */}
                    {msg.model_name && (
                      <span
                        className="mono"
                        style={{
                          fontSize: 10,
                          background: badgeStyle.bg,
                          color: badgeStyle.text,
                          border: `1px solid ${badgeStyle.border}`,
                          padding: '1px 6px',
                          borderRadius: 4,
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: 4,
                          fontWeight: 600,
                        }}
                        title={`Model: ${msg.model_name} (Provider: ${msg.provider || 'cloud'})`}
                      >
                        <Cpu size={11} />
                        {msg.model_name}
                      </span>
                    )}

                    <ArrowRight size={13} color="var(--text-muted)" />

                    {/* Receiver */}
                    <span style={{ fontSize: 13, fontWeight: 600, color: receiverColor }}>
                      {msg.receiver_role}
                    </span>
                  </div>

                  <span className="mono" style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                    {msg.timestamp ? new Date(msg.timestamp).toLocaleTimeString() : ''}
                  </span>
                </div>

                {/* Content in Recessed Teletype Screen */}
                <div
                  className="bezel-screen"
                  style={{
                    fontSize: 13,
                    lineHeight: 1.6,
                    color: 'var(--text-primary)',
                    whiteSpace: 'pre-wrap',
                    padding: 14,
                    fontFamily: msg.content.includes('\n') ? 'var(--font-mono)' : 'var(--font-sans)',
                  }}
                >
                  {msg.content}
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
