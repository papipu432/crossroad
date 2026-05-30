import { useState, useEffect } from 'react';
import { api, partyColor, NEWS_CAT_COLORS, ROLE_LABELS, ROLE_COLORS } from './lib.js';

// ── Atoms ──────────────────────────────────────────────────────────────────────

function SourceLink({ name, url }) {
  if (!url || url === 'internal') return (
    <span style={{ fontSize:9, color:'var(--text3)', fontFamily:'var(--mono)' }}>{name}</span>
  );
  return (
    <a href={url} target="_blank" rel="noopener noreferrer" title={url} style={{
      display:'inline-flex', alignItems:'center', gap:3,
      padding:'2px 8px', borderRadius:10, fontSize:9,
      background:'rgba(99,179,237,0.08)', color:'var(--accent2)',
      border:'0.5px solid rgba(99,179,237,0.2)', fontFamily:'var(--mono)',
      textDecoration:'none', whiteSpace:'nowrap', lineHeight:1.8,
      transition:'background .12s',
    }}
    onMouseEnter={e=>e.currentTarget.style.background='rgba(99,179,237,0.18)'}
    onMouseLeave={e=>e.currentTarget.style.background='rgba(99,179,237,0.08)'}
    >↗ {name}</a>
  );
}

function Tag({ label, color='var(--accent)' }) {
  return (
    <span style={{
      padding:'1px 8px', borderRadius:10, fontSize:10, fontWeight:500,
      background:`${color}22`, color, border:`0.5px solid ${color}44`,
      fontFamily:'var(--mono)', whiteSpace:'nowrap',
    }}>{label}</span>
  );
}

function Section({ title, children, defaultOpen=true, count }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div style={{ borderBottom:'0.5px solid var(--border)', paddingBottom:10, marginBottom:10 }}>
      <button onClick={()=>setOpen(v=>!v)} style={{
        display:'flex', alignItems:'center', justifyContent:'space-between',
        width:'100%', background:'none', border:'none', cursor:'pointer',
        padding:'0 0 7px', color:'var(--text3)', fontFamily:'var(--mono)',
        fontSize:9, textTransform:'uppercase', letterSpacing:1.5,
      }}>
        <span>{title}{count!==undefined ? ` (${count})` : ''}</span>
        <span style={{ fontSize:10 }}>{open ? '▾' : '▸'}</span>
      </button>
      {open && <div className="fade-in">{children}</div>}
    </div>
  );
}

function ScoreBar({ score, label='Party Alignment' }) {
  if (score === null || score === undefined) return null;
  const pct = Math.round(((score+1)/2)*100);
  const color = score>0.25?'var(--green)':score<-0.25?'var(--red)':'var(--gold)';
  const text  = score>0.25?'Aligned':score<-0.25?'Critical':'Neutral';
  return (
    <div>
      <div style={{ display:'flex', justifyContent:'space-between', marginBottom:3 }}>
        <span style={{ fontSize:9, color:'var(--text3)', fontFamily:'var(--mono)' }}>{label}</span>
        <span style={{ fontSize:9, color, fontFamily:'var(--mono)', fontWeight:700 }}>
          {text} ({score>0?'+':''}{(score||0).toFixed(2)})
        </span>
      </div>
      <div className="score-track"><div className="score-fill" style={{ width:`${pct}%`, background:color }}/></div>
    </div>
  );
}

// ── Relationship item with evidence ───────────────────────────────────────────

function RelItem({ rel, selfName, onNavigate }) {
  const [expanded, setExpanded] = useState(false);
  const isFrom = rel.from_id !== undefined; // came from "from" side

  const REL_COLORS = {
    FAMILY_OF:'#b794f4', MEMBER_OF:'#f6ad55', WORKS_AT:'#4fd1c5',
    STUDIED_AT:'#68d391', OWNS:'#fc8181', ALLIED_WITH:'#63b3ed',
    RIVAL_OF:'#fc8181', APPOINTED_BY:'#f6ad55', RELATED_TO:'#454e60',
  };
  const color = REL_COLORS[rel.rel_type] || '#454e60';

  // Parse sources from JSON string if needed
  let sources = [];
  if (rel.sources) {
    try {
      sources = typeof rel.sources === 'string' ? JSON.parse(rel.sources) : rel.sources;
    } catch {}
  }

  return (
    <div style={{
      padding:'8px 10px', borderRadius:8, background:'var(--panel2)',
      border:'0.5px solid var(--border)', marginBottom:6,
      borderLeft:`2px solid ${color}`,
    }}>
      <div style={{ display:'flex', alignItems:'center', gap:7, flexWrap:'wrap' }}>
        <span style={{
          fontSize:9, padding:'1px 7px', borderRadius:8,
          background:`${color}22`, color, fontFamily:'var(--mono)',
          textTransform:'uppercase',
        }}>{rel.rel_type?.replace('_',' ')}</span>
        {rel.subtype && (
          <span style={{ fontSize:9, color:'var(--text3)', fontFamily:'var(--mono)' }}>
            {rel.subtype}
          </span>
        )}
        {rel.label && rel.label !== rel.rel_type && rel.label !== rel.subtype && (
          <span style={{ fontSize:10, color:'var(--text2)' }}>{rel.label}</span>
        )}
        {(rel.year_start || rel.year_end) && (
          <span style={{ fontSize:9, color:'var(--text3)', fontFamily:'var(--mono)' }}>
            {rel.year_start}{rel.year_end?` — ${rel.year_end}`:''}
          </span>
        )}
        {/* Confidence badge */}
        {rel.notes && (
          <button onClick={()=>setExpanded(v=>!v)} style={{
            marginLeft:'auto', background:'none', border:'none', cursor:'pointer',
            color:'var(--text3)', fontSize:9, fontFamily:'var(--mono)', padding:0,
          }}>
            {expanded ? '▾ hide proof' : '▸ evidence'}
          </button>
        )}
      </div>

      {/* Evidence + source */}
      {expanded && rel.notes && (
        <div style={{
          marginTop:6, padding:'6px 8px', borderRadius:6,
          background:'rgba(99,179,237,0.04)', border:'0.5px solid rgba(99,179,237,0.1)',
        }}>
          <div style={{ fontSize:9, color:'var(--text2)', lineHeight:1.7, marginBottom:5, fontStyle:'italic' }}>
            "{rel.notes}"
          </div>
          {sources.map((s, i) => (
            <div key={i} style={{ marginTop:3 }}>
              <SourceLink name={s.name || 'Wikipedia'} url={s.url} />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}


// ── Main panel ─────────────────────────────────────────────────────────────────

export default function PersonPanel({ slug, onClose, onNavigate }) {
  const [person,   setPerson]   = useState(null);
  const [news,     setNews]     = useState([]);
  const [rels,     setRels]     = useState([]);
  const [loading,  setLoading]  = useState(true);
  const [tab,      setTab]      = useState('bio');
  const [enriching,setEnriching]= useState(false);
  const [newsFilter,setNewsFilter]=useState('all');

  useEffect(() => {
    if (!slug) return;
    setLoading(true); setPerson(null); setNews([]); setRels([]); setTab('bio');
    Promise.all([
      api.getPerson(slug).then(r => setPerson(r.person)).catch(()=>{}),
      api.getNews(slug).then(r => setNews(r.articles||[])).catch(()=>{}),
      api.getRelations(slug).then(r => setRels(r.relationships||[])).catch(()=>{}),
    ]).finally(() => setLoading(false));
  }, [slug]);

  const triggerEnrich = async () => {
    setEnriching(true);
    try {
      await api.enrichOne(slug);
      setTimeout(async () => {
        const r = await api.getPerson(slug).catch(()=>null);
        if (r) setPerson(r.person);
        setEnriching(false);
      }, 3000);
    } catch { setEnriching(false); }
  };

  if (!slug) return null;

  const pc     = partyColor(person?.party);
  const rc     = ROLE_COLORS[person?.role_type]||'var(--accent)';
  const initials = (person?.full_name||'?').split(' ').map(w=>w[0]).join('').slice(0,2).toUpperCase();

  const newsCategories = ['all',...new Set(news.map(n=>n.category||'other').filter(Boolean))];
  const filteredNews   = newsFilter==='all' ? news : news.filter(n=>(n.category||'other')===newsFilter);
  const avgAlign = news.length
    ? (news.reduce((s,n)=>s+(n.alignment_score||0),0)/news.length)
    : null;

  // Group relationships by type
  const relsByType = rels.reduce((acc, r) => {
    const t = r.rel_type || 'OTHER';
    if (!acc[t]) acc[t] = [];
    acc[t].push(r);
    return acc;
  }, {});

  const REL_ORDER = ['FAMILY_OF','MEMBER_OF','WORKS_AT','STUDIED_AT','OWNS','ALLIED_WITH','RIVAL_OF'];
  const orderedRelTypes = [
    ...REL_ORDER.filter(t => relsByType[t]),
    ...Object.keys(relsByType).filter(t => !REL_ORDER.includes(t))
  ];

  const TABS = [
    { id:'bio',       label:'Bio' },
    { id:'education', label:'Pendidikan' },
    { id:'career',    label:'Karier' },
    { id:'companies', label:'Perusahaan' },
    { id:'relations', label:`Relasi (${rels.length})` },
    { id:'news',      label:`Berita (${news.length})` },
    { id:'sources',   label:'Sumber' },
  ];

  return (
    <div style={{
      width:340, minWidth:320, background:'var(--panel)',
      borderLeft:'0.5px solid var(--border)',
      display:'flex', flexDirection:'column', overflow:'hidden',
    }}>
      {/* Header */}
      <div style={{
        background:`linear-gradient(135deg, ${pc}28 0%, transparent 70%)`,
        borderBottom:`1px solid ${pc}25`, padding:'14px 16px 10px',
        flexShrink:0,
      }}>
        <div style={{ display:'flex', gap:11, alignItems:'flex-start' }}>
          <div style={{
            width:50, height:50, borderRadius:'50%', flexShrink:0,
            background:`${pc}28`, border:`2px solid ${pc}55`,
            display:'flex', alignItems:'center', justifyContent:'center',
            fontSize:16, fontWeight:800, color:pc, fontFamily:'var(--mono)',
          }}>
            {loading ? '…' : initials}
          </div>
          <div style={{ flex:1, minWidth:0 }}>
            {loading
              ? <div style={{ height:14, width:150, background:'var(--panel2)', borderRadius:4, marginBottom:6 }}/>
              : <div style={{ fontSize:14, fontWeight:700, color:'var(--text)', lineHeight:1.3 }}>
                  {person?.full_name || slug}
                </div>
            }
            {person?.current_position && (
              <div style={{ fontSize:10, color:'var(--text2)', marginTop:3, lineHeight:1.5 }}>
                {person.current_position}
              </div>
            )}
            <div style={{ marginTop:5, display:'flex', gap:5, flexWrap:'wrap' }}>
              {person?.party     && <Tag label={person.party}      color={pc} />}
              {person?.role_type && <Tag label={ROLE_LABELS[person.role_type]||person.role_type} color={rc} />}
              {person?.province  && (
                <span style={{ fontSize:9, color:'var(--text3)', fontFamily:'var(--mono)',
                  padding:'1px 6px', background:'var(--panel2)', borderRadius:8 }}>
                  {person.province}
                </span>
              )}
            </div>
            {avgAlign!==null && person?.party && (
              <div style={{ marginTop:8 }}>
                <ScoreBar score={avgAlign} label={`${person.party} Alignment`} />
              </div>
            )}
          </div>
          <button onClick={onClose} style={{
            background:'none', border:'none', cursor:'pointer',
            color:'var(--text3)', fontSize:16, padding:2, flexShrink:0,
          }}>✕</button>
        </div>
      </div>

      {/* Tab bar */}
      <div style={{
        display:'flex', gap:0, borderBottom:'0.5px solid var(--border)',
        background:'var(--bg2)', flexShrink:0, overflowX:'auto',
      }}>
        {TABS.map(t => (
          <button key={t.id} onClick={()=>setTab(t.id)} style={{
            padding:'6px 10px', background:'none', border:'none', cursor:'pointer',
            fontSize:9, fontFamily:'var(--mono)', textTransform:'uppercase', letterSpacing:0.7,
            color:tab===t.id?'var(--accent2)':'var(--text3)',
            borderBottom:tab===t.id?'1.5px solid var(--accent)':'1.5px solid transparent',
            whiteSpace:'nowrap',
          }}>{t.label}</button>
        ))}
      </div>

      {/* Body */}
      <div style={{ flex:1, overflowY:'auto', padding:'12px 14px' }}>
        {loading && (
          <div style={{ display:'flex', gap:8, alignItems:'center', padding:'20px 0', color:'var(--text3)' }}>
            <div style={{ width:12, height:12, borderRadius:'50%', border:'2px solid rgba(99,179,237,.2)', borderTopColor:'var(--accent)', animation:'spin .7s linear infinite' }}/>
            <span style={{ fontSize:11, fontFamily:'var(--mono)' }}>Loading…</span>
          </div>
        )}

        {/* ── BIO ── */}
        {!loading && tab==='bio' && (
          <div className="fade-in">
            {person?.bio && (
              <Section title="Biografi">
                <p style={{ fontSize:12, color:'var(--text2)', lineHeight:1.75 }}>{person.bio}</p>
              </Section>
            )}
            <Section title="Data">
              {[
                ['Lahir', person?.born],
                ['Tempat Lahir', person?.birthplace],
                ['Agama', person?.religion],
                ['Dapil', person?.dapil],
                ['Fraksi', person?.faction],
              ].filter(([,v])=>v).map(([k,v])=>(
                <div key={k} style={{ display:'flex', gap:8, padding:'4px 0', borderBottom:'0.5px solid var(--border)' }}>
                  <span style={{ fontSize:10, color:'var(--text3)', fontFamily:'var(--mono)', width:80, flexShrink:0 }}>{k}</span>
                  <span style={{ fontSize:11, color:'var(--text2)' }}>{v}</span>
                </div>
              ))}
            </Section>
            <div style={{ display:'flex', gap:6, flexWrap:'wrap' }}>
              <button onClick={triggerEnrich} disabled={enriching} style={{
                padding:'5px 12px', borderRadius:8, fontSize:10, fontFamily:'var(--mono)',
                background:'rgba(99,179,237,0.1)', color:'var(--accent2)',
                border:'0.5px solid rgba(99,179,237,0.28)', cursor:'pointer',
                display:'flex', alignItems:'center', gap:5,
              }}>
                {enriching
                  ? <><span style={{ width:9, height:9, borderRadius:'50%', border:'1.5px solid rgba(99,179,237,.2)', borderTopColor:'var(--accent)', animation:'spin .7s linear infinite', display:'inline-block' }}/> Enriching…</>
                  : '⟳ Re-crawl Wiki'
                }
              </button>
              {person?.wiki_url_id && <SourceLink name="Wikipedia ID" url={person.wiki_url_id}/>}
              {person?.wiki_url_en && <SourceLink name="Wikipedia EN" url={person.wiki_url_en}/>}
            </div>
          </div>
        )}

        {/* ── EDUCATION ── */}
        {!loading && tab==='education' && (
          <div className="fade-in">
            {person?.education?.length > 0
              ? person.education.map((e,i) => (
                  <div key={i} style={{
                    padding:'9px 11px', borderRadius:8, background:'var(--panel2)',
                    border:'0.5px solid var(--border)', marginBottom:7,
                    borderLeft:'2px solid var(--green)',
                  }}>
                    <div style={{ fontSize:11, color:'var(--text)', fontWeight:500, lineHeight:1.5 }}>
                      {e.institution || e}
                    </div>
                    {(e.year || e.degree) && (
                      <div style={{ display:'flex', gap:8, marginTop:3 }}>
                        {e.degree && <span style={{ fontSize:10, color:'var(--text3)' }}>{e.degree}</span>}
                        {e.year   && <span style={{ fontSize:10, color:'var(--green)', fontFamily:'var(--mono)' }}>{e.year}</span>}
                      </div>
                    )}
                  </div>
                ))
              : <div style={{ color:'var(--text3)', fontSize:11, padding:'16px 0' }}>
                  Belum ada data. Klik Re-crawl Wiki.
                </div>
            }
          </div>
        )}

        {/* ── CAREER ── */}
        {!loading && tab==='career' && (
          <div className="fade-in">
            {person?.career?.length > 0
              ? (
                <div style={{ position:'relative' }}>
                  <div style={{ position:'absolute', left:18, top:8, bottom:0, width:1, background:'var(--border)' }}/>
                  {person.career.map((c,i) => (
                    <div key={i} style={{ display:'flex', gap:10, marginBottom:10, position:'relative' }}>
                      <div style={{ width:8, height:8, borderRadius:'50%', background:'var(--accent)', marginTop:5, flexShrink:0, marginLeft:15, zIndex:1 }}/>
                      <div style={{ padding:'7px 9px', borderRadius:8, background:'var(--panel2)', border:'0.5px solid var(--border)', flex:1 }}>
                        <div style={{ fontSize:11, color:'var(--text)', lineHeight:1.5 }}>{c.title || c}</div>
                        {c.org && <div style={{ fontSize:10, color:'var(--text2)', marginTop:2 }}>{c.org}</div>}
                        {(c.year_start||c.year_end) && (
                          <div style={{ fontSize:9, color:'var(--accent)', fontFamily:'var(--mono)', marginTop:2 }}>
                            {[c.year_start,c.year_end].filter(Boolean).join(' — ')}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )
              : <div style={{ color:'var(--text3)', fontSize:11, padding:'16px 0' }}>Belum ada data.</div>
            }
          </div>
        )}

        {/* ── COMPANIES ── */}
        {!loading && tab==='companies' && (
          <div className="fade-in">
            {person?.companies?.length > 0
              ? person.companies.map((c,i) => (
                  <div key={i} style={{
                    padding:'9px 11px', borderRadius:8, background:'var(--panel2)',
                    border:'0.5px solid var(--border)', marginBottom:7,
                    borderLeft:'2px solid var(--red)',
                  }}>
                    <div style={{ fontSize:11, color:'var(--text)', fontWeight:500 }}>{c.name||c}</div>
                    {(c.role||c.industry) && (
                      <div style={{ display:'flex', gap:8, marginTop:4 }}>
                        {c.role     && <Tag label={c.role}     color="var(--red)"/>}
                        {c.industry && <span style={{ fontSize:10, color:'var(--text3)' }}>{c.industry}</span>}
                      </div>
                    )}
                  </div>
                ))
              : <div style={{ color:'var(--text3)', fontSize:11, padding:'16px 0' }}>Tidak ada data perusahaan.</div>
            }
          </div>
        )}

        {/* ── RELATIONS ── */}
        {!loading && tab==='relations' && (
          <div className="fade-in">
            {rels.length === 0
              ? <div style={{ color:'var(--text3)', fontSize:11, padding:'16px 0' }}>
                  Belum ada relasi ditemukan. Graph mining akan mengisinya otomatis.
                </div>
              : orderedRelTypes.map(relType => (
                  <Section key={relType} title={relType.replace(/_/g,' ')}
                    count={relsByType[relType].length} defaultOpen={['FAMILY_OF','MEMBER_OF'].includes(relType)}>
                    {relsByType[relType].map((r,i) => (
                      <RelItem key={i} rel={r} selfName={person?.full_name} onNavigate={onNavigate} />
                    ))}
                  </Section>
                ))
            }
          </div>
        )}

        {/* ── NEWS ── */}
        {!loading && tab==='news' && (
          <div className="fade-in">
            <div style={{ display:'flex', gap:4, flexWrap:'wrap', marginBottom:10 }}>
              {newsCategories.map(cat => {
                const cc = NEWS_CAT_COLORS[cat]||'#718096';
                return (
                  <button key={cat} onClick={()=>setNewsFilter(cat)} style={{
                    padding:'2px 8px', borderRadius:20, fontSize:9, cursor:'pointer',
                    background:newsFilter===cat?`${cc}22`:'transparent',
                    color:newsFilter===cat?cc:'var(--text3)',
                    border:`0.5px solid ${newsFilter===cat?cc+'44':'var(--border)'}`,
                    fontFamily:'var(--mono)',
                  }}>{cat}</button>
                );
              })}
            </div>
            {filteredNews.map((a,i) => {
              const cc = NEWS_CAT_COLORS[a.category||'other']||'#718096';
              const score = a.alignment_score ?? null;
              return (
                <div key={i} style={{
                  padding:'9px 11px', borderRadius:8, background:'var(--panel2)',
                  border:'0.5px solid var(--border)', marginBottom:8,
                  borderLeft:`2.5px solid ${cc}`,
                }}>
                  <div style={{ display:'flex', gap:6, marginBottom:5, flexWrap:'wrap' }}>
                    <span style={{ fontSize:8, padding:'1px 6px', borderRadius:8, background:`${cc}22`, color:cc, fontFamily:'var(--mono)', textTransform:'uppercase' }}>
                      {a.category||'other'}
                    </span>
                    {a.sentiment && (
                      <span style={{ fontSize:8, color:'var(--text3)', fontFamily:'var(--mono)' }}>
                        {a.sentiment==='positive'?'😊':a.sentiment==='negative'?'😠':'😐'} {a.sentiment}
                      </span>
                    )}
                  </div>
                  <div style={{ fontSize:11, color:'var(--text)', fontWeight:500, lineHeight:1.5, marginBottom:5 }}>{a.title}</div>
                  {a.summary && (
                    <p style={{ fontSize:10, color:'var(--text3)', lineHeight:1.6, marginBottom:5 }}>
                      {(a.summary||'').slice(0,180)}{(a.summary||'').length>180?'…':''}
                    </p>
                  )}
                  <div style={{ display:'flex', gap:6, alignItems:'center', flexWrap:'wrap', marginBottom:score!==null?6:0 }}>
                    <SourceLink name={a.outlet||a.source_name||'Sumber'} url={a.url||a.source_url}/>
                    {a.published_at && <span style={{ fontSize:9, color:'var(--text3)', fontFamily:'var(--mono)' }}>{a.published_at}</span>}
                  </div>
                  {score!==null && <ScoreBar score={score} label="Faction Bias" />}
                </div>
              );
            })}
            {filteredNews.length===0 && (
              <div style={{ color:'var(--text3)', fontSize:11, padding:'16px 0' }}>Belum ada berita.</div>
            )}
          </div>
        )}

        {/* ── SOURCES ── */}
        {!loading && tab==='sources' && (
          <div className="fade-in">
            <Section title="Sumber Terverifikasi" defaultOpen>
              {(person?.sources||[]).map((s,i)=>(
                <div key={i} style={{ marginBottom:6 }}>
                  <SourceLink name={s.name} url={s.url}/>
                </div>
              ))}
              {person?.wiki_url_id && <div style={{ marginBottom:5 }}><SourceLink name="Wikipedia Indonesia" url={person.wiki_url_id}/></div>}
              {person?.wiki_url_en && <div style={{ marginBottom:5 }}><SourceLink name="Wikipedia English" url={person.wiki_url_en}/></div>}
            </Section>
            <div style={{ fontSize:9, color:'var(--text3)', fontFamily:'var(--mono)', lineHeight:1.9, marginTop:6 }}>
              Data bersumber dari catatan publik.<br/>
              Setiap relasi dilengkapi evidence dan source URL.<br/>
              Sumber: Wikipedia · dpr.go.id · setneg.go.id<br/>
              Berita: Tempo · Kompas · Detik · CNN Indonesia · Antara
            </div>
          </div>
        )}
      </div>

      {/* Footer */}
      {person && (
        <div style={{
          padding:'8px 12px', borderTop:'0.5px solid var(--border)',
          background:'var(--bg2)', flexShrink:0, display:'flex', gap:6,
        }}>
          <button onClick={()=>onNavigate&&onNavigate(person.slug||slug)} style={{
            flex:1, padding:'6px', borderRadius:8, fontSize:10, fontFamily:'var(--mono)',
            background:'rgba(99,179,237,0.12)', color:'var(--accent2)',
            border:'0.5px solid rgba(99,179,237,0.28)', cursor:'pointer',
          }}>🕸 Explore Network</button>
        </div>
      )}
    </div>
  );
}
