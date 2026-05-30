import { useState, useEffect, useRef, useCallback } from 'react';
import { api } from './lib.js';

// ─────────────────────────────────────────────────────────────────────────────
// Tiny atoms
// ─────────────────────────────────────────────────────────────────────────────

function Spinner({ size = 12, color = 'var(--accent)', speed = '.7s' }) {
  return (
    <span style={{
      display: 'inline-block', width: size, height: size, borderRadius: '50%',
      border: `2px solid ${color}30`, borderTopColor: color, flexShrink: 0,
      animation: `spin ${speed} linear infinite`,
    }} />
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Digger Worker Card — the main visual showpiece
// Each card represents one active crawl agent
// ─────────────────────────────────────────────────────────────────────────────

const ENTITY_ICONS = {
  PERSON:       '👤',
  PARTY:        '🏛',
  UNIVERSITY:   '🎓',
  COMPANY:      '🏢',
  ORGANIZATION: '🏛',
  OTHER:        '📄',
  '?':          '🔍',
};

const DEPTH_COLORS = ['var(--gold)', 'var(--accent)', 'var(--purple)', 'var(--teal)'];

const WORKER_TYPE_LABELS = {
  graph:  'GRAPH MINER',
  news:   'NEWS AGENT',
  seed:   'SEED AGENT',
};

function DiggerCard({ worker, idx, type = 'graph' }) {
  const color   = DEPTH_COLORS[Math.min(worker.depth || 0, 3)];
  const icon    = ENTITY_ICONS[worker.entity_type] || '🔍';
  const status  = worker.status || 'crawling';
  const elapsed = worker.started
    ? Math.round((Date.now() / 1000) - worker.started)
    : null;

  // Staggered animation delay
  const delay = `${idx * 0.08}s`;

  return (
    <div style={{
      position: 'relative', overflow: 'hidden',
      borderRadius: 10, padding: '10px 12px',
      background: `${color}0a`,
      border: `0.5px solid ${color}3a`,
      animation: `fadeIn 0.3s ease ${delay} both`,
      transition: 'border-color .3s',
    }}>
      {/* Animated scan line */}
      <div style={{
        position: 'absolute', top: 0, left: '-100%', right: 0, height: '100%',
        background: `linear-gradient(90deg, transparent 0%, ${color}12 50%, transparent 100%)`,
        animation: `slide ${1.8 + idx * 0.3}s ease-in-out infinite`,
        pointerEvents: 'none',
      }} />

      <div style={{ display: 'flex', gap: 8, alignItems: 'flex-start', position: 'relative' }}>

        {/* Agent avatar with pulse ring */}
        <div style={{ position: 'relative', flexShrink: 0 }}>
          <div style={{
            width: 34, height: 34, borderRadius: 8,
            background: `${color}1a`, border: `1.5px solid ${color}55`,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 16,
          }}>{icon}</div>
          {/* Pulse ring when crawling */}
          {status === 'crawling' && (
            <div style={{
              position: 'absolute', inset: -3, borderRadius: 11,
              border: `1.5px solid ${color}`,
              animation: 'pulse-ring 1.5s ease-out infinite',
              opacity: 0,
            }} />
          )}
          {/* Depth badge */}
          <div style={{
            position: 'absolute', bottom: -3, right: -3,
            width: 14, height: 14, borderRadius: 4,
            background: color, border: '1.5px solid var(--panel)',
            fontSize: 8, fontWeight: 800, color: '#000',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontFamily: 'var(--mono)',
          }}>d{worker.depth ?? 0}</div>
        </div>

        {/* Content */}
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 3 }}>
            <span style={{
              fontSize: 7, fontFamily: 'var(--mono)', letterSpacing: 1,
              color: color, textTransform: 'uppercase', fontWeight: 700,
            }}>{WORKER_TYPE_LABELS[type] || 'AGENT'} #{idx + 1}</span>
            <span style={{
              fontSize: 7, padding: '1px 5px', borderRadius: 4,
              background: status === 'crawling' ? `${color}22` : 'rgba(104,211,145,0.15)',
              color: status === 'crawling' ? color : 'var(--green)',
              fontFamily: 'var(--mono)',
            }}>{status}</span>
            {elapsed !== null && (
              <span style={{ fontSize: 7, color: 'var(--text3)', fontFamily: 'var(--mono)', marginLeft: 'auto' }}>
                {elapsed}s
              </span>
            )}
          </div>

          {/* Current target */}
          <div style={{
            fontSize: 11, fontWeight: 600, color: 'var(--text)',
            overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
            marginBottom: 2,
          }}>
            {worker.name || '…'}
          </div>

          {/* Parent + stats row */}
          <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
            {worker.parent && worker.parent !== 'seed' && (
              <span style={{ fontSize: 8, color: 'var(--text3)', fontFamily: 'var(--mono)' }}>
                ← {worker.parent.split('/').pop()?.replace(/_/g,' ')?.slice(0,20)}
              </span>
            )}
            {worker.rels_found !== undefined && worker.rels_found > 0 && (
              <span style={{ fontSize: 8, color: 'var(--green)', fontFamily: 'var(--mono)' }}>
                +{worker.rels_found} relations
              </span>
            )}
          </div>

          {/* Mini progress wave */}
          {status === 'crawling' && (
            <div style={{
              marginTop: 6, height: 2, borderRadius: 1, overflow: 'hidden',
              background: `${color}22`,
            }}>
              <div style={{
                height: '100%', width: '60%', borderRadius: 1,
                background: color,
                animation: `slide ${1.2 + idx * 0.15}s ease-in-out infinite`,
              }} />
            </div>
          )}
        </div>

        {/* Wiki link */}
        {worker.url && worker.url.startsWith('http') && (
          <a href={worker.url} target="_blank" rel="noopener noreferrer" style={{
            fontSize: 10, color: 'var(--text3)', textDecoration: 'none',
            flexShrink: 0, alignSelf: 'center', opacity: .6,
            transition: 'opacity .1s',
          }}
          onMouseEnter={e => e.currentTarget.style.opacity = '1'}
          onMouseLeave={e => e.currentTarget.style.opacity = '.6'}
          title={worker.url}>↗</a>
        )}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Worker Pool Section — shows all active agents grouped by type
// ─────────────────────────────────────────────────────────────────────────────

function WorkerPool({ workers, maxWorkers, phase, newsWorkers, maxNewsWorkers }) {
  const graphWorkers = workers || [];
  const totalSlots   = Math.max(maxWorkers || 4, graphWorkers.length);

  // Empty slot placeholder
  const EmptySlot = ({ idx }) => (
    <div style={{
      borderRadius: 10, padding: '10px 12px', opacity: .3,
      border: '0.5px dashed var(--border)',
      display: 'flex', alignItems: 'center', gap: 8,
    }}>
      <div style={{
        width: 34, height: 34, borderRadius: 8,
        border: '1px dashed var(--border)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontSize: 12, color: 'var(--text3)',
      }}>⛏</div>
      <div>
        <div style={{ fontSize: 7, fontFamily: 'var(--mono)', color: 'var(--text3)', letterSpacing: 1 }}>
          GRAPH MINER #{idx + 1}
        </div>
        <div style={{ fontSize: 10, color: 'var(--text3)', fontFamily: 'var(--mono)', marginTop: 3 }}>
          idle
        </div>
      </div>
    </div>
  );

  const newsActive = newsWorkers || [];
  const newsSlots  = Math.max(maxNewsWorkers || 2, newsActive.length);

  const isGraphPhase = ['graph_mine','graph_mining'].includes(phase);
  const isNewsPhase  = ['news','news_crawling'].includes(phase);

  if (!isGraphPhase && !isNewsPhase) return null;

  return (
    <div style={{ marginBottom: 14 }}>
      {/* Graph workers */}
      {isGraphPhase && (
        <div style={{ marginBottom: 10 }}>
          <div style={{
            display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8,
          }}>
            <span style={{ fontSize: 9, fontFamily: 'var(--mono)', color: 'var(--text3)', letterSpacing: 1 }}>
              ⛏ GRAPH MINERS
            </span>
            <div style={{
              padding: '1px 7px', borderRadius: 20, fontSize: 8, fontFamily: 'var(--mono)',
              background: 'rgba(99,179,237,0.15)', color: 'var(--accent)',
              border: '0.5px solid rgba(99,179,237,0.3)',
            }}>
              {graphWorkers.length}/{totalSlots} active
            </div>
            <div style={{ flex: 1, height: 1, background: 'var(--border)' }} />
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 6 }}>
            {Array.from({ length: totalSlots }).map((_, i) => {
              const w = graphWorkers[i];
              return w
                ? <DiggerCard key={w.id || i} worker={w} idx={i} type="graph" />
                : <EmptySlot key={`empty-${i}`} idx={i} />;
            })}
          </div>
        </div>
      )}

      {/* News workers */}
      {isNewsPhase && (
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
            <span style={{ fontSize: 9, fontFamily: 'var(--mono)', color: 'var(--text3)', letterSpacing: 1 }}>
              📰 NEWS AGENTS
            </span>
            <div style={{
              padding: '1px 7px', borderRadius: 20, fontSize: 8, fontFamily: 'var(--mono)',
              background: 'rgba(79,209,197,0.15)', color: 'var(--teal)',
              border: '0.5px solid rgba(79,209,197,0.3)',
            }}>
              {newsActive.length}/{newsSlots} active
            </div>
            <div style={{ flex: 1, height: 1, background: 'var(--border)' }} />
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 6 }}>
            {Array.from({ length: newsSlots }).map((_, i) => {
              const w = newsActive[i];
              return w
                ? <DiggerCard key={w.id || i} worker={w} idx={i} type="news" />
                : (
                  <div key={`news-empty-${i}`} style={{
                    borderRadius: 10, padding: '10px 12px', opacity: .3,
                    border: '0.5px dashed var(--border)',
                    display: 'flex', alignItems: 'center', gap: 8,
                  }}>
                    <div style={{
                      width: 34, height: 34, borderRadius: 8,
                      border: '1px dashed var(--border)',
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      fontSize: 12,
                    }}>📰</div>
                    <div>
                      <div style={{ fontSize: 7, fontFamily: 'var(--mono)', color: 'var(--text3)', letterSpacing: 1 }}>
                        NEWS AGENT #{i + 1}
                      </div>
                      <div style={{ fontSize: 10, color: 'var(--text3)', marginTop: 3, fontFamily: 'var(--mono)' }}>idle</div>
                    </div>
                  </div>
                );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Phase bar
// ─────────────────────────────────────────────────────────────────────────────

function PhaseRow({ num, label, color, active, done, total, extra }) {
  const pct = total > 0 ? Math.min(100, Math.round((done / total) * 100)) : 0;
  return (
    <div style={{
      padding: '9px 11px', borderRadius: 8, marginBottom: 5,
      background: active ? `${color}0d` : 'var(--panel2)',
      border: `0.5px solid ${active ? color + '44' : 'var(--border)'}`,
      transition: 'all .3s',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: (total > 0 || active) ? 6 : 0 }}>
        <div style={{
          width: 20, height: 20, borderRadius: 5, flexShrink: 0,
          background: `${color}22`, border: `1px solid ${color}44`,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 9, fontWeight: 800, color, fontFamily: 'var(--mono)',
        }}>{num}</div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <span style={{ fontSize: 10, color: active ? 'var(--text)' : 'var(--text3)', fontWeight: active ? 600 : 400 }}>
            {label}
          </span>
          {extra && (
            <div style={{ fontSize: 8, color: 'var(--text3)', fontFamily: 'var(--mono)', marginTop: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {extra}
            </div>
          )}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexShrink: 0 }}>
          {total > 0 && (
            <span style={{ fontSize: 10, color, fontFamily: 'var(--mono)', fontWeight: 700 }}>
              {done}/{total} ({pct}%)
            </span>
          )}
          {active && !total && done > 0 && (
            <span style={{ fontSize: 10, color, fontFamily: 'var(--mono)' }}>{done}</span>
          )}
          {active && <Spinner color={color} size={10} />}
        </div>
      </div>
      {total > 0 && (
        <div style={{ height: 4, borderRadius: 2, background: 'var(--border)', overflow: 'hidden' }}>
          <div style={{
            height: '100%', borderRadius: 2, transition: 'width .6s ease',
            background: `linear-gradient(90deg, ${color}88, ${color})`,
            width: `${pct}%`, boxShadow: active ? `0 0 8px ${color}77` : 'none',
          }} />
        </div>
      )}
      {active && total === 0 && (
        <div style={{ height: 3, borderRadius: 2, background: 'var(--border)', overflow: 'hidden', position: 'relative' }}>
          <div style={{
            position: 'absolute', height: '100%', width: '35%',
            background: `linear-gradient(90deg, transparent, ${color}, transparent)`,
            animation: 'slide 1.6s ease-in-out infinite',
          }} />
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Live event feed
// ─────────────────────────────────────────────────────────────────────────────

function LiveFeed({ events }) {
  const ref = useRef(null);
  useEffect(() => {
    if (ref.current) ref.current.scrollTop = 0;
  }, [events]);

  if (!events?.length) return null;
  return (
    <div style={{
      borderRadius: 8, background: 'var(--bg)',
      border: '0.5px solid var(--border)', marginBottom: 12, overflow: 'hidden',
    }}>
      <div style={{
        padding: '5px 10px', borderBottom: '0.5px solid var(--border)',
        fontSize: 8, color: 'var(--text3)', fontFamily: 'var(--mono)',
        letterSpacing: 1, display: 'flex', alignItems: 'center', gap: 5,
      }}>
        <div style={{ width: 5, height: 5, borderRadius: '50%', background: 'var(--green)', animation: 'pulse 1.5s infinite' }} />
        LIVE CRAWL LOG
        <span style={{ marginLeft: 'auto', color: 'var(--text3)' }}>
          {events.length} events
        </span>
      </div>
      <div ref={ref} style={{ maxHeight: 110, overflowY: 'auto' }}>
        {events.map((ev, i) => (
          <div key={ev.ts} style={{
            padding: '3px 10px', fontSize: 9, fontFamily: 'var(--mono)',
            color: i === 0 ? 'var(--text2)' : 'var(--text3)',
            borderBottom: '0.5px solid rgba(255,255,255,0.03)',
            display: 'flex', gap: 8, alignItems: 'center',
            background: i === 0 ? 'rgba(99,179,237,0.04)' : 'transparent',
            animation: i === 0 ? 'fadeIn .3s ease' : 'none',
          }}>
            <span style={{ flexShrink: 0 }}>{ev.icon}</span>
            <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {ev.text}
            </span>
            {ev.meta && <span style={{ color: 'var(--text3)', flexShrink: 0, fontSize: 8 }}>{ev.meta}</span>}
          </div>
        ))}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Main dashboard
// ─────────────────────────────────────────────────────────────────────────────

export default function AgentDashboard({ onClose }) {
  const [state,     setState]     = useState(null);
  const [running,   setRunning]   = useState(false);
  const [connected, setConnected] = useState(false);
  const [liveFeed,  setLiveFeed]  = useState([]);
  const [limits,    setLimits]    = useState({
    limit_dpr: 100, limit_menteri: 50, limit_gubernur: 40,
    limit_regional: 150, limit_dprd: 100,
  });
  const [jobs,         setJobs]         = useState([]);
  const [confirmDialog,setConfirmDialog] = useState(null); // null | 'restart' | 'stop'
  const [isPaused,     setIsPaused]      = useState(false);
  const [starting,     setStarting]      = useState(false); // true between click and SSE confirmation
  const sseRef  = useRef(null);
  const feedRef = useRef([]);

  const pushFeed = useCallback((icon, text, meta) => {
    const ev = { icon, text, meta, ts: Date.now() };
    feedRef.current = [ev, ...feedRef.current.slice(0, 39)];
    setLiveFeed([...feedRef.current]);
  }, []);

  const connectSSE = useCallback(() => {
    if (sseRef.current) sseRef.current.close();
    const es = new EventSource('/api/agent/stream');
    sseRef.current = es;
    es.onopen  = () => setConnected(true);
    es.onerror = () => setConnected(false);
    es.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        setState(data);
        const RUNNING = ['seeding','graph_mining','news_crawling','vectorizing','discovering','graph_mine','news'];
        const isPausedStatus = data.status === 'paused';
        const isNowRunning = (RUNNING.includes(data.status) || RUNNING.includes(data.phase)) && !isPausedStatus;
        setRunning(isNowRunning);
        setIsPaused(isPausedStatus);
        // Clear the "starting" spinner once SSE confirms the run is live
        if (isNowRunning || data.status === 'error' || data.status === 'done') {
          setStarting(false);
        }

        // Build feed from current_crawling
        if (data.current_crawling?.length) {
          const url  = data.current_crawling[0];
          const name = decodeURIComponent(url.split('/').pop()?.replace(/_/g,' ') || url);
          const depth = data.graph_depth || 0;
          pushFeed('🔍', name, `d${depth}`);
        }
      } catch {}
    };
  }, [pushFeed]);

  useEffect(() => {
    connectSSE();
    api.agentStatus().then(r => { if (r.state) setState(r.state); setRunning(r.running); }).catch(() => {});
    api.jobs().then(r => setJobs(r.jobs || [])).catch(() => {});
    return () => sseRef.current?.close();
  }, [connectSSE]);

  const startAgent  = async (restartMode = 'new') => {
    setStarting(true);
    feedRef.current = []; setLiveFeed([]);
    const modeLabels = { new:'Starting mining run…', skip:'Resuming (skip done)…', fresh:'Wiping data and restarting…' };
    pushFeed('▶', modeLabels[restartMode] || 'Starting…', null);
    try {
      await api.agentStart({...limits, restart_mode: restartMode});
      connectSSE();
    } catch (e) {
      setStarting(false);
      alert(e.message);
    }
  };
  const stopAgent   = async () => {
    setConfirmDialog(null);
    await api.agentStop().catch(() => {});
    pushFeed('■', 'Stop signal sent', null);
  };
  const pauseAgent  = async () => {
    await api.agentPause().catch(() => {});
    pushFeed('⏸', 'Pause sent', null);
  };
  const resumeAgent = async () => {
    await api.agentResume().catch(() => {});
    setIsPaused(false);
    pushFeed('▶', 'Resume sent', null);
  };

  const phase  = state?.phase  || 'idle';
  const status = state?.status || 'idle';

  const STATUS_COLORS = {
    idle:'var(--text3)', seeding:'var(--gold)', graph_mining:'var(--accent)',
    graph_mine:'var(--accent)', news_crawling:'var(--teal)', news:'var(--teal)',
    vectorizing:'var(--green)', done:'var(--green)', error:'var(--red)',
    starting:'var(--gold)', discovering:'var(--gold)',
  };
  const sc = STATUS_COLORS[status] || STATUS_COLORS[phase] || 'var(--text3)';

  const elapsed = state?.started_at
    ? (() => {
        const s = Math.round((Date.now() - new Date(state.started_at)) / 1000);
        return s < 60 ? `${s}s` : s < 3600 ? `${Math.floor(s/60)}m ${s%60}s` : `${Math.floor(s/3600)}h ${Math.floor((s%3600)/60)}m`;
      })()
    : null;

  const overallPct = state?.status === 'done' ? 100
    : { seed:5, discovering:8, graph_mine:30, news:65, vectorize:90 }[phase] || 0;

  // Phase list
  const phases = [
    {
      num:'0', label:'Seed & Discovery',
      color:'var(--gold)',
      active: ['seeding','discovering','seed'].includes(phase) || ['seeding','discovering'].includes(status),
      done: state?.discovered || 0, total: 0,
      extra: state?.discovered ? `${state.discovered} officials discovered` : 'Wikipedia list pages',
    },
    {
      num:'1', label:'Wikipedia Graph Mining',
      color:'var(--accent)',
      active: ['graph_mine','graph_mining'].includes(phase) || status === 'graph_mining',
      done: state?.graph_pages_crawled || 0,
      total: state?.graph_max_nodes || 0,
      extra: state?.graph_pages_crawled
        ? `${state.graph_nodes||0} nodes · ${state.graph_edges||0} edges · depth ${state.graph_depth||'?'}`
        : `recursive link-following · max depth ${state?.graph_depth||2}`,
    },
    {
      num:'2', label:'News Crawl + Faction Scoring',
      color:'var(--teal)',
      active: ['news','news_crawling'].includes(phase) || status === 'news_crawling',
      done: state?.news_persons_done || 0,
      total: state?.news_persons_total || 0,
      extra: state?.news_articles ? `${state.news_articles} articles · 8 outlets` : 'Tempo · Kompas · Detik · CNN · Antara…',
    },
    {
      num:'3', label:'Embed into ChromaDB (RAG)',
      color:'var(--green)',
      active: ['vectorize','vectorizing'].includes(phase) || status === 'vectorizing',
      done: 0, total: 0,
      extra: 'paraphrase-multilingual-MiniLM-L12-v2',
    },
  ];

  // Build news workers from current_crawling for news phase
  const activeWorkers = state?.active_workers || [];
  const isNewsPhase   = ['news','news_crawling'].includes(phase) || status === 'news_crawling';
  const newsWorkers   = isNewsPhase
    ? (state?.current_crawling || []).map((url, i) => ({
        id: i, url, name: decodeURIComponent(url.split('/').pop()?.replace(/_/g,' ') || url),
        depth: 0, entity_type: 'PERSON', status: 'crawling',
      }))
    : [];

  // Summary bar: show active/total workers
  const workerCount  = activeWorkers.length;
  const maxWorkers   = state?.max_l1_workers || 4;
  const newsCount    = newsWorkers.length;
  const maxNews      = state?.max_news_workers || 2;

  return (
    <div style={{
      position: 'fixed', inset: 0, background: 'rgba(6,8,16,0.92)',
      backdropFilter: 'blur(12px)', zIndex: 300,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
    }}>
      <div style={{
        width: 720, maxHeight: '93vh', background: 'var(--panel)',
        border: '0.5px solid var(--border2)', borderRadius: 16,
        display: 'flex', flexDirection: 'column', overflow: 'hidden',
        boxShadow: '0 0 100px rgba(99,179,237,0.1)',
      }}>

        {/* ── Header ── */}
        <div style={{
          padding: '12px 18px', borderBottom: '0.5px solid var(--border)',
          background: 'rgba(99,179,237,0.03)', flexShrink: 0,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
            <div style={{ flex: 1 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span style={{ fontSize: 13, fontWeight: 700, fontFamily: 'var(--mono)', color: 'var(--text)', letterSpacing: 2 }}>
                  ⚡ AUTONOMOUS AGENT
                </span>
                <span style={{
                  fontSize: 8, padding: '1px 8px', borderRadius: 20, fontFamily: 'var(--mono)',
                  background: `${sc}18`, color: sc, border: `0.5px solid ${sc}44`, textTransform: 'uppercase',
                }}>{status}</span>
                {running && <Spinner color={sc} size={10} />}
              </div>
              {state?.phase_label && (
                <div style={{ fontSize: 9, color: 'var(--text3)', fontFamily: 'var(--mono)', marginTop: 4 }}>
                  {state.phase_label}
                </div>
              )}
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              {/* Worker count badge */}
              {(workerCount > 0 || newsCount > 0) && (
                <div style={{
                  display: 'flex', alignItems: 'center', gap: 5,
                  padding: '3px 10px', borderRadius: 20,
                  background: 'rgba(99,179,237,0.1)', border: '0.5px solid rgba(99,179,237,0.25)',
                }}>
                  <div style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--accent)', animation: 'pulse 1s infinite' }}/>
                  <span style={{ fontSize: 9, color: 'var(--accent2)', fontFamily: 'var(--mono)' }}>
                    {workerCount || newsCount} workers
                  </span>
                </div>
              )}
              <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                <div style={{ width: 6, height: 6, borderRadius: '50%', background: connected ? 'var(--green)' : 'var(--red)', animation: connected ? 'pulse 2s infinite' : 'none' }}/>
                <span style={{ fontSize: 8, color: connected ? 'var(--green)' : 'var(--red)', fontFamily: 'var(--mono)' }}>
                  {connected ? 'SSE' : 'off'}
                </span>
              </div>
              {elapsed && <span style={{ fontSize: 9, color: 'var(--text3)', fontFamily: 'var(--mono)' }}>{elapsed}</span>}
              <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text3)', fontSize: 18, padding: 0 }}>✕</button>
            </div>
          </div>

          {/* Overall progress bar */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <div style={{ flex: 1, height: 4, borderRadius: 2, background: 'var(--border)', overflow: 'hidden', position: 'relative' }}>
              <div style={{
                height: '100%', borderRadius: 2, background: sc,
                width: `${overallPct}%`, transition: 'width 1.5s ease',
                boxShadow: running ? `0 0 8px ${sc}` : 'none',
              }} />
              {running && overallPct > 0 && (
                <div style={{
                  position: 'absolute', top: 0, right: 0, bottom: 0, width: 30,
                  background: `linear-gradient(90deg, transparent, ${sc}40)`,
                  animation: 'pulse 1s infinite',
                }} />
              )}
            </div>
            <span style={{ fontSize: 9, color: sc, fontFamily: 'var(--mono)', width: 30, textAlign: 'right' }}>
              {overallPct}%
            </span>
          </div>
        </div>

        <div style={{ overflowY: 'auto', flex: 1, padding: '12px 16px' }}>

          {/* ── Stats ── */}
          <div style={{ display: 'flex', gap: 5, marginBottom: 12 }}>
            {[
              { label:'Officials', v: state?.discovered,          color:'var(--gold)'    },
              { label:'Pages',     v: state?.graph_pages_crawled, color:'var(--accent)'  },
              { label:'Nodes',     v: state?.graph_nodes,         color:'var(--purple)'  },
              { label:'Edges',     v: state?.graph_edges,         color:'var(--accent2)' },
              { label:'Articles',  v: state?.news_articles,       color:'var(--teal)'    },
            ].map(s => (
              <div key={s.label} style={{
                flex: 1, padding: '8px 6px', borderRadius: 8, textAlign: 'center',
                background: 'var(--panel2)', border: `0.5px solid ${s.color}25`,
              }}>
                <div style={{ fontSize: 20, fontWeight: 800, color: s.color, fontFamily: 'var(--mono)', lineHeight: 1 }}>
                  {s.v ?? <span style={{ color: 'var(--border2)', fontSize: 14 }}>—</span>}
                </div>
                <div style={{ fontSize: 7, color: 'var(--text3)', fontFamily: 'var(--mono)', marginTop: 3, letterSpacing: .8 }}>
                  {s.label.toUpperCase()}
                </div>
              </div>
            ))}
          </div>

          {/* ── Phase bars ── */}
          <div style={{ marginBottom: 12 }}>
            {phases.map(p => <PhaseRow key={p.num} {...p} />)}
          </div>

          {/* ── WORKER POOL — the star of the show ── */}
          <WorkerPool
            workers={activeWorkers}
            maxWorkers={maxWorkers}
            phase={phase}
            newsWorkers={newsWorkers}
            maxNewsWorkers={maxNews}
          />

          {/* ── Live feed ── */}
          <LiveFeed events={liveFeed} />

          {/* ── Controls ── */}
          <div style={{
            padding: '12px', borderRadius: 10, border: '0.5px solid var(--border)',
            background: 'var(--panel2)', marginBottom: 12,
          }}>
            <div style={{ fontSize: 8, color: 'var(--text3)', fontFamily: 'var(--mono)', marginBottom: 10, letterSpacing: 1 }}>
              DISCOVERY LIMITS
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 6, marginBottom: 8 }}>
              {[['DPR','limit_dpr'],['Menteri','limit_menteri'],['Gubernur','limit_gubernur'],['Bupati/Wali','limit_regional'],['DPRD','limit_dprd']].map(([l,k]) => (
                <div key={k}>
                  <div style={{ fontSize: 7, color: 'var(--text3)', fontFamily: 'var(--mono)', marginBottom: 3 }}>{l}</div>
                  <input type="number" min={1} max={600} value={limits[k]}
                    onChange={e => setLimits(p => ({...p,[k]:+e.target.value}))} disabled={running}
                    style={{
                      width: '100%', padding: '4px 6px', borderRadius: 5, fontSize: 10,
                      fontFamily: 'var(--mono)', background: 'var(--panel)', color: 'var(--text)',
                      border: '0.5px solid var(--border)', outline: 'none', opacity: running ? .5 : 1,
                    }}
                  />
                </div>
              ))}
            </div>
            <div style={{ fontSize: 7, color: 'var(--text3)', fontFamily: 'var(--mono)', marginBottom: 10 }}>
              ~{Object.values(limits).reduce((a,b)=>a+b,0)} officials · {maxWorkers} graph workers · {maxNews > 0 ? maxNews : 2} news workers
            </div>
            <div style={{ display: 'flex', gap: 6, flexWrap:'wrap' }}>
              {!running && !isPaused ? (
                // Not running — show Start + Restart options
                <>
                  <button
                    onClick={() => !starting && startAgent('new')}
                    disabled={starting}
                    style={{
                      flex: 1, padding: '8px', borderRadius: 8, fontSize: 12,
                      fontFamily: 'var(--mono)', fontWeight: 700,
                      cursor: starting ? 'not-allowed' : 'pointer',
                      background: starting ? 'rgba(99,179,237,0.07)' : 'rgba(99,179,237,0.15)',
                      color: starting ? 'rgba(99,179,237,0.45)' : 'var(--accent2)',
                      border: `0.5px solid ${starting ? 'rgba(99,179,237,0.15)' : 'rgba(99,179,237,0.35)'}`,
                      display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
                      transition: 'all .2s',
                    }}
                  >
                    {starting
                      ? <><Spinner size={11} color="rgba(99,179,237,0.5)" speed=".9s" /> Mining in progress… please wait</>
                      : <>▶ Start Mining Run</>
                    }
                  </button>
                  {/* Restart button — only show if there's previous data, hide while starting */}
                  {!starting && (
                    <button onClick={() => setConfirmDialog('restart')} style={{
                      padding: '8px 12px', borderRadius: 8, fontSize: 11,
                      fontFamily: 'var(--mono)', cursor: 'pointer',
                      background: 'rgba(246,173,85,0.12)', color: 'var(--gold)',
                      border: '0.5px solid rgba(246,173,85,0.3)',
                    }}>↺ Restart</button>
                  )}
                </>
              ) : isPaused ? (
                // Paused state
                <>
                  <button onClick={resumeAgent} style={{
                    flex:1, padding:'8px', borderRadius:8, fontSize:12, fontFamily:'var(--mono)', fontWeight:700,
                    background:'rgba(104,211,145,.18)', color:'var(--green)',
                    border:'0.5px solid rgba(104,211,145,.4)', cursor:'pointer',
                  }}>▶ Resume</button>
                  <button onClick={() => setConfirmDialog('stop')} style={{
                    padding:'8px 12px', borderRadius:8, fontSize:11, fontFamily:'var(--mono)',
                    background:'rgba(252,129,129,.12)', color:'var(--red)',
                    border:'0.5px solid rgba(252,129,129,.3)', cursor:'pointer',
                  }}>■ Stop</button>
                  <button onClick={() => setConfirmDialog('restart')} style={{
                    padding:'8px 12px', borderRadius:8, fontSize:11, fontFamily:'var(--mono)',
                    background:'rgba(246,173,85,.12)', color:'var(--gold)',
                    border:'0.5px solid rgba(246,173,85,.3)', cursor:'pointer',
                  }}>↺ Restart</button>
                </>
              ) : (
                // Running state
                <>
                  <button onClick={pauseAgent} style={{
                    flex:1, padding:'8px', borderRadius:8, fontSize:11, fontFamily:'var(--mono)',
                    background:'rgba(246,173,85,.12)', color:'var(--gold)',
                    border:'0.5px solid rgba(246,173,85,.3)', cursor:'pointer',
                  }}>⏸ Pause</button>
                  <button onClick={() => setConfirmDialog('stop')} style={{
                    padding:'8px 12px', borderRadius:8, fontSize:11, fontFamily:'var(--mono)',
                    background:'rgba(252,129,129,.12)', color:'var(--red)',
                    border:'0.5px solid rgba(252,129,129,.3)', cursor:'pointer',
                  }}>■ Stop</button>
                  <button onClick={() => setConfirmDialog('restart')} style={{
                    padding:'8px 12px', borderRadius:8, fontSize:11, fontFamily:'var(--mono)',
                    background:'rgba(246,173,85,.12)', color:'var(--gold)',
                    border:'0.5px solid rgba(246,173,85,.3)', cursor:'pointer',
                  }}>↺ Restart</button>
                </>
              )}
            </div>
          </div>

          {/* Errors */}
          {state?.errors?.length > 0 && (
            <div style={{ padding:'8px 10px', borderRadius:8, marginBottom:10, background:'rgba(252,129,129,0.05)', border:'0.5px solid rgba(252,129,129,0.2)' }}>
              <div style={{ fontSize:7, color:'var(--red)', fontFamily:'var(--mono)', marginBottom:4, letterSpacing:1 }}>
                ERRORS ({state.errors.length})
              </div>
              {state.errors.slice(-4).map((e,i) => (
                <div key={i} style={{ fontSize:8, color:'rgba(252,129,129,0.6)', fontFamily:'var(--mono)', marginBottom:2 }}>{e}</div>
              ))}
            </div>
          )}

          {/* Job history */}
          {jobs.slice(0,3).map(j => {
            const c = {pending:'var(--text3)',running:'var(--gold)',done:'var(--green)',failed:'var(--red)'}[j.status]||'var(--text3)';
            return (
              <div key={j.id} style={{ padding:'6px 10px', borderRadius:7, background:'var(--panel2)', border:`0.5px solid var(--border)`, marginBottom:4, borderLeft:`2px solid ${c}` }}>
                <div style={{ display:'flex', justifyContent:'space-between' }}>
                  <span style={{ fontSize:9, fontFamily:'var(--mono)', color:'var(--text2)' }}>{j.job_type} · {j.target}</span>
                  <span style={{ fontSize:8, color:c, fontFamily:'var(--mono)', textTransform:'uppercase', fontWeight:700 }}>{j.status}</span>
                </div>
                <div style={{ fontSize:7, color:'var(--text3)', fontFamily:'var(--mono)', marginTop:2 }}>
                  #{j.id} · {new Date(j.created_at).toLocaleString('id-ID')}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* ── Confirm Dialog ── */}
      {confirmDialog && (
        <div style={{
          position:'absolute', inset:0, background:'rgba(6,8,16,0.85)',
          backdropFilter:'blur(8px)', borderRadius:16, zIndex:10,
          display:'flex', alignItems:'center', justifyContent:'center',
        }}>
          <div style={{
            width:380, background:'var(--panel2)', borderRadius:14,
            border:'0.5px solid var(--border2)', overflow:'hidden',
            boxShadow:'0 0 60px rgba(0,0,0,0.6)',
          }}>
            {confirmDialog === 'stop' ? (
              <>
                <div style={{ padding:'18px 20px', borderBottom:'0.5px solid var(--border)' }}>
                  <div style={{ fontSize:14, fontWeight:700, fontFamily:'var(--mono)', color:'var(--text)', marginBottom:6 }}>
                    ■ Stop Mining Run?
                  </div>
                  <div style={{ fontSize:11, color:'var(--text2)', lineHeight:1.7 }}>
                    All active workers will finish their current page then stop.
                    Progress is saved — you can restart later.
                  </div>
                </div>
                <div style={{ display:'flex', gap:8, padding:'14px 20px' }}>
                  <button onClick={stopAgent} style={{
                    flex:1, padding:'9px', borderRadius:8, fontSize:12,
                    fontFamily:'var(--mono)', fontWeight:700, cursor:'pointer',
                    background:'rgba(252,129,129,0.18)', color:'var(--red)',
                    border:'0.5px solid rgba(252,129,129,0.4)',
                  }}>■ Yes, Stop</button>
                  <button onClick={() => setConfirmDialog(null)} style={{
                    padding:'9px 18px', borderRadius:8, fontSize:12,
                    fontFamily:'var(--mono)', cursor:'pointer',
                    background:'var(--panel)', color:'var(--text2)',
                    border:'0.5px solid var(--border)',
                  }}>Cancel</button>
                </div>
              </>
            ) : (
              // Restart dialog
              <>
                <div style={{ padding:'18px 20px', borderBottom:'0.5px solid var(--border)' }}>
                  <div style={{ fontSize:14, fontWeight:700, fontFamily:'var(--mono)', color:'var(--text)', marginBottom:6 }}>
                    ↺ Restart Mining Run
                  </div>
                  <div style={{ fontSize:11, color:'var(--text2)', lineHeight:1.7 }}>
                    Choose how to restart:
                  </div>
                </div>

                {/* Option 1: Skip already dug */}
                <div style={{ margin:'12px 16px 0', borderRadius:10, padding:'14px',
                  background:'rgba(99,179,237,0.06)', border:'0.5px solid rgba(99,179,237,0.2)',
                  cursor:'pointer', transition:'background .15s' }}
                  onClick={async () => { setConfirmDialog(null); await stopAgent(); setTimeout(() => startAgent('skip'), 1000); }}
                  onMouseEnter={e=>e.currentTarget.style.background='rgba(99,179,237,0.12)'}
                  onMouseLeave={e=>e.currentTarget.style.background='rgba(99,179,237,0.06)'}
                >
                  <div style={{ display:'flex', gap:10, alignItems:'flex-start' }}>
                    <span style={{ fontSize:20, flexShrink:0 }}>⏭</span>
                    <div>
                      <div style={{ fontSize:12, fontWeight:700, color:'var(--accent2)', marginBottom:4 }}>
                        Resume — skip already dug
                      </div>
                      <div style={{ fontSize:10, color:'var(--text2)', lineHeight:1.7 }}>
                        Keep all existing data. Skip Wikipedia pages that were already crawled.
                        Pick up where we left off — only new links will be followed.
                      </div>
                      <div style={{ fontSize:9, color:'var(--text3)', fontFamily:'var(--mono)', marginTop:6 }}>
                        ✓ Faster · ✓ No data loss · Best for: continuing an interrupted run
                      </div>
                    </div>
                  </div>
                </div>

                {/* Option 2: Fresh restart */}
                <div style={{ margin:'8px 16px 14px', borderRadius:10, padding:'14px',
                  background:'rgba(252,129,129,0.06)', border:'0.5px solid rgba(252,129,129,0.2)',
                  cursor:'pointer', transition:'background .15s' }}
                  onClick={async () => { setConfirmDialog(null); await stopAgent(); setTimeout(() => startAgent('fresh'), 1000); }}
                  onMouseEnter={e=>e.currentTarget.style.background='rgba(252,129,129,0.12)'}
                  onMouseLeave={e=>e.currentTarget.style.background='rgba(252,129,129,0.06)'}
                >
                  <div style={{ display:'flex', gap:10, alignItems:'flex-start' }}>
                    <span style={{ fontSize:20, flexShrink:0 }}>🔄</span>
                    <div>
                      <div style={{ fontSize:12, fontWeight:700, color:'var(--red)', marginBottom:4 }}>
                        Full Restart — re-dig everything
                      </div>
                      <div style={{ fontSize:10, color:'var(--text2)', lineHeight:1.7 }}>
                        <strong style={{color:'var(--red)'}}>Wipes all data</strong> — persons, relations,
                        news, and Neo4j graph — then crawls everything from scratch.
                      </div>
                      <div style={{ fontSize:9, color:'var(--text3)', fontFamily:'var(--mono)', marginTop:6 }}>
                        ⚠ Destructive · Slower · Best for: after config changes or data corruption
                      </div>
                    </div>
                  </div>
                </div>

                <div style={{ padding:'0 16px 14px' }}>
                  <button onClick={() => setConfirmDialog(null)} style={{
                    width:'100%', padding:'8px', borderRadius:8, fontSize:11,
                    fontFamily:'var(--mono)', cursor:'pointer',
                    background:'var(--panel)', color:'var(--text3)',
                    border:'0.5px solid var(--border)',
                  }}>Cancel</button>
                </div>
              </>
            )}
          </div>
        </div>
      )}

    </div>
  );
}
