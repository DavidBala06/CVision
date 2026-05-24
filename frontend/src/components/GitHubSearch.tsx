import React, { useState } from 'react';
import './GitHubSearch.css';

interface GitHubRepo {
  name: string;
  description: string;
  stars: number;
  language: string;
  url: string;
  forks: number;
}

interface GitHubProfile {
  username: string;
  name: string;
  avatar_url: string;
  profile_url: string;
  bio: string;
  location: string;
  company: string;
  public_repos: number;
  followers: number;
  languages: string[];
  top_repos: GitHubRepo[];
  hireable: boolean;
}

const GitHubSearch: React.FC = () => {
  const [searchType, setSearchType] = useState<'criteria' | 'profile'>('criteria');
  const [queryText, setQueryText] = useState('');
  const [result, setResult] = useState<any>(null);
  const [isSearching, setIsSearching] = useState(false);

  const handleSearch = async () => {
    if (!queryText.trim()) return;
    setIsSearching(true);
    setResult(null);

    try {
      const res = await fetch('http://127.0.0.1:8000/api/github-search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: queryText, search_type: searchType }),
      });
      if (!res.ok) throw new Error(`Error: ${res.status}`);
      const data = await res.json();
      setResult(data);
    } catch (err) {
      setResult({ error: `Search failed: ${err}` });
    } finally {
      setIsSearching(false);
    }
  };

  const renderProfileCard = (profile: GitHubProfile, index: number) => (
    <div key={index} className="github-profile-card">
      <div className="profile-card-header">
        <img src={profile.avatar_url} alt={profile.name} className="github-avatar" />
        <div className="profile-card-info">
          <h3 className="profile-name">{profile.name}</h3>
          <span className="profile-username">@{profile.username}</span>
          {profile.location && (
            <span className="profile-location">📍 {profile.location}</span>
          )}
        </div>
        <div className="profile-card-stats">
          <div className="stat-chip">
            <span className="stat-num">{profile.public_repos}</span>
            <span className="stat-txt">repos</span>
          </div>
          <div className="stat-chip">
            <span className="stat-num">{profile.followers}</span>
            <span className="stat-txt">followers</span>
          </div>
        </div>
      </div>

      {profile.bio && <p className="profile-bio">{profile.bio}</p>}

      {profile.languages.length > 0 && (
        <div className="profile-languages">
          {profile.languages.map((lang, i) => (
            <span key={i} className="lang-badge">{lang}</span>
          ))}
        </div>
      )}

      {profile.top_repos.length > 0 && (
        <div className="profile-repos">
          <div className="repos-label">Top Repositories</div>
          <div className="repos-list">
            {profile.top_repos.slice(0, 3).map((repo, i) => (
              <a key={i} href={repo.url} target="_blank" rel="noopener noreferrer" className="repo-item">
                <div className="repo-name">{repo.name}</div>
                <div className="repo-meta">
                  {repo.language && <span className="repo-lang">{repo.language}</span>}
                  <span className="repo-stars">⭐ {repo.stars}</span>
                  {repo.forks > 0 && <span className="repo-forks">🔀 {repo.forks}</span>}
                </div>
                {repo.description && <div className="repo-desc">{repo.description}</div>}
              </a>
            ))}
          </div>
        </div>
      )}

      <div className="profile-card-footer">
        <a href={profile.profile_url} target="_blank" rel="noopener noreferrer" className="btn btn-sm btn-secondary">
          View on GitHub
        </a>
        {profile.hireable && <span className="hireable-badge">Hireable</span>}
      </div>
    </div>
  );

  const profiles = result?.profiles || result?.similar_profiles || [];

  return (
    <div className="github-search">
      <div className="section-header">
        <div>
          <div className="section-title">GitHub Developer Search</div>
          <div className="section-subtitle">Find developer candidates from GitHub profiles & repositories</div>
        </div>
      </div>

      <div className="github-content">
        <div className="search-form">
          <div className="search-type-toggle">
            <button
              className={`toggle-btn ${searchType === 'criteria' ? 'active' : ''}`}
              onClick={() => setSearchType('criteria')}
            >
              Search by Role
            </button>
            <button
              className={`toggle-btn ${searchType === 'profile' ? 'active' : ''}`}
              onClick={() => setSearchType('profile')}
            >
              👤 Find Similar Devs
            </button>
          </div>

          <div className="form-group">
            <label className="form-label">
              {searchType === 'criteria' ? 'Job Description / Role Requirements' : 'GitHub Username or Profile URL'}
            </label>
            <textarea
              className="form-textarea"
              placeholder={searchType === 'criteria'
                ? 'Describe the role (e.g., "Senior Python Developer with ML experience in Romania...")'
                : 'Enter a GitHub username or profile URL (e.g., "torvalds" or "https://github.com/torvalds")'}
              value={queryText}
              onChange={e => setQueryText(e.target.value)}
              rows={searchType === 'criteria' ? 5 : 2}
            />
          </div>

          <button className="btn btn-primary" onClick={handleSearch} disabled={isSearching || !queryText.trim()}>
            {isSearching ? <><span className="spinner"></span> Searching GitHub...</> : 'Search GitHub'}
          </button>
        </div>

        {/* Strategy info */}
        {result && !result.error && result.search_strategy && (
          <div className="strategy-section">
            {result.search_strategy.sourcing_tips && (
              <div className="result-card">
                <div className="result-card-title">💡 Sourcing Tips</div>
                <ul className="tips-list">
                  {result.search_strategy.sourcing_tips.map((tip: string, i: number) => (
                    <li key={i}>{tip}</li>
                  ))}
                </ul>
              </div>
            )}
            {result.search_strategy.search_query && (
              <div className="result-card">
                <div className="result-card-header">
                  <span className="result-card-title">🔎 Search Query Used</span>
                </div>
                <div className="result-value code">{result.search_strategy.search_query}</div>
              </div>
            )}
          </div>
        )}

        {/* Source profile (for profile search) */}
        {result?.source_profile && (
          <div className="source-profile-section">
            <div className="source-label">Source Profile</div>
            {renderProfileCard({
              ...result.source_profile,
              profile_url: `https://github.com/${result.source_profile.username}`,
              public_repos: 0,
              followers: 0,
              company: '',
              hireable: false,
            } as GitHubProfile, -1)}
          </div>
        )}

        {/* Profile results */}
        {profiles.length > 0 && (
          <div className="profiles-section">
            <div className="profiles-header">
              <span className="profiles-label">
                {result?.similar_profiles ? '👥 Similar Developers' : '👥 Matching Developers'}
              </span>
              <span className="profiles-count">{profiles.length} found</span>
            </div>
            <div className="profiles-grid">
              {profiles.map((p: GitHubProfile, i: number) => renderProfileCard(p, i))}
            </div>
          </div>
        )}

        {result && !result.error && profiles.length === 0 && !isSearching && (
          <div className="empty-state">
            <div className="empty-state-icon"></div>
            <div className="empty-state-text">No matching profiles found. Try broadening your search criteria.</div>
          </div>
        )}

        {result?.error && <div className="info-msg">{result.error}</div>}
      </div>
    </div>
  );
};

export default GitHubSearch;
