import { useState, useRef, useEffect } from 'react';
import { api } from './lib.js';

const EXAMPLE_QUERIES = [
  "Siapa istri Prabowo Subianto?",
  "Siapa saja anggota DPR dari Gerindra?",
  "Siapa yang bersekolah di tempat yang sama dengan Joko Widodo?",
  "Tampilkan semua berita korupsi tentang politisi dari PDIP",
  "Siapa sekutu politik Megawati?",
  "Perusahaan apa yang dimiliki oleh Airlangga Hartarto?",
  "Berapa anggota DPR dari Jawa Timur?",
  "Siapa yang pernah menjadi Menteri dan juga Gubernur?",
];

function ModeTab({ label, active, onClick, color }) {
  return (
    <button onClick={onClick} style={{
      padding:'5px 14px', borderRadius:20, fontSize:10, fontFamily:'var(--mono)',
      background: active ? `${color}22` : 'transparent',
      color: active ? color : 'var(--text3)',
      border:`0.5px solid ${active ? color+'55' : 'var(--border)'}`,
      cursor:'pointer', letterSpacing:.5,
    }}>{label}</button>
  );
}

function SourceTag({ url, outlet, score }) {
  const scoreColor = (score > 0.25) ? 'var(--green)' : (score < -0.25) ? 'var(--red)' : 'var(--gold)';
  const scoreLabel = (score > 0.25) ? '↑ Pro-partai' : (score < -0.25) ? '↓ Kritis' : '● Netral';
  return (
    <div style={{ display:'flex', gap:8, alignItems:'center', marginBottom:6 }}>
      <a href={url} target="_blank" rel="noopener noreferrer"
        style={{
          fontSize:9, fontFamily:'var(--mono)', color:'var(--accent2)',
          background:'rgba(99,179,237,0.1)', padding:'2px 8px',
          border:'0.5px solid rgba(99,179,237,0.25)', borderRadius:10,
          textDecoration:'none', whiteSpace:'nowrap',
        }}
      >↗ {outlet || 'Sumber'}</a>
      {score !== undefined && (
        <span style={{ fontSize:8, color:scoreColor, fontFamily:'var(--mono)' }}>
          {scoreLabel} ({score > 0 ? '+' : ''}{(score||0).toFixed(2)})
        </span>
      )}
    </div>
  );
}

export default function QueryPanel({ onClose, onNavigate }) {
  const [mode,     setMode]     = useState('auto');
  const [question, setQuestion] = useState('');
  const [result,   setResult]   = useState(null);
  const [loading,  setLoading]  = useState(false);
  const [history,  setHistory]  = useState([]);
  const inputRef = useRef(null);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const submit = async (q = question) => {
    if (!q.trim()) return;
    setLoading(true); setResult(null);
    try {
      const r = await api.nlQuery(q.trim(), mode);
      setResult(r);
      setHistory(h => [{q: q.trim(), mode, result: r}, ...h.slice(0,9)]);
    } catch(e) {
      setResult({ error: e.message });
    }
    setLoading(false);
  };

  const modeColor = { auto:'var(--accent)', rag:'var(--green)', cypher:'var(--purple)' };

  return (
    <div style={{
      position:'fixed', inset:0, background:'rgba(6,8,16,0.9)',
      backdropFilter:'blur(10px)', zIndex:300,
      display:'flex', alignItems:'center', justifyContent:'center',
    }}>
      <div style={{
        width:720, maxHeight:'90vh', background:'var(--panel)',
        border:'0.5px solid var(--border2)', borderRadius:16,
        display:'flex', flexDirection:'column', overflow:'hidden',
        boxShadow:'0 0 80px rgba(168,85,247,0.1)',
      }}>
        {/* Header */}
        <div style={{
          padding:'14px 20px', borderBottom:'0.5px solid var(--border)',
          display:'flex', alignItems:'center', gap:12,
        }}>
          <div style={{ flex:1 }}>
            <div style={{ fontSize:14, fontWeight:700, fontFamily:'var(--mono)', color:'var(--text)', letterSpacing:2 }}>
              🧠 KNOWLEDGE QUERY
            </div>
            <div style={{ fontSize:9, color:'var(--text3)', fontFamily:'var(--mono)', marginTop:2 }}>
              ChromaDB RAG + Ollama LLM + Neo4j Cypher · Tanya dalam Bahasa Indonesia
            </div>
          </div>
          <button onClick={onClose} style={{ background:'none', border:'none', cursor:'pointer', color:'var(--text3)', fontSize:18 }}>✕</button>
        </div>

        <div style={{ overflowY:'auto', padding:'16px 20px', flex:1 }}>
          {/* Mode selector */}
          <div style={{ display:'flex', gap:6, marginBottom:14 }}>
            <span style={{ fontSize:9, color:'var(--text3)', fontFamily:'var(--mono)', alignSelf:'center' }}>MODE:</span>
            {[
              { id:'auto',   label:'AUTO',   desc:'Cypher if specific, RAG if broad' },
              { id:'rag',    label:'RAG',     desc:'Semantic search + context' },
              { id:'cypher', label:'CYPHER',  desc:'Graph query (precise)' },
            ].map(m => (
              <ModeTab key={m.id} label={m.label} active={mode===m.id}
                onClick={() => setMode(m.id)} color={modeColor[m.id]} />
            ))}
            <span style={{ fontSize:9, color:'var(--text3)', fontFamily:'var(--mono)', alignSelf:'center', marginLeft:4 }}>
              {mode === 'auto'   ? '→ tries Cypher first, falls back to RAG'
               : mode === 'rag'  ? '→ semantic search over ChromaDB embeddings'
               : '→ translates to Neo4j Cypher query'}
            </span>
          </div>

          {/* Input */}
          <div style={{ display:'flex', gap:8, marginBottom:14 }}>
            <input
              ref={inputRef}
              value={question}
              onChange={e => setQuestion(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && !e.shiftKey && submit()}
              placeholder="Tanya tentang siapapun... Siapa istri Prabowo? Perusahaan apa yang dimiliki Erick Thohir?"
              style={{
                flex:1, padding:'10px 14px', borderRadius:10, fontSize:12,
                background:'var(--panel2)', color:'var(--text)',
                border:'0.5px solid var(--border)', outline:'none',
                fontFamily:'var(--sans)',
              }}
              disabled={loading}
            />
            <button onClick={() => submit()} disabled={loading || !question.trim()} style={{
              padding:'10px 20px', borderRadius:10, fontSize:12, fontFamily:'var(--mono)',
              background: loading ? 'rgba(168,85,247,0.1)' : 'rgba(168,85,247,0.2)',
              color:'var(--purple)', border:'0.5px solid rgba(168,85,247,0.35)',
              cursor: loading || !question.trim() ? 'not-allowed' : 'pointer',
              display:'flex', alignItems:'center', gap:8, fontWeight:700,
            }}>
              {loading
                ? <><div style={{ width:12, height:12, borderRadius:'50%', border:'2px solid rgba(168,85,247,.2)', borderTopColor:'var(--purple)', animation:'spin .7s linear infinite' }} /> Thinking…</>
                : '→ Ask'
              }
            </button>
          </div>

          {/* Example queries */}
          {!result && !loading && (
            <div style={{ marginBottom:14 }}>
              <div style={{ fontSize:9, color:'var(--text3)', fontFamily:'var(--mono)', marginBottom:8, letterSpacing:1 }}>
                CONTOH PERTANYAAN
              </div>
              <div style={{ display:'flex', gap:6, flexWrap:'wrap' }}>
                {EXAMPLE_QUERIES.map((q, i) => (
                  <button key={i} onClick={() => { setQuestion(q); submit(q); }} style={{
                    padding:'4px 10px', borderRadius:20, fontSize:10, cursor:'pointer',
                    background:'var(--panel2)', color:'var(--text2)',
                    border:'0.5px solid var(--border)', fontFamily:'var(--sans)',
                  }}>{q}</button>
                ))}
              </div>
            </div>
          )}

          {/* Result */}
          {result && !result.error && (
            <div className="fade-in">
              {/* Mode badge */}
              <div style={{ display:'flex', gap:8, alignItems:'center', marginBottom:12 }}>
                <span style={{
                  padding:'2px 10px', borderRadius:20, fontSize:9, fontFamily:'var(--mono)',
                  background: result.mode === 'cypher' ? 'rgba(168,85,247,0.2)' : 'rgba(104,211,145,0.2)',
                  color: result.mode === 'cypher' ? 'var(--purple)' : 'var(--green)',
                  border:`0.5px solid ${result.mode === 'cypher' ? 'rgba(168,85,247,0.4)' : 'rgba(104,211,145,0.4)'}`,
                }}>
                  {result.mode === 'cypher' ? '⬡ CYPHER' : '◎ RAG'}
                </span>
                {result.mode === 'cypher' && result.raw_results && (
                  <span style={{ fontSize:9, color:'var(--text3)', fontFamily:'var(--mono)' }}>
                    {result.raw_results.length} Neo4j records
                  </span>
                )}
              </div>

              {/* Cypher query shown */}
              {result.cypher && (
                <div style={{
                  padding:'10px 12px', borderRadius:8, background:'rgba(168,85,247,0.05)',
                  border:'0.5px solid rgba(168,85,247,0.2)', marginBottom:12,
                  fontFamily:'var(--mono)', fontSize:10, color:'rgba(183,148,244,0.8)',
                  overflowX:'auto', whiteSpace:'pre-wrap', lineHeight:1.6,
                }}>
                  {result.cypher}
                </div>
              )}

              {/* Answer */}
              <div style={{
                padding:'14px 16px', borderRadius:10, background:'var(--panel2)',
                border:'0.5px solid var(--border)', marginBottom:12,
                fontSize:13, color:'var(--text)', lineHeight:1.8,
              }}>
                {result.answer}
              </div>

              {/* Sources */}
              {result.sources?.persons?.length > 0 && (
                <div style={{ marginBottom:10 }}>
                  <div style={{ fontSize:9, color:'var(--text3)', fontFamily:'var(--mono)', marginBottom:6, letterSpacing:1 }}>
                    TOKOH TERKAIT
                  </div>
                  <div style={{ display:'flex', gap:6, flexWrap:'wrap' }}>
                    {result.sources.persons.map((p, i) => (
                      <button key={i}
                        onClick={() => onNavigate && onNavigate(p.slug)}
                        style={{
                          padding:'3px 10px', borderRadius:20, fontSize:10, cursor:'pointer',
                          background:'rgba(99,179,237,0.1)', color:'var(--accent2)',
                          border:'0.5px solid rgba(99,179,237,0.25)', fontFamily:'var(--sans)',
                        }}
                      >↗ {p.name}</button>
                    ))}
                  </div>
                </div>
              )}

              {result.sources?.news?.length > 0 && (
                <div>
                  <div style={{ fontSize:9, color:'var(--text3)', fontFamily:'var(--mono)', marginBottom:6, letterSpacing:1 }}>
                    SUMBER BERITA (dengan skor keberpihakan)
                  </div>
                  {result.sources.news.map((n, i) => (
                    <SourceTag key={i} url={n.url} outlet={n.outlet}
                      score={parseFloat(n.alignment_score) || 0} />
                  ))}
                </div>
              )}

              {/* Raw results table for Cypher */}
              {result.mode === 'cypher' && result.raw_results?.length > 0 && (
                <details style={{ marginTop:10 }}>
                  <summary style={{ fontSize:9, color:'var(--text3)', fontFamily:'var(--mono)', cursor:'pointer', letterSpacing:1 }}>
                    RAW NEO4J RECORDS
                  </summary>
                  <div style={{
                    marginTop:6, padding:'8px', borderRadius:8,
                    background:'var(--bg)', fontSize:9, fontFamily:'var(--mono)',
                    color:'var(--text3)', overflowX:'auto', maxHeight:200, overflowY:'auto',
                  }}>
                    <pre>{JSON.stringify(result.raw_results, null, 2)}</pre>
                  </div>
                </details>
              )}
            </div>
          )}

          {result?.error && (
            <div style={{
              padding:'10px 14px', borderRadius:8,
              background:'rgba(252,129,129,0.1)', border:'0.5px solid rgba(252,129,129,0.3)',
              fontSize:12, color:'var(--red)',
            }}>
              Error: {result.error}
            </div>
          )}

          {/* History */}
          {history.length > 0 && !result && (
            <div style={{ marginTop:16 }}>
              <div style={{ fontSize:9, color:'var(--text3)', fontFamily:'var(--mono)', letterSpacing:1, marginBottom:8 }}>
                HISTORY
              </div>
              {history.slice(0,5).map((h, i) => (
                <div key={i}
                  onClick={() => { setQuestion(h.q); setResult(h.result); }}
                  style={{
                    padding:'7px 12px', borderRadius:8, cursor:'pointer',
                    border:'0.5px solid var(--border)', marginBottom:5,
                    fontSize:11, color:'var(--text2)', fontFamily:'var(--sans)',
                    transition:'background .12s',
                  }}
                  onMouseEnter={e=>e.currentTarget.style.background='var(--panel2)'}
                  onMouseLeave={e=>e.currentTarget.style.background=''}
                >{h.q}</div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
