import { useEffect, useRef, useCallback, useState } from 'react';
import * as d3 from 'd3';
import { NODE_STYLE, EDGE_STYLE, partyColor } from './lib.js';

// ── Helpers ────────────────────────────────────────────────────────────────────

function nodeColor(n) {
  const style = NODE_STYLE[n._label] || NODE_STYLE.Person;
  return style.color(n);
}

function nodeRadius(n) {
  if (n._label === 'Person') {
    if (n.role_type === 'presiden' || n.role_type === 'wapres') return 34;
    if (n.role_type === 'menteri' || n.role_type === 'gubernur') return 28;
    return 22;
  }
  if (n._label === 'Org') return 16;
  return 10;
}

function edgeStyle(e) {
  const type = (e.type || 'default').toUpperCase().replace('-','_');
  return EDGE_STYLE[type] || EDGE_STYLE.default;
}

function shortLabel(text = '', maxLen = 14) {
  if (!text) return '';
  const words = text.split(' ');
  // If single word that's long, truncate
  if (words.length === 1) return text.length > maxLen ? text.slice(0, maxLen - 1) + '…' : text;
  // Multi-word: take initials or first 2 words
  if (text.length <= maxLen) return text;
  return words.slice(0, 2).join(' ').slice(0, maxLen);
}

// ── Component ─────────────────────────────────────────────────────────────────

export default function GraphCanvas({ data, centerSlug, onNodeClick, height }) {
  const svgRef = useRef(null);
  const simRef = useRef(null);
  const [tooltip, setTooltip] = useState(null);

  const draw = useCallback(() => {
    if (!svgRef.current || !data?.nodes?.length) return;

    const el = svgRef.current;
    const W = el.clientWidth || 1200;
    const H = height || el.clientHeight || 680;

    d3.select(el).selectAll('*').remove();

    // ── Deep copy so D3 mutation doesn't affect React state ──────────────────
    const nodes = data.nodes.map(n => ({ ...n }));
    const nodeMap = new Map(nodes.map(n => [n.id, n]));

    const links = (data.edges || [])
      .filter(e => nodeMap.has(e.source) && nodeMap.has(e.target))
      .map(e => ({ ...e }));

    const svg = d3.select(el)
      .attr('width', W).attr('height', H);

    // ── Defs ──────────────────────────────────────────────────────────────────
    const defs = svg.append('defs');

    // Radial gradient for background
    const bgGrad = defs.append('radialGradient').attr('id', 'bg-grad')
      .attr('cx','50%').attr('cy','50%').attr('r','70%');
    bgGrad.append('stop').attr('offset','0%').attr('stop-color','#0d1a2e').attr('stop-opacity',1);
    bgGrad.append('stop').attr('offset','100%').attr('stop-color','#060810').attr('stop-opacity',1);

    // Glow filter
    const glow = defs.append('filter').attr('id','glow').attr('x','-50%').attr('y','-50%').attr('width','200%').attr('height','200%');
    glow.append('feGaussianBlur').attr('stdDeviation','5').attr('result','blur');
    const fm = glow.append('feMerge');
    fm.append('feMergeNode').attr('in','blur');
    fm.append('feMergeNode').attr('in','SourceGraphic');

    // Strong glow for center
    const glowStrong = defs.append('filter').attr('id','glow-strong').attr('x','-80%').attr('y','-80%').attr('width','260%').attr('height','260%');
    glowStrong.append('feGaussianBlur').attr('stdDeviation','10').attr('result','blur');
    const fm2 = glowStrong.append('feMerge');
    fm2.append('feMergeNode').attr('in','blur');
    fm2.append('feMergeNode').attr('in','SourceGraphic');

    // Arrow markers per edge type
    const edgeTypes = [...new Set(links.map(e => (e.type||'default').toUpperCase().replace('-','_')))];
    edgeTypes.forEach(type => {
      const es = EDGE_STYLE[type] || EDGE_STYLE.default;
      defs.append('marker')
        .attr('id', `arr-${type}`)
        .attr('viewBox','0 0 8 8').attr('refX',18).attr('refY',4)
        .attr('markerWidth',5).attr('markerHeight',5)
        .attr('orient','auto-start-reverse')
        .append('path').attr('d','M1 1L7 4L1 7')
        .attr('fill','none').attr('stroke', es.color)
        .attr('stroke-width',1.6).attr('stroke-linecap','round');
    });

    // ── Background ────────────────────────────────────────────────────────────
    svg.append('rect').attr('width',W).attr('height',H)
      .attr('fill','url(#bg-grad)');

    // Dot grid
    const dotGrid = defs.append('pattern').attr('id','dots')
      .attr('width',32).attr('height',32).attr('patternUnits','userSpaceOnUse');
    dotGrid.append('circle').attr('cx',1).attr('cy',1).attr('r',0.8)
      .attr('fill','rgba(99,179,237,0.07)');
    svg.append('rect').attr('width',W).attr('height',H).attr('fill','url(#dots)');

    // ── Zoom container ────────────────────────────────────────────────────────
    const g = svg.append('g').attr('class','graph-root');

    svg.call(
      d3.zoom()
        .scaleExtent([0.1, 5])
        .on('zoom', e => g.attr('transform', e.transform))
    );

    // ── Links ─────────────────────────────────────────────────────────────────
    const linkG = g.append('g');
    const linkSel = linkG.selectAll('line')
      .data(links).join('line')
      .attr('stroke', d => edgeStyle(d).color)
      .attr('stroke-width', d => edgeStyle(d).width)
      .attr('stroke-dasharray', d => edgeStyle(d).dash)
      .attr('stroke-opacity', 0.55)
      .attr('marker-end', d => {
        const t = (d.type||'default').toUpperCase().replace('-','_');
        return `url(#arr-${t})`;
      });

    // Link labels
    const linkLabelSel = linkG.selectAll('text.link-label')
      .data(links.filter(l => l.label && l.label.length < 20)).join('text')
      .attr('class','link-label')
      .attr('text-anchor','middle')
      .attr('fill','rgba(140,160,190,0.5)')
      .attr('font-size',8)
      .attr('font-family','Space Mono, monospace')
      .attr('pointer-events','none')
      .text(d => d.label || '');

    // ── Nodes ─────────────────────────────────────────────────────────────────
    const nodeG = g.append('g');
    const nodeSel = nodeG.selectAll('g.node')
      .data(nodes).join('g')
      .attr('class','node')
      .attr('cursor','pointer')
      .on('click', (event, d) => {
        event.stopPropagation();
        onNodeClick && onNodeClick(d);
      })
      .on('mouseover', (event, d) => {
        const [mx, my] = d3.pointer(event, svg.node());
        setTooltip({ x: mx, y: my, node: d });
      })
      .on('mouseout', () => setTooltip(null))
      .call(
        d3.drag()
          .on('start', (e, d) => { if (!e.active) simRef.current?.alphaTarget(0.3).restart(); d.fx=d.x; d.fy=d.y; })
          .on('drag',  (e, d) => { d.fx=e.x; d.fy=e.y; })
          .on('end',   (e, d) => { if (!e.active) simRef.current?.alphaTarget(0); d.fx=null; d.fy=null; })
      );

    // Center node orbit ring
    nodeSel.filter(d => d.id === centerSlug || d.slug === centerSlug)
      .append('circle')
      .attr('r', d => nodeRadius(d) + 12)
      .attr('fill','none')
      .attr('stroke', d => nodeColor(d))
      .attr('stroke-width',1)
      .attr('stroke-opacity',0.25)
      .attr('stroke-dasharray','3 4');

    // Outer glow circle
    nodeSel.filter(d => d._label === 'Person')
      .append('circle')
      .attr('r', d => nodeRadius(d) + 4)
      .attr('fill', d => nodeColor(d))
      .attr('fill-opacity', 0.08)
      .attr('stroke','none');

    // Main circle
    nodeSel.append('circle')
      .attr('r', d => nodeRadius(d))
      .attr('fill', d => nodeColor(d))
      .attr('fill-opacity', d => d._label === 'News' ? 0.4 : 0.9)
      .attr('stroke', d => d.id === centerSlug || d.slug === centerSlug
        ? '#fff' : 'rgba(255,255,255,0.12)')
      .attr('stroke-width', d => d.id === centerSlug || d.slug === centerSlug ? 2 : 1)
      .attr('filter', d => d.id === centerSlug || d.slug === centerSlug ? 'url(#glow-strong)' : 'url(#glow)');

    // Type icon inside node
    const TYPE_ICON = { party:'★', university:'◎', company:'◈', govt:'▲', military:'✦', org:'●' };
    nodeSel.filter(d => d._label === 'Org')
      .append('text')
      .attr('text-anchor','middle').attr('dominant-baseline','central')
      .attr('fill','rgba(255,255,255,0.7)')
      .attr('font-size', d => nodeRadius(d) * 0.8)
      .attr('pointer-events','none')
      .text(d => TYPE_ICON[d.org_type || d.type || ''] || '●');

    // Initials for Person nodes
    nodeSel.filter(d => d._label === 'Person' || d._label !== 'Org')
      .append('text')
      .attr('text-anchor','middle').attr('dominant-baseline','central')
      .attr('fill','rgba(255,255,255,0.9)')
      .attr('font-size', d => nodeRadius(d) * 0.42)
      .attr('font-weight','700')
      .attr('font-family','Outfit, sans-serif')
      .attr('pointer-events','none')
      .text(d => {
        const name = d.name || d.label || d.full_name || '';
        return name.split(' ').map(w => w[0]).join('').toUpperCase().slice(0,2);
      });

    // Node name label below
    nodeSel.append('text')
      .attr('text-anchor','middle')
      .attr('y', d => nodeRadius(d) + 13)
      .attr('fill','rgba(200,215,240,0.8)')
      .attr('font-size', d => d._label === 'Person' ? 10 : 9)
      .attr('font-family','Outfit, sans-serif')
      .attr('pointer-events','none')
      .text(d => shortLabel(d.name || d.label || d.full_name || '', 15));

    // Party badge below name (for Persons with party)
    nodeSel.filter(d => d._label === 'Person' && d.party)
      .append('text')
      .attr('text-anchor','middle')
      .attr('y', d => nodeRadius(d) + 24)
      .attr('fill', d => nodeColor(d))
      .attr('fill-opacity', 0.7)
      .attr('font-size',8)
      .attr('font-family','Space Mono, monospace')
      .attr('pointer-events','none')
      .text(d => d.party || '');

    // ── Force simulation ──────────────────────────────────────────────────────
    const centerNode = nodes.find(n => n.id === centerSlug || n.slug === centerSlug);

    const sim = d3.forceSimulation(nodes)
      .force('link',      d3.forceLink(links).id(d => d.id).distance(d => {
        const t = (d.type||'').toUpperCase();
        if (t === 'FAMILY_OF')  return 110;
        if (t === 'MEMBER_OF')  return 140;
        if (t === 'STUDIED_AT') return 150;
        return 160;
      }).strength(0.5))
      .force('charge',    d3.forceManyBody().strength(d => d._label === 'News' ? -80 : -500))
      .force('center',    d3.forceCenter(W/2, H/2))
      .force('collision', d3.forceCollide(d => nodeRadius(d) + 28))
      .alphaDecay(0.025);

    if (centerNode) {
      sim.force('cx', d3.forceX(W/2).strength(d =>
        d.id === centerSlug || d.slug === centerSlug ? 0.8 : 0.02));
      sim.force('cy', d3.forceY(H/2).strength(d =>
        d.id === centerSlug || d.slug === centerSlug ? 0.8 : 0.02));
    }

    simRef.current = sim;

    sim.on('tick', () => {
      linkSel
        .attr('x1', d => d.source.x).attr('y1', d => d.source.y)
        .attr('x2', d => d.target.x).attr('y2', d => d.target.y);

      linkLabelSel
        .attr('x', d => (d.source.x + d.target.x) / 2)
        .attr('y', d => (d.source.y + d.target.y) / 2 - 4);

      nodeSel.attr('transform', d => `translate(${d.x},${d.y})`);
    });

    return () => sim.stop();
  }, [data, centerSlug, height, onNodeClick]);

  useEffect(() => {
    const cleanup = draw();
    return () => { cleanup?.(); simRef.current?.stop(); };
  }, [draw]);

  return (
    <div style={{ position:'relative', width:'100%', height: height||'100%' }}>
      <svg ref={svgRef} style={{ width:'100%', height:'100%', display:'block' }} />
      {tooltip && (
        <div style={{
          position:'absolute', left: tooltip.x + 14, top: tooltip.y - 10,
          background:'rgba(11,14,26,0.95)', border:'0.5px solid rgba(99,179,237,0.3)',
          borderRadius:8, padding:'8px 12px', pointerEvents:'none', zIndex:100,
          fontSize:11, fontFamily:'Space Mono, monospace', maxWidth:220,
          backdropFilter:'blur(8px)',
        }}>
          <div style={{ color:'#e8eaf0', fontWeight:700, marginBottom:3 }}>
            {tooltip.node.name || tooltip.node.label || tooltip.node.title || tooltip.node.id}
          </div>
          {tooltip.node._label && (
            <div style={{ color:'rgba(99,179,237,0.8)', fontSize:9 }}>
              {tooltip.node._label}{tooltip.node.role_type ? ` · ${tooltip.node.role_type}` : ''}
            </div>
          )}
          {tooltip.node.party && (
            <div style={{ color:'#f6ad55', fontSize:9, marginTop:2 }}>{tooltip.node.party}</div>
          )}
        </div>
      )}
    </div>
  );
}
