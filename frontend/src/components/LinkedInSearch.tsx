import React, { useState } from 'react';
import './LinkedInSearch.css';

const LinkedInSearch: React.FC = () => {
  const [searchType, setSearchType] = useState<'role' | 'profile'>('role');
  const [queryText, setQueryText] = useState('');
  const [result, setResult] = useState<any>(null);
  const [isSearching, setIsSearching] = useState(false);

  const handleSearch = async () => {
    if (!queryText.trim()) return;
    setIsSearching(true);
    setResult(null);

    try {
      const res = await fetch('http://127.0.0.1:8000/api/linkedin-search', {
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

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  return (
    <div className="linkedin-search">
      <div className="section-header">
        <div>
          <div className="section-title">🔍 LinkedIn Candidate Sourcing</div>
          <div className="section-subtitle">Nice-to-have: AI-generated search strategies (GDPR compliant)</div>
        </div>
      </div>

      <div className="linkedin-content">
        <div className="search-form">
          <div className="search-type-toggle">
            <button
              className={`toggle-btn ${searchType === 'role' ? 'active' : ''}`}
              onClick={() => setSearchType('role')}
            >
              🎯 Search by Role
            </button>
            <button
              className={`toggle-btn ${searchType === 'profile' ? 'active' : ''}`}
              onClick={() => setSearchType('profile')}
            >
              👤 Find Similar Profiles
            </button>
          </div>

          <div className="form-group">
            <label className="form-label">
              {searchType === 'role' ? 'Job Description / Role Requirements' : 'LinkedIn Profile Text or URL'}
            </label>
            <textarea
              className="form-textarea"
              placeholder={searchType === 'role'
                ? 'Describe the role you\'re hiring for (e.g., "Senior Python Developer with ML experience in Cluj...")' 
                : 'Paste a LinkedIn profile text or URL to find similar candidates...'}
              value={queryText}
              onChange={e => setQueryText(e.target.value)}
              rows={5}
            />
          </div>

          <button className="btn btn-primary" onClick={handleSearch} disabled={isSearching || !queryText.trim()}>
            {isSearching ? <><span className="spinner"></span> Generating strategy...</> : '🤖 Generate LinkedIn Search Strategy'}
          </button>
        </div>

        {result && !result.error && (
          <div className="search-results">
            {result.search_keywords && (
              <div className="result-card">
                <div className="result-card-header">
                  <span className="result-card-title">🔎 Search Keywords</span>
                  <button className="btn btn-sm btn-secondary" onClick={() => copyToClipboard(result.search_keywords)}>📋 Copy</button>
                </div>
                <div className="result-value">{result.search_keywords}</div>
              </div>
            )}

            {result.boolean_query && (
              <div className="result-card">
                <div className="result-card-header">
                  <span className="result-card-title">🧮 Boolean Query</span>
                  <button className="btn btn-sm btn-secondary" onClick={() => copyToClipboard(result.boolean_query)}>📋 Copy</button>
                </div>
                <div className="result-value code">{result.boolean_query}</div>
              </div>
            )}

            {result.linkedin_search_url && (
              <div className="result-card">
                <div className="result-card-header">
                  <span className="result-card-title">🔗 LinkedIn Search URL</span>
                </div>
                <a href={result.linkedin_search_url} target="_blank" rel="noopener noreferrer" className="search-url-link">
                  Open in LinkedIn →
                </a>
              </div>
            )}

            {result.skills_filter && (
              <div className="result-card">
                <div className="result-card-title">🏷️ Skills to Filter</div>
                <div className="skills-list">
                  {result.skills_filter.map((s: string, i: number) => (
                    <span key={i} className="tech-tag">{s}</span>
                  ))}
                </div>
              </div>
            )}

            {result.alternative_titles && (
              <div className="result-card">
                <div className="result-card-title">💼 Alternative Job Titles</div>
                <div className="skills-list">
                  {result.alternative_titles.map((t: string, i: number) => (
                    <span key={i} className="alt-title">{t}</span>
                  ))}
                </div>
              </div>
            )}

            {result.companies_to_target && (
              <div className="result-card">
                <div className="result-card-title">🏢 Companies to Target</div>
                <div className="skills-list">
                  {result.companies_to_target.map((c: string, i: number) => (
                    <span key={i} className="company-tag">{c}</span>
                  ))}
                </div>
              </div>
            )}

            {result.sourcing_tips && (
              <div className="result-card">
                <div className="result-card-title">💡 Sourcing Tips</div>
                <ul className="tips-list">
                  {result.sourcing_tips.map((tip: string, i: number) => (
                    <li key={i}>{tip}</li>
                  ))}
                </ul>
              </div>
            )}

            {result.profile_summary && (
              <div className="result-card">
                <div className="result-card-title">📝 Profile Analysis</div>
                <div className="result-value">{result.profile_summary}</div>
              </div>
            )}
          </div>
        )}

        {result?.error && <div className="info-msg">{result.error}</div>}
      </div>
    </div>
  );
};

export default LinkedInSearch;
