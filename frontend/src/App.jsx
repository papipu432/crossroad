import { useState, useEffect, useCallback, useRef } from 'react';
import { api, partyColor, ROLE_LABELS, ROLE_COLORS, QUICK } from './lib.js';
import GraphCanvas from './GraphCanvas.jsx';
import PersonPanel from './PersonPanel.jsx';
import AgentDashboard from './AgentDashboard.jsx';
import QueryPanel from './QueryPanel.jsx';
import DynastyPanel from './DynastyPanel.jsx';
import CoalitionPanel from './CoalitionPanel.jsx';

function Spinner({ size=14, color='var(--accent)' }) {
  return (
    <span style={{
      display:'inline-block', width:size, height:size, borderRadius:'50%',
      border:`2px solid ${color}22`, borderTopColor:color,
      animation:'spin .7s linear infinite', flexShrink:0,
    }}/>
  );
}

function MiningIndicator({ state }) {
  if (!state || state.status === 'idle' || state.status === 'done') return null;
  const STATUS_COLOR = {
    discovering:'var(--gold)', l1_running:'var(--accent)',
    l2_running:'var(--purple)', l3_running:'var(--teal)',
    paused:'var(--text3)', error:'var(--red)',
  };
  const c = STATUS_COLOR[state.status] || 'var(--accent)';
  const total = state.l1_total || 1;
  const done  = (state.l1_done||0) + (state.l2_done||0) + (state.l3_done||0);
  const pct   = Math.min(100, Math.round((done / (total * 3)) * 100));

  return (
    <div style={{
      display:'flex', alignItems:'center', gap:8,
      padding:'4px 10px', borderRadius:20,
      background:`${c}12`, border:`0.5px solid ${c}30`,
    }}>
      <Spinner size={10} color={c} />
      <span style={{ fontSize:9, color:c, fontFamily:'var(--mono)', whiteSpace:'nowrap' }}>
        {state.phase_label?.slice(0,35) || state.status}
      </span>
      <div style={{ width:50, height:3, borderRadius:2, background:`${c}20`, overflow:'hidden' }}>
        <div style={{ height:'100%', width:`${pct}%`, background:c, transition:'width .5s' }}/>
      </div>
      <span style={{ fontSize:9, color:c, fontFamily:'var(--mono)' }}>{pct}%</span>
    </div>
  );
}

export default function App() {
  const [health,     setHealth]     = useState(null);
  const [stats,      setStats]      = useState(null);
  const [graphData,  setGraphData]  = useState({nodes:[],edges:[]});
  const [centerSlug, setCenterSlug] = useState(null);
  const [persons,    setPersons]    = useState([]);
  const [activeRole, setActiveRole] = useState('all');
  const [selectedSlug,  setSelectedSlug]  = useState(null);
  const [showAgent,  setShowAgent]  = useState(false);
  const [showQuery,  setShowQuery]  = useState(false);
  const [showDynasty,setShowDynasty]= useState(false);
  const [showCoalition,setShowCoalition]=useState(false);
  const [showPath,   setShowPath]   = useState(false);
  const [pathA,      setPathA]      = useState('');
  const [pathB,      setPathB]      = useState('');
  const [pathResult, setPathResult] = useState(null);
  const [searchQ,    setSearchQ]    = useState('');
  const [hints,      setHints]      = useState([]);
  const [hintFocus,  setHintFocus]  = useState(false);
  const [graphLoading, setGraphLoading] = useState(false);
  const [graphMode,  setGraphMode]  = useState('full');
  const [agentState, setAgentState] = useState(null);
  const sseRef = useRef(null);

  // Live agent state via SSE
  useEffect(() => {
    const es = new EventSource('/api/agent/stream');
    sseRef.current = es;
    es.onmessage = (e) => {
      try { setAgentState(JSON.parse(e.data)); } catch {}
    };
    return () => es.close();
  }, []);

  useEffect(() => {
    api.health().then(setHealth).catch(()=>
      setHealth({neo4j:'disconnected',redis:'disconnected',ollama:'disconnected',chroma:'disconnected'}));
    const t = setInterval(() => api.health().then(setHealth).catch(()=>{}), 30000);
    return () => clearInterval(t);
  }, []);

  useEffect(() => {
    api.stats().then(setStats).catch(()=>{});
    const t = setInterval(() => api.stats().then(setStats).catch(()=>{}), 20000);
    return () => clearInterval(t);
  }, []);

  useEffect(() => { loadFullGraph(); }, []);

  const loadFullGraph = useCallback(async () => {
    setGraphLoading(true); setCenterSlug(null); setGraphMode('full');
    try { setGraphData(await api.fullGraph(500)); } catch {}
    setGraphLoading(false);
  }, []);

  const loadEgoGraph = useCallback(async (slug) => {
    setGraphLoading(true); setGraphMode('ego'); setCenterSlug(slug);
    try { setGraphData(await api.egoGraph(slug, 2)); } catch {}
    setGraphLoading(false);
  }, []);

  useEffect(() => {
    if (!searchQ || searchQ.length < 2) { setHints([]); return; }
    const t = setTimeout(async () => {
      const r = await api.searchPersons(searchQ).catch(()=>({results:[]}));
      setHints(r.results||[]);
    }, 250);
    return () => clearTimeout(t);
  }, [searchQ]);

  useEffect(() => {
    const role = activeRole==='all' ? undefined : activeRole;
    api.persons({role_type:role, limit:300}).then(r=>setPersons(r.persons||[])).catch(()=>{});
  }, [activeRole]);

  const selectPerson = useCallback((slug) => {
    setSelectedSlug(slug); loadEgoGraph(slug);
    setSearchQ(''); setHints([]);
  }, [loadEgoGraph]);

  const findPath = useCallback(async () => {
    if (!pathA || !pathB) return;
    setPathResult(null);
    const r = await api.pathBetween(pathA, pathB).catch(()=>({found:false}));
    if (r.found) { setGraphData(r); setCenterSlug(pathA); setShowPath(false); }
    setPathResult(r);
  }, [pathA, pathB]);

  const roleCounts = persons.reduce((acc,p) => {
    acc[p.role_type] = (acc[p.role_type]||0)+1; return acc;
  }, {});

  const ROLES = ['all','presiden','wapres','menteri','dpr','dprd','gubernur','bupati','walikota'];
  const DOT = (ok) => ({ color: ok?'var(--green)':'var(--red)', fontSize:9, fontFamily:'var(--mono)' });

  return (
    <div style={{ height:'100%', display:'flex', flexDirection:'column', overflow:'hidden' }}>
      <div className="scanline"/>

      {/* TOP BAR */}
      <header style={{
        height:52, background:'var(--bg2)', borderBottom:'0.5px solid var(--border)',
        display:'flex', alignItems:'center', gap:10, padding:'0 14px',
        flexShrink:0, zIndex:50,
      }}>
        {/* Logo */}
        <div style={{ display:'flex', alignItems:'center', gap:8, flexShrink:0 }}>
          <div style={{
            width:28, height:28, borderRadius:6,
            background:'linear-gradient(135deg,#1a3a5c,#0d1a2e)',
            border:'1px solid rgba(99,179,237,0.3)',
            display:'flex', alignItems:'center', justifyContent:'center', fontSize:14,
          }}>🇮🇩</div>
          <div>
            <div style={{ fontSize:13, fontWeight:800, letterSpacing:3, color:'var(--text)', fontFamily:'var(--mono)' }}>CROSSROAD</div>
            <div style={{ fontSize:8, color:'var(--text3)', fontFamily:'var(--mono)', letterSpacing:1 }}>KNOWLEDGE GRAPH</div>
          </div>
        </div>

        {/* Search */}
        <div style={{ flex:1, maxWidth:460, position:'relative' }}>
          <input
            value={searchQ}
            onChange={e=>setSearchQ(e.target.value)}
            onFocus={()=>setHintFocus(true)}
            onBlur={()=>setTimeout(()=>setHintFocus(false),200)}
            placeholder="Search — Prabowo, Sri Mulyani, Megawati…"
            style={{
              width:'100%', padding:'7px 14px 7px 32px', borderRadius:20, fontSize:12,
              background:'var(--panel)', color:'var(--text)',
              border:`0.5px solid ${hintFocus?'rgba(99,179,237,.4)':'var(--border)'}`,
              outline:'none', fontFamily:'var(--sans)',
            }}
          />
          <span style={{ position:'absolute', left:11, top:'50%', transform:'translateY(-50%)', color:'var(--text3)', fontSize:12 }}>⌕</span>
          {hintFocus && (hints.length > 0 || QUICK.length > 0) && (
            <div style={{
              position:'absolute', top:'calc(100% + 6px)', left:0, right:0, zIndex:200,
              background:'var(--panel)', border:'0.5px solid var(--border2)',
              borderRadius:10, overflow:'hidden', boxShadow:'0 8px 32px rgba(0,0,0,.5)',
            }}>
              {(hints.length > 0 ? hints : QUICK.map(n=>({full_name:n,slug:n.toLowerCase().replace(/ /g,'-')}))).map((p,i)=>(
                <div key={i} onClick={()=>selectPerson(p.slug||p.full_name?.toLowerCase().replace(/ /g,'-'))}
                  style={{ display:'flex', gap:10, padding:'8px 12px', cursor:'pointer',
                    borderBottom:'0.5px solid var(--border)', transition:'background .1s' }}
                  onMouseEnter={e=>e.currentTarget.style.background='var(--panel2)'}
                  onMouseLeave={e=>e.currentTarget.style.background=''}
                >
                  <div style={{
                    width:26, height:26, borderRadius:'50%', flexShrink:0,
                    background:`${partyColor(p.party)}25`, border:`1px solid ${partyColor(p.party)}50`,
                    display:'flex', alignItems:'center', justifyContent:'center',
                    fontSize:9, fontWeight:700, color:partyColor(p.party), fontFamily:'var(--mono)',
                  }}>
                    {(p.full_name||'?').split(' ').map(w=>w[0]).join('').slice(0,2).toUpperCase()}
                  </div>
                  <div>
                    <div style={{ fontSize:12, color:'var(--text)', fontWeight:500 }}>{p.full_name}</div>
                    {p.role_type && <div style={{ fontSize:9, color:'var(--text3)', fontFamily:'var(--mono)' }}>{p.role_type}{p.party?` · ${p.party}`:''}</div>}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Stats */}
        {stats && (
          <div style={{ display:'flex', gap:6, flexShrink:0 }}>
            {[
              {v:stats.total_persons, l:'Persons',   c:'var(--accent)'},
              {v:stats.total_rels,    l:'Relations', c:'var(--purple)'},
              {v:stats.total_news,    l:'Articles',  c:'var(--gold)'},
              {v:stats.chroma_persons,l:'Vectors',   c:'var(--green)'},
            ].map(s=>(
              <div key={s.l} style={{
                padding:'3px 9px', borderRadius:20, background:`${s.c}12`,
                border:`0.5px solid ${s.c}35`, display:'flex', gap:4, alignItems:'center',
              }}>
                <span style={{ fontSize:12, fontWeight:700, color:s.c, fontFamily:'var(--mono)' }}>{s.v??'…'}</span>
                <span style={{ fontSize:8, color:'var(--text3)', fontFamily:'var(--mono)' }}>{s.l}</span>
              </div>
            ))}
          </div>
        )}

        {/* Mining indicator */}
        <MiningIndicator state={agentState} />

        {/* Actions */}
        <div style={{ display:'flex', gap:5, flexShrink:0 }}>
          <button onClick={()=>setShowQuery(true)} style={{
            padding:'6px 11px', borderRadius:8, fontSize:10, fontFamily:'var(--mono)',
            background:'rgba(168,85,247,0.12)', color:'var(--purple)',
            border:'0.5px solid rgba(168,85,247,0.3)', cursor:'pointer',
          }}>🧠 Query</button>
          <button onClick={()=>setShowDynasty(true)} style={{
            padding:'6px 11px', borderRadius:8, fontSize:10, fontFamily:'var(--mono)',
            background:'rgba(252,129,129,0.1)', color:'#fc8181',
            border:'0.5px solid rgba(252,129,129,0.28)', cursor:'pointer',
          }}>🏛 Dinasti</button>
          <button onClick={()=>setShowCoalition(true)} style={{
            padding:'6px 11px', borderRadius:8, fontSize:10, fontFamily:'var(--mono)',
            background:'rgba(104,211,145,0.1)', color:'var(--green)',
            border:'0.5px solid rgba(104,211,145,0.28)', cursor:'pointer',
          }}>🤝 Koalisi</button>
          <button onClick={()=>setShowPath(true)} style={{
            padding:'6px 11px', borderRadius:8, fontSize:10, fontFamily:'var(--mono)',
            background:'rgba(99,179,237,0.1)', color:'var(--accent2)',
            border:'0.5px solid rgba(99,179,237,0.25)', cursor:'pointer',
          }}>⟷ Path</button>
          <button onClick={loadFullGraph} disabled={graphLoading} style={{
            padding:'6px 11px', borderRadius:8, fontSize:10, fontFamily:'var(--mono)',
            background:'rgba(99,179,237,0.08)', color:'var(--text3)',
            border:'0.5px solid var(--border)', cursor:'pointer',
          }}>◎ Full</button>
          <button onClick={()=>setShowAgent(true)} style={{
            padding:'6px 11px', borderRadius:8, fontSize:10, fontFamily:'var(--mono)',
            background:'rgba(246,173,85,0.12)', color:'var(--gold)',
            border:'0.5px solid rgba(246,173,85,0.3)', cursor:'pointer',
          }}>⚡ Agent</button>
        </div>

        {/* Health dots */}
        {health && (
          <div style={{ display:'flex', gap:8, flexShrink:0 }}>
            {[['Neo4j',health.neo4j],['Redis',health.redis],['Ollama',health.ollama],['Chroma',health.chroma]].map(([l,v])=>(
              <span key={l} style={DOT(v==='connected')}>
                {v==='connected'?'●':'○'} {l}
              </span>
            ))}
          </div>
        )}
      </header>

      {/* ROLE FILTER BAR */}
      <div style={{
        height:38, background:'var(--bg2)', borderBottom:'0.5px solid var(--border)',
        display:'flex', alignItems:'center', gap:5, padding:'0 14px',
        overflowX:'auto', flexShrink:0,
      }}>
        {ROLES.map(r => {
          const c = ROLE_COLORS[r] || 'var(--text3)';
          const active = activeRole===r;
          return (
            <button key={r} onClick={()=>setActiveRole(r)} style={{
              padding:'4px 11px', borderRadius:20, fontSize:10, cursor:'pointer',
              background: active ? `${c}22` : 'transparent',
              color: active ? c : 'var(--text3)',
              border:`0.5px solid ${active ? c+'55' : 'var(--border)'}`,
              fontFamily:'var(--mono)', whiteSpace:'nowrap',
            }}>
              {r==='all'?'All':ROLE_LABELS[r]||r}
              {r!=='all' && roleCounts[r] ? <span style={{ opacity:.6, marginLeft:4 }}>{roleCounts[r]}</span> : null}
            </button>
          );
        })}
        {graphLoading && (
          <div style={{ marginLeft:'auto', display:'flex', gap:6, alignItems:'center' }}>
            <Spinner size={11}/>
            <span style={{ fontSize:9, color:'var(--text3)', fontFamily:'var(--mono)' }}>
              {graphMode==='ego'?'Building ego network…':'Loading graph…'}
            </span>
          </div>
        )}
      </div>

      {/* MAIN AREA */}
      <div style={{ flex:1, display:'flex', overflow:'hidden' }}>

        {/* LEFT SIDEBAR */}
        <div style={{
          width:210, background:'var(--panel)', borderRight:'0.5px solid var(--border)',
          display:'flex', flexDirection:'column', flexShrink:0, overflow:'hidden',
        }}>
          <div style={{
            padding:'8px 12px 5px', borderBottom:'0.5px solid var(--border)',
            fontSize:9, color:'var(--text3)', fontFamily:'var(--mono)', letterSpacing:1,
          }}>
            {activeRole==='all'?'SEMUA POLITISI':(ROLE_LABELS[activeRole]||activeRole).toUpperCase()}
            <span style={{ float:'right', color:'var(--accent)' }}>{persons.length}</span>
          </div>
          <div style={{ flex:1, overflowY:'auto' }}>
            {persons.map((p,i)=>{
              const pc=partyColor(p.party);
              const sel=p.slug===selectedSlug;
              return (
                <div key={i} onClick={()=>selectPerson(p.slug)}
                  style={{
                    display:'flex', gap:7, padding:'6px 10px', cursor:'pointer',
                    background:sel?`${pc}12`:'transparent',
                    borderLeft:sel?`2px solid ${pc}`:'2px solid transparent',
                    borderBottom:'0.5px solid var(--border)', transition:'background .12s',
                  }}
                  onMouseEnter={e=>{ if(!sel)e.currentTarget.style.background='var(--panel2)'; }}
                  onMouseLeave={e=>{ if(!sel)e.currentTarget.style.background='transparent'; }}
                >
                  <div style={{
                    width:26, height:26, borderRadius:'50%', flexShrink:0,
                    background:`${pc}22`, border:`1px solid ${pc}45`,
                    display:'flex', alignItems:'center', justifyContent:'center',
                    fontSize:9, fontWeight:700, color:pc, fontFamily:'var(--mono)',
                  }}>{(p.full_name||'?').split(' ').map(w=>w[0]).join('').slice(0,2).toUpperCase()}</div>
                  <div style={{ minWidth:0 }}>
                    <div style={{ fontSize:11, fontWeight:500, color:sel?'var(--text)':'var(--text2)',
                      overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap' }}>
                      {p.full_name}
                    </div>
                    <div style={{ fontSize:9, color:'var(--text3)', fontFamily:'var(--mono)', marginTop:1 }}>
                      {p.party}{p.province?` · ${p.province?.split(' ')[0]}`:''}
                    </div>
                  </div>
                </div>
              );
            })}
            {persons.length===0 && (
              <div style={{ padding:'16px 12px', fontSize:11, color:'var(--text3)', lineHeight:1.9 }}>
                Tidak ada data.<br/>
                <button onClick={()=>setShowAgent(true)} style={{
                  marginTop:8, padding:'5px 12px', borderRadius:8, fontSize:10,
                  fontFamily:'var(--mono)', background:'rgba(246,173,85,0.12)',
                  color:'var(--gold)', border:'0.5px solid rgba(246,173,85,0.3)', cursor:'pointer',
                }}>⚡ Start Agent</button>
              </div>
            )}
          </div>
        </div>

        {/* GRAPH CANVAS */}
        <div style={{ flex:1, position:'relative', background:'var(--bg)', overflow:'hidden' }}>
          {/* Graph mode pill */}
          <div style={{
            position:'absolute', top:10, left:10, zIndex:10,
            background:'rgba(11,14,26,0.85)', border:'0.5px solid var(--border)',
            borderRadius:8, padding:'4px 10px', backdropFilter:'blur(8px)',
            fontSize:9, fontFamily:'var(--mono)', color:'var(--text3)',
          }}>
            {graphMode==='ego'
              ? `◉ Ego · ${graphData?.nodes?.length||0}n · ${graphData?.edges?.length||0}e`
              : `◎ Full · ${graphData?.nodes?.length||0}n · ${graphData?.edges?.length||0}e`
            }
            {graphMode==='ego' && (
              <button onClick={loadFullGraph} style={{ background:'none', border:'none', cursor:'pointer', color:'var(--text3)', fontSize:9, fontFamily:'var(--mono)', marginLeft:8, padding:0 }}>← Full</button>
            )}
          </div>

          {graphData?.nodes?.length === 0 && !graphLoading ? (
            <div style={{
              position:'absolute', inset:0, display:'flex', flexDirection:'column',
              alignItems:'center', justifyContent:'center', gap:16,
            }}>
              {[180,280,380].map(r=>(
                <div key={r} style={{
                  position:'absolute', width:r, height:r, borderRadius:'50%',
                  border:'0.5px solid rgba(99,179,237,0.06)',
                  top:'50%', left:'50%', transform:'translate(-50%,-50%)',
                }}/>
              ))}
              <div style={{ textAlign:'center', zIndex:1 }}>
                <div style={{ fontSize:44, marginBottom:12, opacity:.4 }}>🕸</div>
                <div style={{ fontSize:16, fontWeight:800, color:'var(--text)', letterSpacing:-0.3, marginBottom:8 }}>
                  Knowledge Graph Empty
                </div>
                <div style={{ fontSize:11, color:'var(--text2)', lineHeight:1.9, maxWidth:320 }}>
                  Launch the autonomous agent to begin 24-hour deep mining of all Indonesian officials.
                </div>
                <button onClick={()=>setShowAgent(true)} style={{
                  marginTop:16, padding:'9px 22px', borderRadius:10, fontSize:12,
                  fontFamily:'var(--mono)', background:'rgba(246,173,85,0.15)',
                  color:'var(--gold)', border:'0.5px solid rgba(246,173,85,0.35)', cursor:'pointer',
                }}>⚡ Launch Agent</button>
              </div>
            </div>
          ) : (
            <GraphCanvas
              data={graphData}
              centerSlug={centerSlug}
              onNodeClick={node => {
                const slug = node.slug || node.id;
                if ((node._label==='Person'||!node._label) && slug) {
                  setSelectedSlug(slug); loadEgoGraph(slug);
                }
              }}
            />
          )}

          {/* Legend */}
          <div style={{
            position:'absolute', bottom:14, left:14, zIndex:10,
            background:'rgba(11,14,26,0.88)', border:'0.5px solid var(--border)',
            borderRadius:10, padding:'8px 12px', backdropFilter:'blur(8px)',
            fontSize:8, fontFamily:'var(--mono)',
          }}>
            <div style={{ color:'var(--text3)', letterSpacing:1, marginBottom:6 }}>LEGEND</div>
            <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:'3px 14px' }}>
              {[
                {c:'var(--accent)',  l:'Politisi'},
                {c:'#b794f4', l:'Keluarga'},
                {c:'#f6ad55', l:'Partai'},
                {c:'#68d391', l:'Universitas'},
                {c:'#fc8181', l:'Perusahaan'},
                {c:'#4fd1c5', l:'Instansi Pemerintah'},
              ].map(n=>(
                <div key={n.l} style={{ display:'flex', alignItems:'center', gap:5, color:'var(--text3)' }}>
                  <div style={{ width:7, height:7, borderRadius:'50%', background:n.c, flexShrink:0 }}/>{n.l}
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* PERSON PANEL */}
        {selectedSlug && (
          <PersonPanel
            slug={selectedSlug}
            onClose={()=>setSelectedSlug(null)}
            onNavigate={slug=>{ setSelectedSlug(slug); loadEgoGraph(slug); }}
          />
        )}
      </div>

      {/* PATH MODAL */}
      {showPath && (
        <div style={{
          position:'fixed', inset:0, background:'rgba(6,8,16,0.85)',
          backdropFilter:'blur(8px)', zIndex:200,
          display:'flex', alignItems:'center', justifyContent:'center',
        }}>
          <div style={{
            width:440, background:'var(--panel)', border:'0.5px solid var(--border2)',
            borderRadius:14, padding:22, boxShadow:'0 0 60px rgba(168,85,247,.12)',
          }}>
            <div style={{ display:'flex', justifyContent:'space-between', marginBottom:16 }}>
              <div style={{ fontSize:13, fontWeight:700, fontFamily:'var(--mono)', color:'var(--text)' }}>
                ⟷ SHORTEST PATH
              </div>
              <button onClick={()=>setShowPath(false)} style={{ background:'none', border:'none', cursor:'pointer', color:'var(--text3)', fontSize:16 }}>✕</button>
            </div>
            <p style={{ fontSize:11, color:'var(--text2)', marginBottom:14, lineHeight:1.7 }}>
              Find shortest relationship chain between two Indonesian officials in the knowledge graph.
            </p>
            {['Person A (slug, e.g. prabowo-subianto)', 'Person B (slug, e.g. megawati-soekarnoputri)'].map((ph,i)=>(
              <input key={i} placeholder={ph}
                value={i===0?pathA:pathB}
                onChange={e=>i===0?setPathA(e.target.value):setPathB(e.target.value)}
                style={{
                  width:'100%', padding:'8px 12px', borderRadius:8, fontSize:11,
                  background:'var(--panel2)', color:'var(--text)',
                  border:'0.5px solid var(--border)', marginBottom:8,
                  fontFamily:'var(--mono)', outline:'none',
                }}
              />
            ))}
            {pathResult && !pathResult.found && (
              <div style={{ fontSize:11, color:'var(--red)', fontFamily:'var(--mono)', marginBottom:8 }}>
                No path found within 5 hops.
              </div>
            )}
            <div style={{ display:'flex', gap:8 }}>
              <button onClick={findPath} style={{
                flex:1, padding:'8px', borderRadius:8, fontSize:12, fontFamily:'var(--mono)',
                background:'rgba(168,85,247,0.15)', color:'var(--purple)',
                border:'0.5px solid rgba(168,85,247,0.3)', cursor:'pointer',
              }}>Find Path</button>
              <button onClick={()=>setShowPath(false)} style={{
                padding:'8px 14px', borderRadius:8, fontSize:12, fontFamily:'var(--mono)',
                background:'var(--panel2)', color:'var(--text2)',
                border:'0.5px solid var(--border)', cursor:'pointer',
              }}>Cancel</button>
            </div>
          </div>
        </div>
      )}

      {showAgent && <AgentDashboard onClose={()=>setShowAgent(false)} />}
      {showDynasty && (
        <div style={{
          position:'fixed', inset:0, background:'rgba(6,8,16,0.9)',
          backdropFilter:'blur(10px)', zIndex:300,
          display:'flex', flexDirection:'column', overflow:'hidden',
        }}>
          <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center',
            padding:'10px 18px', borderBottom:'0.5px solid var(--border)',
            background:'var(--panel)', flexShrink:0 }}>
            <span style={{ fontSize:13, fontWeight:700, fontFamily:'var(--mono)', color:'var(--text)' }}>
              🏛 DETEKSI DINASTI POLITIK INDONESIA
            </span>
            <button onClick={()=>setShowDynasty(false)} style={{
              background:'none', border:'none', cursor:'pointer', color:'var(--text3)', fontSize:18 }}>✕</button>
          </div>
          <div style={{ flex:1, overflow:'hidden' }}>
            <DynastyPanel onNavigate={slug => { setShowDynasty(false); selectPerson(slug); }} />
          </div>
        </div>
      )}
      {showCoalition && (
        <div style={{
          position:'fixed', inset:0, background:'rgba(6,8,16,0.9)',
          backdropFilter:'blur(10px)', zIndex:300,
          display:'flex', flexDirection:'column', overflow:'hidden',
        }}>
          <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center',
            padding:'10px 18px', borderBottom:'0.5px solid var(--border)',
            background:'var(--panel)', flexShrink:0 }}>
            <span style={{ fontSize:13, fontWeight:700, fontFamily:'var(--mono)', color:'var(--text)' }}>
              🤝 KOALISI & FRAKSI POLITIK INDONESIA
            </span>
            <button onClick={()=>setShowCoalition(false)} style={{
              background:'none', border:'none', cursor:'pointer', color:'var(--text3)', fontSize:18 }}>✕</button>
          </div>
          <div style={{ flex:1, overflow:'hidden' }}>
            <CoalitionPanel onNavigate={slug => { setShowCoalition(false); selectPerson(slug); }} />
          </div>
        </div>
      )}
      {showQuery  && <QueryPanel
        onClose={()=>setShowQuery(false)}
        onNavigate={slug=>{ setShowQuery(false); selectPerson(slug); }}
      />}
    </div>
  );
}
