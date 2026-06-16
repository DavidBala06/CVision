import { useState, useEffect } from 'react';
import LoginPage from './components/LoginPage';
import ChatArea from './components/ChatArea';
import Dashboard from './components/Dashboard';
import UploadCV from './components/UploadCV';
import Outreach from './components/Outreach';
import GitHubSearch from './components/GitHubSearch';
import Metrics from './components/Metrics';
import './index.css';

export interface Candidate {
  initials: string;
  name: string;
  role: string;
  matchScore: number;
  matchRank: string;
  skillsScore: number;
  expScore: number;
  industryScore?: number;
  locationScore: number;
  statusScore?: number;
  tags: string[];
  langs: string;
  github_url?: string;
  citation?: string;
  colorTheme: 'purple' | 'green' | 'blue';
  skill_breakdown?: { skill: string; match: string; value: number }[];
  weights?: Record<string, number>;
}

export interface ChatMessage {
  id: string;
  sender: 'user' | 'ai';
  text: string;
  candidates?: Candidate[];
}

export interface PoolCandidate {
  name: string;
  seniority: string;
  years_of_experience: string;
  current_role: string;
  previous_jobs: string;
  degrees: string;
  location: string;
  languages: string;
  technologies: string;
  project_summary: string;
  linkedin_url: string;
  github_url: string;
  email: string;
  status: string;
  outreach_status: string;
  outreach_date: string;
  last_updated_at: string;
}

interface AuthUser {
  name: string;
  role: string;
  username: string;
}

type TabId = 'dashboard' | 'shortlist' | 'upload' | 'outreach' | 'github' | 'metrics';

function App() {
  // Auth state
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [authUser, setAuthUser] = useState<AuthUser | null>(null);

  // App state
  const [activeTab, setActiveTab] = useState<TabId>('dashboard');
  const [poolCandidates, setPoolCandidates] = useState<PoolCandidate[]>([]);
  const [preselectedCandidate, setPreselectedCandidate] = useState<string>('');
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'welcome',
      sender: 'ai',
      text: 'Hi! I\'m the TalentAI Agent. Describe a role or candidate profile to scan the talent pool and generate a shortlist.'
    }
  ]);
  const [isLoading, setIsLoading] = useState<boolean>(false);

  // Check localStorage for existing session on mount
  useEffect(() => {
    const stored = localStorage.getItem('talentai_session');
    if (stored) {
      try {
        const session = JSON.parse(stored);
        if (session.user && session.token) {
          setAuthUser(session.user);
          setIsAuthenticated(true);
        }
      } catch {
        localStorage.removeItem('talentai_session');
      }
    }
  }, []);

  // Fetch talent pool when authenticated
  useEffect(() => {
    if (isAuthenticated) {
      fetchCandidates();
    }
  }, [isAuthenticated]);

  const handleLogin = (user: AuthUser, token: string) => {
    localStorage.setItem('talentai_session', JSON.stringify({ user, token }));
    setAuthUser(user);
    setIsAuthenticated(true);
  };

  const handleLogout = () => {
    localStorage.removeItem('talentai_session');
    setAuthUser(null);
    setIsAuthenticated(false);
    setActiveTab('dashboard');
  };

  const fetchCandidates = async () => {
    try {
      const res = await fetch('http://127.0.0.1:8000/api/candidates');
      if (res.ok) {
        const data = await res.json();
        setPoolCandidates(data);
      }
    } catch (err) {
      console.error('Failed to fetch candidates:', err);
    }
  };

  const handleHRQuery = async (queryText: string) => {
    const userMsg: ChatMessage = {
      id: Date.now().toString(),
      sender: 'user',
      text: queryText
    };
    setMessages((prev) => [...prev, userMsg]);
    setIsLoading(true);

    try {
      const response = await fetch('http://127.0.0.1:8000/api/match', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: queryText }),
      });

      if (!response.ok) throw new Error(`Server error: ${response.status}`);
      const data = await response.json();

      let candidatesArray: Candidate[] = [];
      if (Array.isArray(data)) {
        candidatesArray = data;
      } else if (data && typeof data === 'object') {
        candidatesArray = [data as Candidate];
      }

      const aiMsg: ChatMessage = {
        id: (Date.now() + 1).toString(),
        sender: 'ai',
        text: candidatesArray.length > 0
          ? `Found ${candidatesArray.length} matching candidates from the talent pool:`
          : `No matching candidates found in the talent pool. Try adjusting the technologies, location, or seniority requirements.`,
        candidates: candidatesArray
      };
      setMessages((prev) => [...prev, aiMsg]);
    } catch (error) {
      console.error("Backend error:", error);
      setMessages((prev) => [...prev, {
        id: (Date.now() + 1).toString(),
        sender: 'ai',
        text: 'Error: Could not reach the TalentAI engine. Make sure the backend is running on port 8000.'
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleDraftEmail = (candidateName: string) => {
    setPreselectedCandidate(candidateName);
    setActiveTab('outreach');
  };

  const handleNavigateTab = (tab: string) => {
    if (['dashboard', 'shortlist', 'upload', 'outreach', 'github', 'metrics'].includes(tab)) {
      setActiveTab(tab as TabId);
    }
  };

  const renderActiveTab = () => {
    switch (activeTab) {
      case 'dashboard':
        return <Dashboard candidates={poolCandidates} onRefresh={fetchCandidates} onNavigate={handleNavigateTab} />;
      case 'shortlist':
        return <ChatArea messages={messages} onSendMessage={handleHRQuery} isLoading={isLoading} onDraftEmail={handleDraftEmail} />;
      case 'upload':
        return <UploadCV onCandidateAdded={fetchCandidates} />;
      case 'outreach':
        return <Outreach candidates={poolCandidates} preselectedCandidate={preselectedCandidate} />;
      case 'github':
        return <GitHubSearch />;
      case 'metrics':
        return <Metrics />;
      default:
        return <Dashboard candidates={poolCandidates} onRefresh={fetchCandidates} onNavigate={handleNavigateTab} />;
    }
  };

  const tabs: { id: TabId; label: string; icon: string }[] = [
    { id: 'dashboard', label: 'Dashboard', icon: '' },
    { id: 'shortlist', label: 'Shortlist', icon: '' },
    { id: 'upload', label: 'Add Candidate', icon: '' },
    { id: 'outreach', label: 'Outreach', icon: '' },
    { id: 'github', label: 'Source', icon: '' },
    { id: 'metrics', label: 'Metrics', icon: '' },
  ];

  // --- RENDER ---

  if (!isAuthenticated) {
    return <LoginPage onLogin={handleLogin} />;
  }

  return (
    <div className="app-container">
      <main className="main-content">
        <div className="tab-header">
          <div className="navbar-brand">
            <span className="brand-icon"></span>
            <div className="brand-text">
              <span className="brand-name">TalentAI</span>
              <span className="brand-sub">by CVision</span>
            </div>
          </div>
          <div className="navbar-tabs">
            {tabs.map(tab => (
              <button
                key={tab.id}
                id={`nav-tab-${tab.id}`}
                className={`tab-btn ${activeTab === tab.id ? 'active' : ''}`}
                onClick={() => setActiveTab(tab.id)}
              >
                <span className="tab-icon">{tab.icon}</span> {tab.label}
              </button>
            ))}
          </div>
          <div className="navbar-meta">
            <div className="pool-count-badge">
              <span className="pool-count-num">{poolCandidates.length}</span>
              <span className="pool-count-label">in pool</span>
            </div>
            {authUser && (
              <button
                id="btn-sign-out"
                className="sign-out-btn"
                onClick={handleLogout}
                title={`Signed in as ${authUser.name}`}
              >
                {authUser.name.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase()}
              </button>
            )}
          </div>
        </div>
        <div className="tab-content">
          {renderActiveTab()}
        </div>
      </main>
    </div>
  );
}

export default App;