import React, { useState } from 'react';
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
      <div className="login-card">
        <div className="login-brand">
          <div className="login-brand-icon">⚡</div>
          <div className="login-brand-name">TalentAI</div>
          <div className="login-brand-sub">Intelligent Recruitment Platform</div>
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
