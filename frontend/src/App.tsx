import { useState, useEffect } from 'react';
import Sidebar from './components/Sidebar';
import ChatArea from './components/ChatArea';
import Dashboard from './components/Dashboard';
import UploadCV from './components/UploadCV';
import Outreach from './components/Outreach';
import LinkedInSearch from './components/LinkedInSearch';
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
  locationScore: number;
  tags: string[];
  langs: string;
  linkedin_url?: string;
  citation?: string;
  colorTheme: 'purple' | 'green' | 'blue';
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

type TabId = 'dashboard' | 'shortlist' | 'upload' | 'outreach' | 'linkedin' | 'metrics';

function App() {
  const [activeTab, setActiveTab] = useState<TabId>('dashboard');
  const [poolCandidates, setPoolCandidates] = useState<PoolCandidate[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'welcome',
      sender: 'ai',
      text: 'Hi! I\'m the TalentAI Agent. Describe a role or candidate profile to scan the talent pool and generate a shortlist.'
    }
  ]);
  const [isLoading, setIsLoading] = useState<boolean>(false);

  // Fetch talent pool on mount
  useEffect(() => {
    fetchCandidates();
  }, []);

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

  const renderActiveTab = () => {
    switch (activeTab) {
      case 'dashboard':
        return <Dashboard candidates={poolCandidates} onRefresh={fetchCandidates} />;
      case 'shortlist':
        return <ChatArea messages={messages} onSendMessage={handleHRQuery} isLoading={isLoading} />;
      case 'upload':
        return <UploadCV onCandidateAdded={fetchCandidates} />;
      case 'outreach':
        return <Outreach candidates={poolCandidates} />;
      case 'linkedin':
        return <LinkedInSearch />;
      case 'metrics':
        return <Metrics />;
      default:
        return <Dashboard candidates={poolCandidates} onRefresh={fetchCandidates} />;
    }
  };

  const tabs: { id: TabId; label: string; icon: string }[] = [
    { id: 'dashboard', label: 'Dashboard', icon: '📊' },
    { id: 'shortlist', label: 'Shortlist', icon: '🎯' },
    { id: 'upload', label: 'Upload CV', icon: '📄' },
    { id: 'outreach', label: 'Outreach', icon: '✉️' },
    { id: 'linkedin', label: 'LinkedIn Search', icon: '🔍' },
    { id: 'metrics', label: 'Metrics', icon: '📈' },
  ];

  return (
    <div className="app-container">
      <Sidebar
        activeTab={activeTab}
        onTabChange={setActiveTab}
        candidateCount={poolCandidates.length}
      />
      <main className="main-content">
        <div className="tab-header">
          {tabs.map(tab => (
            <button
              key={tab.id}
              className={`tab-btn ${activeTab === tab.id ? 'active' : ''}`}
              onClick={() => setActiveTab(tab.id)}
            >
              {tab.icon} {tab.label}
            </button>
          ))}
        </div>
        <div className="tab-content">
          {renderActiveTab()}
        </div>
      </main>
    </div>
  );
}

export default App;