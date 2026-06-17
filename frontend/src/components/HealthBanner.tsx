import React, { useEffect, useState, useRef } from 'react';
import './HealthBanner.css';
import type { PoolCandidate } from '../App';

interface HealthBannerProps {
  candidates: PoolCandidate[];
}

function useCountUp(target: number, duration = 900) {
  const [count, setCount] = useState(0);
  const frameRef = useRef<number>();

  useEffect(() => {
    const start = performance.now();
    const tick = (now: number) => {
      const elapsed = now - start;
      const progress = Math.min(elapsed / duration, 1);
      // ease-out cubic
      const eased = 1 - Math.pow(1 - progress, 3);
      setCount(Math.round(eased * target));
      if (progress < 1) frameRef.current = requestAnimationFrame(tick);
    };
    frameRef.current = requestAnimationFrame(tick);
    return () => { if (frameRef.current) cancelAnimationFrame(frameRef.current); };
  }, [target, duration]);

  return count;
}

const HealthBanner: React.FC<HealthBannerProps> = ({ candidates }) => {
  const [staleCount, setStaleCount] = useState(0);
  const [contactedCount, setContactedCount] = useState(0);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    // Count contacted this week
    const oneWeekAgo = new Date();
    oneWeekAgo.setDate(oneWeekAgo.getDate() - 7);

    const contacted = candidates.filter(c => {
      const sent = ['email_sent', 'replied'].includes(c.outreach_status);
      if (!sent) return false;
      if (!c.outreach_date) return true; // count if status is set but no date
      try {
        return new Date(c.outreach_date) >= oneWeekAgo;
      } catch {
        return false;
      }
    }).length;
    setContactedCount(contacted);

    // Fetch stale count
    fetch('http://127.0.0.1:8000/api/refresh/stale')
      .then(r => r.json())
      .then(data => {
        setStaleCount(data.count ?? 0);
        setLoaded(true);
      })
      .catch(() => setLoaded(true));
  }, [candidates]);

  const totalCount = useCountUp(candidates.length);
  const staleAnimated = useCountUp(staleCount);
  const contactedAnimated = useCountUp(contactedCount);

  const healthScore = candidates.length === 0
    ? 0
    : Math.round(((candidates.length - staleCount) / candidates.length) * 100);

  const healthColor =
    healthScore >= 80 ? '#4ade80' :
    healthScore >= 50 ? '#fbbf24' : '#f87171';

  const stats = [
    {
      id: 'stat-total',
      value: totalCount,
      label: 'Total Candidates',
      sub: 'in talent pool',
      color: '#6366f1',
      icon: 'Total',
    },
    {
      id: 'stat-stale',
      value: staleAnimated,
      label: 'Need Refresh',
      sub: staleCount === 0 ? 'All up to date' : 'profiles >3 months old',
      color: staleCount === 0 ? '#4ade80' : '#f87171',
      icon: 'Stale',
    },
    {
      id: 'stat-contacted',
      value: contactedAnimated,
      label: 'Contacted',
      sub: 'outreach this week',
      color: '#06b6d4',
      icon: 'Outreach',
    },
    {
      id: 'stat-health',
      value: `${healthScore}%`,
      label: 'Pool Health',
      sub: 'fresh profiles ratio',
      color: healthColor,
      icon: 'Health',
      isText: true,
    },
  ];

  return (
    <div className={`health-banner ${loaded ? 'banner-loaded' : ''}`}>
      {stats.map(stat => (
        <div key={stat.id} id={stat.id} className="health-stat">
          <div className="health-stat-icon">{stat.icon}</div>
          <div className="health-stat-value" style={{ color: stat.color }}>
            {stat.isText ? stat.value : stat.value}
          </div>
          <div className="health-stat-label">{stat.label}</div>
          <div className="health-stat-sub">{stat.sub}</div>
        </div>
      ))}
    </div>
  );
};

export default HealthBanner;
