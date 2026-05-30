import { useState, useEffect } from 'react';
import { partyColor } from './lib.js';

const FACTION_POSITION_COLOR = {
  koalisi:      'var(--green)',
  oposisi:      'var(--red)',
  'tidak lolos':'var(--text3)',
  unknown:      'var(--text3)',
};

const FACTION_POSITION_LABEL = {
  koalisi:      'Koalisi Pemerintah',
  oposisi:      'Oposisi',
  'tidak lolos':'Tidak Lolos Parlemen',
};

function PartyRow({ party, seats, coalition, position, members, onClick }) {
  const pc = partyColor(party);
  const posColor = FACTION_POSITION_COLOR[position] || 'var(--text3)';
  const maxSeats = 580; // total DPR seats

  return (
    <div onClick={onClick} style={{
      padding:'10px 12px', borderRadius:8, background:'var(--panel2)',
      border:`0.5px solid ${pc}33`, marginBottom:6, cursor:'pointer',
      transition:'background .12s',
    }}
    onMouseEnter={e=>e.currentTarget.style.background='var(--panel)'}
    onMouseLeave={e=>e.currentTarget.style.background='var(--panel2)'}
    >
      <div style={{ display:'flex', alignItems:'center', gap:10 }}>
        <div style={{
          width:32, height:32, borderRadius:8, flexShrink:0,
          background:`${pc}22`, border:`1.5px solid ${pc}55`,
          display:'flex', alignItems:'center', justifyContent:'center',
          fontSize:10, fontWeight:800, color:pc, fontFamily:'var(--mono)',
        }}>
          {party.slice(0,4)}
        </div>
        <div style={{ flex:1, minWidth:0 }}>
          <div style={{ fontSize:12, fontWeight:600, color:'var(--text)' }}>{party}</div>
          <div style={{ fontSize:9, color:'var(--text3)', fontFamily:'var(--mono)', marginTop:1 }}>
            {coalition || 'Non-koalisi'}
          </div>
        </div>
        <div style={{ textAlign:'right' }}>
          <div style={{ fontSize:13, fontWeight:700, color:pc, fontFamily:'var(--mono)' }}>
            {seats}
          </div>
          <div style={{ fontSize:8, color:'var(--text3)', fontFamily:'var(--mono)' }}>kursi DPR</div>
        </div>
        <div style={{
          padding:'2px 8px', borderRadius:20, fontSize:9, fontFamily:'var(--mono)',
          background:`${posColor}15`, color:posColor,
          border:`0.5px solid ${posColor}40`, whiteSpace:'nowrap',
        }}>
          {FACTION_POSITION_LABEL[position] || position}
        </div>
      </div>

      {/* Seat bar */}
      {seats > 0 && (
        <div style={{ marginTop:8, height:4, borderRadius:2, background:'var(--border)', overflow:'hidden' }}>
          <div style={{
            height:'100%', borderRadius:2, background:pc,
            width:`${(seats/maxSeats)*100}%`, transition:'width .5s',
          }}/>
        </div>
      )}

      {members !== undefined && (
        <div style={{ fontSize:9, color:'var(--text3)', fontFamily:'var(--mono)', marginTop:4 }}>
          {members} pejabat teridentifikasi
        </div>
      )}
    </div>
  );
}

function CoalitionDetail({ coalition, members, seats }) {
  if (!coalition) return null;
  const totalSeats = seats || 0;
  const pct = Math.round((totalSeats / 580) * 100);
  const hasMajority = totalSeats >= 280;

  return (
    <div className="fade-in">
      {/* Header */}
      <div style={{
        padding:'14px 16px', borderRadius:10, background:'var(--panel)',
        border:'0.5px solid var(--border)', marginBottom:16,
      }}>
        <div style={{ fontSize:16, fontWeight:800, color:'var(--text)', marginBottom:4 }}>
          {coalition.name}
        </div>
        <div style={{ fontSize:11, color:'var(--text2)', marginBottom:10 }}>
          {coalition.election} · Pasangan: {coalition.president} – {coalition.vp}
        </div>

        {/* Vote share if available */}
        {coalition.vote_pct && (
          <div style={{ marginBottom:10 }}>
            <div style={{ display:'flex', justifyContent:'space-between', marginBottom:4 }}>
              <span style={{ fontSize:10, color:'var(--text3)', fontFamily:'var(--mono)' }}>Perolehan Suara</span>
              <span style={{ fontSize:11, fontWeight:700,
                color: coalition.won ? 'var(--green)' : 'var(--text2)',
                fontFamily:'var(--mono)' }}>
                {coalition.vote_pct}% {coalition.won ? '✓ MENANG' : '✗ KALAH'}
              </span>
            </div>
            <div style={{ height:6, borderRadius:3, background:'var(--border)', overflow:'hidden' }}>
              <div style={{ height:'100%', borderRadius:3,
                background: coalition.won ? 'var(--green)' : 'var(--text3)',
                width:`${coalition.vote_pct}%` }}/>
            </div>
          </div>
        )}

        {/* DPR seats */}
        <div>
          <div style={{ display:'flex', justifyContent:'space-between', marginBottom:4 }}>
            <span style={{ fontSize:10, color:'var(--text3)', fontFamily:'var(--mono)' }}>Kursi DPR</span>
            <span style={{ fontSize:11, fontWeight:700,
              color: hasMajority ? 'var(--green)' : 'var(--gold)',
              fontFamily:'var(--mono)' }}>
              {totalSeats}/580 ({pct}%) {hasMajority ? '— Mayoritas ✓' : ''}
            </span>
          </div>
          <div style={{ height:6, borderRadius:3, background:'var(--border)', overflow:'hidden', position:'relative' }}>
            <div style={{ height:'100%', borderRadius:3, background:'var(--accent)',
              width:`${pct}%` }}/>
            {/* Majority line */}
            <div style={{
              position:'absolute', top:0, bottom:0, left:'48.3%', width:1,
              background:'var(--red)', opacity:.7,
            }}/>
          </div>
        </div>

        {coalition.wiki_url && (
          <div style={{ marginTop:8 }}>
            <a href={coalition.wiki_url} target="_blank" rel="noopener noreferrer"
              style={{ fontSize:9, color:'var(--accent2)', fontFamily:'var(--mono)' }}>
              ↗ Wikipedia
            </a>
          </div>
        )}
      </div>

      {/* Party breakdown */}
      <div style={{ fontSize:10, color:'var(--text3)', fontFamily:'var(--mono)', letterSpacing:1, marginBottom:8 }}>
        PARTAI KOALISI ({coalition.core_parties?.length || 0} inti
        {coalition.supporting?.length ? ` + ${coalition.supporting.length} pendukung` : ''})
      </div>
      <div style={{ display:'flex', gap:5, flexWrap:'wrap', marginBottom:16 }}>
        {(coalition.core_parties || []).map(p => {
          const c = partyColor(p);
          return (
            <div key={p} style={{
              padding:'4px 10px', borderRadius:20,
              background:`${c}22`, border:`1px solid ${c}55`,
              fontSize:10, color:c, fontFamily:'var(--mono)', fontWeight:600,
            }}>{p}</div>
          );
        })}
        {(coalition.supporting || []).map(p => {
          const c = partyColor(p);
          return (
            <div key={p} style={{
              padding:'4px 10px', borderRadius:20,
              background:`${c}12`, border:`0.5px dashed ${c}44`,
              fontSize:10, color:`${c}99`, fontFamily:'var(--mono)',
            }}>{p} (pendukung)</div>
          );
        })}
        {(coalition.opposition || []).map(p => (
          <div key={p} style={{
            padding:'4px 10px', borderRadius:20,
            background:'rgba(252,129,129,0.1)', border:'0.5px dashed rgba(252,129,129,0.4)',
            fontSize:10, color:'#fc8181', fontFamily:'var(--mono)',
          }}>{p} (oposisi)</div>
        ))}
      </div>

      {/* Members by party */}
      {members && Object.keys(members).length > 0 && (
        <>
          <div style={{ fontSize:10, color:'var(--text3)', fontFamily:'var(--mono)', letterSpacing:1, marginBottom:8 }}>
            PEJABAT TERIDENTIFIKASI
          </div>
          {Object.entries(members).map(([party, persons]) => {
            if (!persons || persons.length === 0) return null;
            const c = partyColor(party);
            return (
              <div key={party} style={{ marginBottom:12 }}>
                <div style={{ display:'flex', alignItems:'center', gap:8, marginBottom:6 }}>
                  <div style={{ width:8, height:8, borderRadius:'50%', background:c }}/>
                  <span style={{ fontSize:10, color:c, fontFamily:'var(--mono)', fontWeight:600 }}>
                    {party} ({persons.length})
                  </span>
                </div>
                <div style={{ display:'flex', flexDirection:'column', gap:3, marginLeft:16 }}>
                  {persons.slice(0,8).map((p, i) => (
                    <div key={i} style={{ fontSize:10, color:'var(--text2)', display:'flex', gap:8 }}>
                      <span style={{ color:'var(--text3)', fontFamily:'var(--mono)', width:60 }}>
                        {p.role_type}
                      </span>
                      <span>{p.full_name}</span>
                      {p.province && <span style={{ color:'var(--text3)' }}>{p.province}</span>}
                    </div>
                  ))}
                  {persons.length > 8 && (
                    <span style={{ fontSize:9, color:'var(--text3)', fontFamily:'var(--mono)' }}>
                      +{persons.length-8} lainnya
                    </span>
                  )}
                </div>
              </div>
            );
          })}
        </>
      )}
    </div>
  );
}

export default function CoalitionPanel({ onNavigate }) {
  const [coalitions,  setCoalitions]  = useState([]);
  const [factionData, setFactionData] = useState(null);
  const [selected,    setSelected]    = useState(null);
  const [detail,      setDetail]      = useState(null);
  const [loading,     setLoading]     = useState(true);
  const [view,        setView]        = useState('coalitions'); // coalitions | factions

  useEffect(() => {
    fetch('/api/coalitions')
      .then(r => r.json())
      .then(data => {
        setCoalitions(data.coalitions || []);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  const selectCoalition = async (c) => {
    setSelected(c);
    setDetail(null);
    try {
      const r = await fetch(`/api/coalitions/${c.id}`);
      const data = await r.json();
      setDetail(data);
    } catch {}
  };

  const DPR_FACTIONS = [
    { party:'Golkar',   seats:102, coalition:'KIM', position:'koalisi' },
    { party:'PDIP',     seats:110, coalition:null,  position:'oposisi' },
    { party:'Nasdem',   seats:69,  coalition:'KIM', position:'koalisi' },
    { party:'PKB',      seats:68,  coalition:'KIM', position:'koalisi' },
    { party:'PKS',      seats:53,  coalition:null,  position:'oposisi' },
    { party:'Demokrat', seats:44,  coalition:'KIM', position:'koalisi' },
    { party:'PAN',      seats:48,  coalition:'KIM', position:'koalisi' },
    { party:'Gerindra', seats:86,  coalition:'KIM', position:'koalisi' },
    { party:'PSI',      seats:18,  coalition:'KIM', position:'koalisi' },
    { party:'PPP',      seats:0,   coalition:null,  position:'tidak lolos' },
    { party:'Hanura',   seats:0,   coalition:null,  position:'tidak lolos' },
  ].sort((a,b) => b.seats - a.seats);

  return (
    <div style={{ display:'flex', gap:0, height:'100%', overflow:'hidden' }}>
      {/* Left: list */}
      <div style={{
        width:380, flexShrink:0, borderRight:'0.5px solid var(--border)',
        display:'flex', flexDirection:'column', overflow:'hidden',
      }}>
        {/* Tab toggle */}
        <div style={{
          padding:'10px 12px', borderBottom:'0.5px solid var(--border)',
          flexShrink:0, display:'flex', gap:6,
        }}>
          {[
            { id:'coalitions', label:'🤝 Koalisi' },
            { id:'factions',   label:'🏛 Fraksi DPR' },
          ].map(t => (
            <button key={t.id} onClick={() => setView(t.id)} style={{
              padding:'5px 14px', borderRadius:8, fontSize:11, cursor:'pointer', fontFamily:'var(--mono)',
              background: view===t.id ? 'rgba(99,179,237,0.15)' : 'transparent',
              color:      view===t.id ? 'var(--accent2)' : 'var(--text3)',
              border:     `0.5px solid ${view===t.id ? 'rgba(99,179,237,0.35)' : 'var(--border)'}`,
            }}>{t.label}</button>
          ))}
        </div>

        <div style={{ flex:1, overflowY:'auto', padding:'10px 12px' }}>
          {view === 'coalitions' && (
            <>
              {loading && <div style={{ color:'var(--text3)', fontSize:11, fontFamily:'var(--mono)', padding:20 }}>Loading…</div>}
              {coalitions.map((c, i) => {
                const allParties = [...(c.core_parties||[]), ...(c.supporting||[])];
                const totalSeats = allParties.reduce((sum, p) => {
                  const f = DPR_FACTIONS.find(f=>f.party===p);
                  return sum + (f?.seats||0);
                }, 0);
                return (
                  <div key={i} onClick={() => selectCoalition(c)} style={{
                    padding:'12px 14px', borderRadius:10, cursor:'pointer',
                    background: selected?.id===c.id ? 'rgba(99,179,237,0.1)' : 'var(--panel2)',
                    border:`0.5px solid ${selected?.id===c.id ? 'rgba(99,179,237,0.4)' : 'var(--border)'}`,
                    marginBottom:8, transition:'all .15s',
                  }}>
                    <div style={{ display:'flex', alignItems:'flex-start', justifyContent:'space-between', marginBottom:6 }}>
                      <div>
                        <div style={{ fontSize:12, fontWeight:700, color:'var(--text)' }}>{c.name}</div>
                        <div style={{ fontSize:10, color:'var(--text3)', fontFamily:'var(--mono)', marginTop:1 }}>
                          {c.president} – {c.vp}
                        </div>
                      </div>
                      <span style={{
                        fontSize:10, fontWeight:700, fontFamily:'var(--mono)',
                        color: c.won ? 'var(--green)' : 'var(--red)',
                      }}>{c.vote_pct}%</span>
                    </div>
                    <div style={{ display:'flex', gap:4, flexWrap:'wrap' }}>
                      {(c.core_parties||[]).slice(0,6).map(p => {
                        const pc = partyColor(p);
                        return (
                          <span key={p} style={{ fontSize:8, padding:'1px 6px', borderRadius:20,
                            background:`${pc}22`, color:pc, fontFamily:'var(--mono)' }}>{p}</span>
                        );
                      })}
                      {(c.core_parties||[]).length > 6 && (
                        <span style={{ fontSize:8, color:'var(--text3)', fontFamily:'var(--mono)' }}>
                          +{c.core_parties.length-6}
                        </span>
                      )}
                    </div>
                    <div style={{ fontSize:9, color:'var(--text3)', fontFamily:'var(--mono)', marginTop:5 }}>
                      {totalSeats} kursi DPR · {c.total_parties} partai
                    </div>
                  </div>
                );
              })}
            </>
          )}

          {view === 'factions' && (
            DPR_FACTIONS.map((f, i) => (
              <PartyRow key={i}
                party={f.party} seats={f.seats}
                coalition={f.coalition}
                position={f.position}
                onClick={() => {}}
              />
            ))
          )}
        </div>
      </div>

      {/* Right: detail */}
      <div style={{ flex:1, overflowY:'auto', padding:'14px 18px' }}>
        {selected && detail ? (
          <CoalitionDetail
            coalition={selected}
            members={detail.members_by_party}
            seats={detail.dpr_seats_total}
          />
        ) : (
          <div style={{ display:'flex', flexDirection:'column', alignItems:'center',
            justifyContent:'center', height:'100%', color:'var(--text3)', textAlign:'center' }}>
            <div style={{ fontSize:40, marginBottom:12 }}>🤝</div>
            <div style={{ fontSize:13, lineHeight:1.9 }}>
              Pilih koalisi atau fraksi<br/>
              untuk melihat komposisi partai,<br/>
              kursi DPR, dan pejabat terkait.
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
