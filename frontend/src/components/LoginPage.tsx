import React, { useState } from 'react';
import Aurora from './Aurora';
import './LoginPage.css';

interface LoginPageProps {
  onLogin: (user: { name: string; role: string; username: string }, token: string) => void;
}

const LoginPage: React.FC<LoginPageProps> = ({ onLogin }) => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim() || !password.trim()) return;

    setError('');
    setIsLoading(true);

    try {
      const res = await fetch('http://127.0.0.1:8000/api/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: username.trim(), password }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        setError(data.detail || 'Invalid credentials. Please try again.');
        return;
      }

      const data = await res.json();
      onLogin(data.user, data.token);
    } catch (err) {
      setError('Cannot connect to server. Make sure the backend is running.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="login-page">
      {/* Aurora animated background */}
      <div className="login-aurora-bg">
        <Aurora
          colorStops={["#6366f1", "#8b5cf6", "#4f46e5"]}
          blend={0.6}
          amplitude={1.2}
          speed={0.8}
        />
      </div>

      {/* Corner branding */}
      <div className="login-corner-brand">
        <div>
          <div className="login-corner-name">TalentAI</div>
          <div className="login-corner-sub">by CVision</div>
        </div>
      </div>

      {/* Login card */}
      <div className="login-card">
        <div className="login-hero">
          <div className="login-hero-title">Your talent pipeline, on autopilot.</div>
          <div className="login-hero-subtitle">
            From CV to shortlist in seconds. No black boxes. No missed candidates.
          </div>
        </div>

        <form className="login-form" onSubmit={handleSubmit}>
          <div className="login-field">
            <label htmlFor="login-username">Username</label>
            <input
              id="login-username"
              type="text"
              placeholder="Enter your username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
              autoFocus
            />
          </div>

          <div className="login-field">
            <label htmlFor="login-password">Password</label>
            <input
              id="login-password"
              type="password"
              placeholder="Enter your password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
            />
          </div>

          {error && <div className="login-error">{error}</div>}

          <button
            id="login-submit-btn"
            type="submit"
            className="login-submit"
            disabled={isLoading || !username.trim() || !password.trim()}
          >
            {isLoading ? (
              <><span className="spinner"></span> Signing in...</>
            ) : (
              'Sign In'
            )}
          </button>
        </form>

        <div className="login-demo-hint">
          <span>Demo credentials</span>
          <div className="login-demo-creds">demo / talent2024</div>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;
