import { useState, useEffect } from 'react';
import { partyColor } from './lib.js';

const DYNASTY_TYPE_LABELS = {
  national_regional: 'Nasional + Regional',
  national:          'Nasional',
  regional_dominant: 'Regional Dominan',
  cross_party:       'Lintas Partai',
  regional:          'Regional',
  local:             'Lokal',
};

const LEVEL_ICONS = { nasional: '🏛', provinsi: '🏢', lokal: '🏠' };
const ROLE_LABELS = {
  presiden:'Presiden', wapres:'Wapres', menteri:'Menteri',
  gubernur:'Gubernur', bupati:'Bupati', walikota:'Walikota',
  dpr:'DPR RI', dprd:'DPRD',
};

function ScoreMeter({ score }) {
  const pct  = (score / 10) * 100;
  const color = score >= 7 ? '#fc8181' : score >= 4 ? '#f6ad55' : '#68d391';
  return (
    <div style={{ display:'flex', alignItems:'center', gap:8 }}>
      <div style={{ flex:1, height:5, borderRadius:3, background:'var(--border)', overflow:'hidden' }}>
        <div style={{ width:`${pct}%`, height:'100%', background:color, borderRadius:3, transition:'width .5s' }}/>
      </div>
      <span style={{ fontSize:11, fontWeight:700, color, fontFamily:'var(--mono)', width:28 }}>
        {score.toFixed(1)}
      </span>
    </div>
  );
}

function DynastyCard({ dynasty, onSelect, selected }) {
  const dominant = dynasty.dominant_party;
  const pc = dominant ? partyColor(dominant) : 'var(--accent)';

  return (
    <div onClick={() => onSelect(dynasty)}
      style={{
        padding:'12px 14px', borderRadius:10, cursor:'pointer',
        background: selected ? `${pc}12` : 'var(--panel2)',
        border:`0.5px solid ${selected ? pc+'55' : 'var(--border)'}`,
        marginBottom:8, transition:'all .15s',
      }}
      onMouseEnter={e=>{ if(!selected) e.currentTarget.style.background='var(--panel)'; }}
      onMouseLeave={e=>{ if(!selected) e.currentTarget.style.background='var(--panel2)'; }}
    >
      <div style={{ display:'flex', alignItems:'flex-start', gap:10, marginBottom:8 }}>
        {/* Avatar */}
        <div style={{
          width:36, height:36, borderRadius:'50%', flexShrink:0,
          background:`${pc}22`, border:`2px solid ${pc}55`,
          display:'flex', alignItems:'center', justifyContent:'center',
          fontSize:13, fontWeight:800, color:pc, fontFamily:'var(--mono)',
        }}>
          {dynasty.family_name.slice(0,2).toUpperCase()}
        </div>
        <div style={{ flex:1, minWidth:0 }}>
          <div style={{ fontSize:13, fontWeight:700, color:'var(--text)' }}>
            Keluarga {dynasty.family_name}
          </div>
          <div style={{ fontSize:10, color:'var(--text3)', fontFamily:'var(--mono)', marginTop:1 }}>
            {dynasty.head_person}
          </div>
        </div>
        <div style={{
          padding:'2px 8px', borderRadius:20, fontSize:9, fontFamily:'var(--mono)',
          background:'rgba(252,129,129,0.15)', color:'#fc8181',
          border:'0.5px solid rgba(252,129,129,0.3)', whiteSpace:'nowrap',
        }}>
          {DYNASTY_TYPE_LABELS[dynasty.dynasty_type] || dynasty.dynasty_type}
        </div>
      </div>

      <ScoreMeter score={dynasty.dynasty_score} />

      <div style={{ display:'flex', gap:8, marginTop:8, flexWrap:'wrap' }}>
        <span style={{ fontSize:10, color:'var(--text2)' }}>
          <span style={{ fontWeight:700, color:'var(--accent2)' }}>{dynasty.active_positions}</span> jabatan aktif
        </span>
        <span style={{ fontSize:10, color:'var(--text2)' }}>
          {dynasty.govt_levels.map(l => LEVEL_ICONS[l] || '●').join(' ')} {dynasty.govt_levels.join(', ')}
        </span>
      </div>

      <div style={{ display:'flex', gap:5, flexWrap:'wrap', marginTop:6 }}>
        {Object.entries(dynasty.parties || {}).map(([party, count]) => {
          const c = partyColor(party);
          return (
            <span key={party} style={{
              fontSize:9, padding:'1px 7px', borderRadius:20,
              background:`${c}22`, color:c, border:`0.5px solid ${c}44`,
              fontFamily:'var(--mono)',
            }}>{party} ×{count}</span>
          );
        })}
      </div>
    </div>
  );
}

function DynastyDetail({ dynasty, onNavigate }) {
  if (!dynasty) return null;
  return (
    <div className="fade-in">
      <div style={{ marginBottom:14 }}>
        <div style={{ fontSize:16, fontWeight:800, color:'var(--text)', marginBottom:4 }}>
          Dinasti {dynasty.family_name}
        </div>
        <div style={{ fontSize:11, color:'var(--text3)', fontFamily:'var(--mono)' }}>
          {dynasty.active_positions} jabatan pemerintahan ·{' '}
          {dynasty.regions.join(', ')}
        </div>
      </div>

      {/* Score breakdown */}
      <div style={{
        padding:'10px 12px', borderRadius:8, background:'var(--panel)',
        border:'0.5px solid var(--border)', marginBottom:14,
      }}>
        <div style={{ display:'flex', justifyContent:'space-between', marginBottom:6 }}>
          <span style={{ fontSize:10, color:'var(--text3)', fontFamily:'var(--mono)' }}>Dynasty Score</span>
          <span style={{ fontSize:10, fontFamily:'var(--mono)',
            color: dynasty.dynasty_score >= 7 ? '#fc8181' : dynasty.dynasty_score >= 4 ? '#f6ad55' : '#68d391' }}>
            {dynasty.dynasty_score}/10 · {DYNASTY_TYPE_LABELS[dynasty.dynasty_type]}
          </span>
        </div>
        <ScoreMeter score={dynasty.dynasty_score} />
      </div>

      {/* Members */}
      <div style={{ fontSize:10, color:'var(--text3)', fontFamily:'var(--mono)', letterSpacing:1, marginBottom:8 }}>
        ANGGOTA KELUARGA DI PEMERINTAHAN
      </div>
      {dynasty.members.map((m, i) => {
        const pc = partyColor(m.party);
        return (
          <div key={i} style={{
            display:'flex', gap:10, padding:'8px 10px', borderRadius:8,
            background:'var(--panel)', border:'0.5px solid var(--border)', marginBottom:6,
            borderLeft: m.is_head ? '3px solid #fc8181' : '2px solid var(--border)',
          }}>
            <div style={{ flex:1, minWidth:0 }}>
              <div style={{ display:'flex', alignItems:'center', gap:6, flexWrap:'wrap' }}>
                <span style={{ fontSize:12, fontWeight:600, color:'var(--text)' }}>{m.name}</span>
                {m.is_head && (
                  <span style={{ fontSize:8, padding:'1px 6px', borderRadius:8,
                    background:'rgba(252,129,129,0.2)', color:'#fc8181',
                    fontFamily:'var(--mono)' }}>HEAD</span>
                )}
              </div>
              <div style={{ fontSize:10, color:'var(--text2)', marginTop:2 }}>
                {ROLE_LABELS[m.role] || m.role}
                {m.region ? ` · ${m.region}` : ''}
              </div>
              {m.position && m.position !== m.role && (
                <div style={{ fontSize:9, color:'var(--text3)', marginTop:1 }}>{m.position}</div>
              )}
            </div>
            {m.party && (
              <span style={{
                alignSelf:'center', padding:'1px 8px', borderRadius:10, fontSize:9,
                background:`${pc}22`, color:pc, border:`0.5px solid ${pc}44`,
                fontFamily:'var(--mono)', whiteSpace:'nowrap',
              }}>{m.party}</span>
            )}
            {m.slug && (
              <button onClick={() => onNavigate && onNavigate(m.slug)} style={{
                alignSelf:'center', background:'none', border:'none', cursor:'pointer',
                color:'var(--text3)', fontSize:12, padding:2,
              }}>→</button>
            )}
          </div>
        );
      })}
    </div>
  );
}

export default function DynastyPanel({ onNavigate }) {
  const [dynasties, setDynasties] = useState([]);
  const [selected,  setSelected]  = useState(null);
  const [loading,   setLoading]   = useState(true);
  const [filter,    setFilter]    = useState('all');
  const [search,    setSearch]    = useState('');

  useEffect(() => {
    fetch('/api/dynasties?min_members=2')
      .then(r => r.json())
      .then(data => { setDynasties(data.dynasties || []); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  const types = ['all', ...new Set(dynasties.map(d => d.dynasty_type))];

  const filtered = dynasties.filter(d => {
    const matchFilter = filter === 'all' || d.dynasty_type === filter;
    const matchSearch = !search ||
      d.family_name.toLowerCase().includes(search.toLowerCase()) ||
      d.head_person?.toLowerCase().includes(search.toLowerCase());
    return matchFilter && matchSearch;
  });

  const TYPE_COLORS = {
    national_regional:'#fc8181', national:'#f6ad55',
    regional_dominant:'#b794f4', cross_party:'#63b3ed',
    regional:'#68d391', local:'#4fd1c5',
  };

  return (
    <div style={{ display:'flex', gap:0, height:'100%', overflow:'hidden' }}>
      {/* Left: dynasty list */}
      <div style={{
        width:360, flexShrink:0, borderRight:'0.5px solid var(--border)',
        display:'flex', flexDirection:'column', overflow:'hidden',
      }}>
        {/* Header */}
        <div style={{ padding:'12px 14px', borderBottom:'0.5px solid var(--border)', flexShrink:0 }}>
          <div style={{ fontSize:13, fontWeight:700, fontFamily:'var(--mono)', color:'var(--text)',
            letterSpacing:1, marginBottom:8 }}>
            🏛 DETEKSI DINASTI POLITIK
          </div>
          <input value={search} onChange={e=>setSearch(e.target.value)}
            placeholder="Cari nama keluarga…"
            style={{
              width:'100%', padding:'6px 10px', borderRadius:8, fontSize:11,
              background:'var(--panel2)', color:'var(--text)',
              border:'0.5px solid var(--border)', outline:'none',
              fontFamily:'var(--sans)', marginBottom:8,
            }}
          />
          <div style={{ display:'flex', gap:5, flexWrap:'wrap' }}>
            {types.map(t => {
              const c = TYPE_COLORS[t] || 'var(--text3)';
              return (
                <button key={t} onClick={() => setFilter(t)} style={{
                  padding:'2px 9px', borderRadius:20, fontSize:9, cursor:'pointer',
                  background:filter===t?`${c}22`:'transparent',
                  color:filter===t?c:'var(--text3)',
                  border:`0.5px solid ${filter===t?c+'44':'var(--border)'}`,
                  fontFamily:'var(--mono)',
                }}>{t === 'all' ? `Semua (${dynasties.length})` : DYNASTY_TYPE_LABELS[t] || t}</button>
              );
            })}
          </div>
        </div>

        {/* List */}
        <div style={{ flex:1, overflowY:'auto', padding:'10px 12px' }}>
          {loading && (
            <div style={{ color:'var(--text3)', fontSize:11, fontFamily:'var(--mono)', padding:20 }}>
              Mendeteksi pola dinasti…
            </div>
          )}
          {!loading && filtered.length === 0 && (
            <div style={{ color:'var(--text3)', fontSize:11, padding:20, lineHeight:1.8 }}>
              Tidak ada dinasti terdeteksi.<br/>
              Jalankan crawler untuk mengisi data.
            </div>
          )}
          {filtered.map((d, i) => (
            <DynastyCard key={i} dynasty={d}
              selected={selected === d}
              onSelect={setSelected}
            />
          ))}
        </div>
      </div>

      {/* Right: detail */}
      <div style={{ flex:1, overflowY:'auto', padding:'14px 18px' }}>
        {selected
          ? <DynastyDetail dynasty={selected} onNavigate={onNavigate} />
          : (
            <div style={{ display:'flex', flexDirection:'column', alignItems:'center',
              justifyContent:'center', height:'100%', color:'var(--text3)', textAlign:'center' }}>
              <div style={{ fontSize:40, marginBottom:12 }}>🏛</div>
              <div style={{ fontSize:13, lineHeight:1.9 }}>
                Pilih dinasti dari daftar kiri<br/>
                untuk melihat detail anggota keluarga<br/>
                dan jabatan pemerintahan mereka.
              </div>
            </div>
          )
        }
      </div>
    </div>
  );
}
