const BASE = import.meta.env.VITE_API_URL || '';

async function req(path, opts = {}) {
  const r = await fetch(BASE + path, {
    headers: { 'Content-Type': 'application/json' }, ...opts,
  });
  if (!r.ok) {
    const e = await r.json().catch(() => ({}));
    throw new Error(e.detail || `HTTP ${r.status}`);
  }
  return r.json();
}

export const api = {
  health:        ()             => req('/health'),
  stats:         ()             => req('/api/stats'),
  persons:       (p={})        => {
    // Strip undefined/null so they don't appear as ?role_type=undefined
    const params = Object.fromEntries(Object.entries(p).filter(([,v]) => v != null && v !== 'undefined'));
    return req('/api/persons?' + new URLSearchParams(params));
  },
  searchPersons: (q)           => req(`/api/persons/search?q=${encodeURIComponent(q)}`),
  getPerson:     (slug)        => req(`/api/persons/${slug}`),
  getNews:       (slug)        => req(`/api/persons/${slug}/news`),
  getRelations:  (slug)        => req(`/api/persons/${slug}/relations`),
  egoGraph:      (slug, d=2)   => req(`/api/graph/ego/${slug}?depth=${d}`),
  fullGraph:     (lim=500)     => req(`/api/graph/full?limit=${lim}`),
  pathBetween:   (a,b)         => req('/api/graph/path',{method:'POST',body:JSON.stringify({slug_a:a,slug_b:b})}),
  agentStart:    (limits)      => req('/api/agent/start',{method:'POST',body:JSON.stringify(limits)}),
  agentStop:     ()            => req('/api/agent/stop',{method:'POST'}),
  agentPause:    ()            => req('/api/agent/pause',{method:'POST'}),
  agentResume:   ()            => req('/api/agent/resume',{method:'POST'}),
  agentStatus:   ()            => req('/api/agent/status'),
  nlQuery:       (q,mode)      => req('/api/query',{method:'POST',body:JSON.stringify({question:q,mode})}),
  vectorSearch:  (q,n=5)       => req(`/api/query/vector-search?q=${encodeURIComponent(q)}&n=${n}`),
  jobs:          ()            => req('/api/jobs'),
};

const PC = {
  PDIP:'#e63946',Gerindra:'#4a90d9',Golkar:'#f6ad55',PKB:'#68d391',
  Demokrat:'#63b3ed',PKS:'#38a169',Nasdem:'#f97316',PAN:'#b794f4',
  PPP:'#48bb78',PSI:'#ed64a6',Hanura:'#a0aec0',Perindo:'#0ea5e9',
  Independen:'#718096',
};
export const partyColor = (p) => PC[p] || '#718096';

export const NODE_STYLE = {
  Person: { color: d => partyColor(d.party) || '#63b3ed', r: 22 },
  Org:    { color: d => {
    const t = d.org_type || d.type || '';
    if (t==='party')      return '#f6ad55';
    if (t==='university') return '#68d391';
    if (t==='company')    return '#fc8181';
    return '#4fd1c5';
  }, r: 16 },
  News:   { color: () => '#454e60', r: 8 },
};

export const EDGE_STYLE = {
  FAMILY_OF:    {color:'#b794f4',dash:null,  width:2.2},
  MEMBER_OF:    {color:'#f6ad55',dash:'6 3', width:1.5},
  WORKS_AT:     {color:'#4fd1c5',dash:null,  width:1.5},
  STUDIED_AT:   {color:'#68d391',dash:'4 4', width:1.2},
  OWNS:         {color:'#fc8181',dash:null,  width:1.5},
  ALLIED_WITH:  {color:'#63b3ed',dash:'8 4', width:1},
  RIVAL_OF:     {color:'#fc8181',dash:'3 3', width:1},
  MET_AT:       {color:'#90cdf4',dash:'2 2', width:1},
  APPOINTED_BY: {color:'#f6ad55',dash:'6 2', width:1},
  MENTIONED_IN: {color:'#2d3748',dash:'2 4', width:0.7},
  default:      {color:'#2d3748',dash:null,  width:0.7},
};

export const ROLE_LABELS = {
  presiden:'Presiden',wapres:'Wapres',menteri:'Menteri',
  dpr:'DPR RI',dprd:'DPRD',gubernur:'Gubernur',
  bupati:'Bupati',walikota:'Walikota',
};
export const ROLE_COLORS = {
  presiden:'#f6ad55',wapres:'#f6ad55',menteri:'#63b3ed',
  dpr:'#68d391',dprd:'#48bb78',gubernur:'#b794f4',
  bupati:'#fc8181',walikota:'#fc8181',
};
export const NEWS_CAT_COLORS = {
  corruption:'#fc8181',policy:'#68d391',election:'#63b3ed',
  family:'#b794f4',business:'#f6ad55',statement:'#4fd1c5',
  legal:'#fc8181',military:'#a0aec0',education:'#48bb78',other:'#454e60',
};
export const QUICK = [
  'Prabowo Subianto','Megawati Soekarnoputri','Joko Widodo',
  'Puan Maharani','Sri Mulyani','Gibran Rakabuming',
  'Anies Baswedan','Ridwan Kamil','Airlangga Hartarto',
];
