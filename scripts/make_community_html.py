# -*- coding: utf-8 -*-
import pickle, json

with open('/sessions/confident-loving-ritchie/mnt/outputs/community_data.pkl','rb') as f:
    data = pickle.load(f)

chris_coauth_count = data['chris_coauth_count']
pairwise_count     = data['pairwise_count']
author_pub_count   = data['author_pub_count']
partition          = data['partition']
community_themes   = data['community_themes']
layout_positions   = data['layout_positions']
n_communities      = data['n_communities']
OTHER_ID           = data['OTHER_ID']
CHRIS              = data['CHRIS']

# rename
community_themes = dict(community_themes)
for k,v in list(community_themes.items()):
    if 'Vegetation' in v or ('plant' in v.lower() and 'Plant ecology' not in v):
        community_themes[k] = 'Plant ecology'

# Wong (2011) colorblind-safe palette
COMM_COLOURS = ['#E69F00','#F0E442','#D55E00','#56B4E9','#009E73','#888888']
COMM_BORDERS = ['#a06800','#a09800','#903000','#2070a0','#006848','#555555']

MAX_CHRIS       = max(chris_coauth_count.values())
total_coauthors = len(chris_coauth_count)
total_pubs      = author_pub_count.get(CHRIS, 0)

coauth_list = sorted(chris_coauth_count.items(), key=lambda x: -x[1])
name_to_id  = {CHRIS: 0}
nodes_data  = [{'id':0,'label':'Chris Dickman','fullname':CHRIS,
                'chris_count':total_pubs,'pub_count':total_pubs,
                'is_chris':True,'community':-1,
                'x':layout_positions.get(CHRIS,(0,0))[0],
                'y':layout_positions.get(CHRIS,(0,0))[1]}]
for idx,(author,count) in enumerate(coauth_list,1):
    name_to_id[author]=idx
    comm=partition.get(author,OTHER_ID)
    x,y=layout_positions.get(author,(0,0))
    nodes_data.append({'id':idx,'label':author,'fullname':author,
                       'chris_count':count,'pub_count':author_pub_count.get(author,0),
                       'is_chris':False,'community':comm,'x':x,'y':y})

edges_data,eid=[],0
for author,count in chris_coauth_count.items():
    if author in name_to_id:
        edges_data.append({'id':eid,'from':0,'to':name_to_id[author],
                           'weight':count,'is_chris_edge':True}); eid+=1
for (a,b),count in pairwise_count.items():
    if a==CHRIS or b==CHRIS: continue
    if a in name_to_id and b in name_to_id and count>=2:
        edges_data.append({'id':eid,'from':name_to_id[a],'to':name_to_id[b],
                           'weight':count,'is_chris_edge':False}); eid+=1

legend_entries=[]
for c in range(n_communities):
    size=sum(1 for v in partition.values() if v==c)
    theme=community_themes.get(c,f'Group {c+1}')
    colour=COMM_COLOURS[c] if c<len(COMM_COLOURS) else '#aaa'
    legend_entries.append({'id':c,'colour':colour,'theme':theme,'size':size})

nodes_js  =json.dumps(nodes_data)
edges_js  =json.dumps(edges_data)
legend_js =json.dumps(legend_entries)
colours_js=json.dumps(COMM_COLOURS)
borders_js=json.dumps(COMM_BORDERS)

parts=[]

# ── CSS ───────────────────────────────────────────────────────────────────────
parts.append("""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Chris Dickman Co-authorship Network</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/vis/4.21.0/vis.min.js"></script>
<link href="https://cdnjs.cloudflare.com/ajax/libs/vis/4.21.0/vis.min.css" rel="stylesheet">
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Segoe UI',Arial,sans-serif;background:#1a1a2e;color:#eee;
     height:100vh;display:flex;flex-direction:column;overflow:hidden}
#header{padding:9px 14px;background:#16213e;border-bottom:1px solid #0f3460;
        display:flex;align-items:center;gap:14px;flex-wrap:wrap;flex-shrink:0}
#header h1{font-size:0.95rem;color:#e0c060;font-weight:700;white-space:nowrap}
#header .subtitle{font-size:0.72rem;color:#aaa}
.controls{display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin-left:auto}
.ctrl-group{display:flex;align-items:center;gap:6px}
.ctrl-group label{font-size:0.75rem;color:#bbb;white-space:nowrap}
input[type=range]{width:90px;accent-color:#e0c060;cursor:pointer}
.val-badge{font-size:0.8rem;font-weight:bold;color:#e0c060;min-width:28px;text-align:left}
#coauthor-edges-toggle{accent-color:#009E73;width:14px;height:14px;cursor:pointer}
.hdr-btn{padding:4px 10px;background:#1a3050;border:1px solid #2a5080;border-radius:4px;
         color:#99bbdd;font-size:0.73rem;cursor:pointer;white-space:nowrap;transition:all .15s}
.hdr-btn:hover{background:#203860;border-color:#4080b0}
.hdr-btn.active{background:#0f3060;border-color:#56B4E9;color:#56B4E9}
#body{display:flex;flex:1;overflow:hidden}
#legend{width:215px;flex-shrink:0;background:#0e1a30;border-right:1px solid #0f3460;
        padding:11px 9px;overflow-y:auto}
#legend h2{font-size:0.7rem;color:#888;text-transform:uppercase;
           letter-spacing:.08em;margin-bottom:9px}
.leg-item{display:flex;align-items:flex-start;gap:8px;margin-bottom:8px;cursor:pointer;
          padding:5px 6px;border-radius:5px;transition:background .12s;
          border:1px solid transparent}
.leg-item:hover{background:rgba(255,255,255,.05)}
.leg-item.active{border-color:rgba(255,255,255,.28);background:rgba(255,255,255,.08)}
.leg-swatch{width:12px;height:12px;border-radius:50%;flex-shrink:0;margin-top:2px}
.leg-label{color:#ddd;font-weight:600;font-size:0.74rem;line-height:1.3}
.leg-size{color:#777;font-size:0.67rem}
.leg-sep{border-top:1px solid #1a2a40;margin:7px 0}
#chris-leg{display:flex;align-items:center;gap:8px;margin-bottom:7px;padding:5px 6px}
.chris-sw{width:14px;height:14px;border-radius:50%;background:#fff;
          border:2px solid #e0c060;flex-shrink:0}
#show-all-btn{display:none;width:100%;margin-top:8px;padding:5px 0;
              background:#1a3050;border:1px solid #2a5080;border-radius:4px;
              color:#99bbdd;font-size:0.72rem;cursor:pointer}
#show-all-btn:hover{background:#203860}
#filter-note{font-size:0.64rem;color:#4a5a6a;margin-top:8px;line-height:1.4}
#network{flex:1;cursor:default}
#network.drag-mode{cursor:grab}
#network.dragging{cursor:grabbing}
#statusbar{padding:3px 14px;background:#16213e;font-size:0.7rem;color:#666;
           display:flex;gap:16px;align-items:center;flex-shrink:0;
           border-top:1px solid #0f3460}
#settling{color:#e0c060;display:none}
@keyframes pulse{from{opacity:.5}to{opacity:1}}
#settling{animation:pulse 1s infinite alternate}
#tooltip{position:fixed;display:none;background:rgba(14,26,48,0.97);
         border:1px solid #1a3050;border-radius:7px;padding:9px 12px;
         font-size:0.77rem;pointer-events:none;z-index:999;max-width:265px;
         box-shadow:0 4px 18px rgba(0,0,0,.6)}
.tt-name{font-weight:700;color:#e0c060;margin-bottom:4px;font-size:0.85rem}
.tt-row{color:#bbb;margin:2px 0}
.tt-row span{font-weight:600;color:#ddd}
.tt-comm{margin-top:5px;font-size:0.71rem;padding:2px 7px;border-radius:3px;
         display:inline-block;color:#111;font-weight:700}
</style>
</head>
<body>""")

# ── HEADER ────────────────────────────────────────────────────────────────────
parts.append(f"""
<div id="header">
  <div>
    <h1>Chris Dickman &#8212; Co-authorship Network</h1>
    <div class="subtitle">{total_pubs} publications &middot; {total_coauthors} co-authors &middot; coloured by research theme</div>
  </div>
  <div class="controls">
    <div class="ctrl-group">
      <label>Min papers:</label>
      <input type="range" id="threshold" min="1" max="30" value="3" step="1">
      <span class="val-badge" id="threshold-val">3</span>
    </div>
    <div class="ctrl-group">
      <label>Theme spacing:</label>
      <input type="range" id="spacing" min="1" max="4" value="1" step="0.05">
      <span class="val-badge" id="spacing-val">1.0x</span>
    </div>
    <div class="ctrl-group">
      <label>Co-author links:</label>
      <input type="checkbox" id="coauthor-edges-toggle" checked>
    </div>
    <button class="hdr-btn" id="drag-mode-btn" onclick="toggleDragMode()">&#8633; Move themes</button>
  </div>
</div>""")

# ── SIDEBAR + CANVAS ──────────────────────────────────────────────────────────
parts.append(f"""
<div id="body">
  <div id="legend">
    <h2>Research themes</h2>
    <div id="chris-leg">
      <div class="chris-sw"></div>
      <div>
        <div class="leg-label">Chris Dickman</div>
        <div class="leg-size">{total_pubs} publications</div>
      </div>
    </div>
    <div class="leg-sep"></div>
    <div id="legend-items"></div>
    <button id="show-all-btn" onclick="clearHighlight()">&#8635; Show all themes</button>
    <div id="filter-note">Click a theme to isolate it</div>
  </div>
  <div id="network"></div>
</div>
<div id="statusbar">
  <span><b>Showing:</b> <span id="stat-nodes">-</span> authors &nbsp;&middot;&nbsp; <span id="stat-edges">-</span> edges</span>
  <span id="settling">&#8635; Settling&hellip;</span>
</div>
<div id="tooltip"></div>""")

# ── JAVASCRIPT ────────────────────────────────────────────────────────────────
parts.append("<script>")
parts.append(f"const ALL_NODES    = {nodes_js};")
parts.append(f"const ALL_EDGES    = {edges_js};")
parts.append(f"const LEGEND       = {legend_js};")
parts.append(f"const COMM_COLOURS = {colours_js};")
parts.append(f"const COMM_BORDERS = {borders_js};")
parts.append(f"const MAX_CHRIS    = {MAX_CHRIS};")

parts.append("""
// ── lookup ──────────────────────────────────────────────────────────────────
var nodeMap = {};
ALL_NODES.forEach(function(n){ nodeMap[n.id] = n; });

// ── state ────────────────────────────────────────────────────────────────────
var network = null, nodesDS = null, edgesDS = null;
var highlightComm  = null;   // null = all visible
var spreadFactor   = 1.0;
var commDragDelta  = {};     // {commId: {dx,dy}}  persistent drag offsets
var isDragMode     = false;
var commCentroids  = {};     // {commId: {x,y}}  set after initial stabilise
var globalCenter   = {x:0, y:0};

// drag tracking
var dragNodeId = null, dragCommId = null, dragStartCanvasPos = null, dragBaseOffset = null;

// ── colour helpers ────────────────────────────────────────────────────────────
function cColour(c){ return (c>=0&&c<COMM_COLOURS.length)?COMM_COLOURS[c]:'#aaa'; }
function cBorder(c){ return (c>=0&&c<COMM_BORDERS.length)?COMM_BORDERS[c]:'#666'; }
function nodeSize(n){
  if(n.is_chris) return 54;
  return Math.max(10,Math.min(50,10+Math.sqrt(n.chris_count/MAX_CHRIS)*40));
}
function edgeWidth(w,isC){
  return isC?Math.max(1,Math.min(18,1+w*0.28)):Math.max(0.5,Math.min(4,0.5+w*0.5));
}

// ── centroid computation ──────────────────────────────────────────────────────
function recomputeCentroids(){
  var sums={}, counts={};
  ALL_NODES.forEach(function(n){
    if(n.is_chris) return;
    var c=n.community;
    if(!sums[c]){sums[c]={x:0,y:0};counts[c]=0;}
    sums[c].x+=n.x; sums[c].y+=n.y; counts[c]++;
  });
  commCentroids={};
  for(var c in sums){
    commCentroids[c]={x:sums[c].x/counts[c], y:sums[c].y/counts[c]};
  }
  var gx=0,gy=0,gc=0;
  for(var c in commCentroids){gx+=commCentroids[c].x;gy+=commCentroids[c].y;gc++;}
  globalCenter=(gc>0)?{x:gx/gc,y:gy/gc}:{x:0,y:0};
}

// ── position formula ──────────────────────────────────────────────────────────
// Applies spread (scales community centroids away from global centre)
// plus per-community drag offsets.
function getCanvasPos(n){
  if(!n) return {x:0,y:0};
  var c  = n.community;
  var dd = commDragDelta[c]||{dx:0,dy:0};
  if(n.is_chris){
    return {x: n.x+dd.dx, y: n.y+dd.dy};
  }
  var cent = commCentroids[c]||{x:n.x,y:n.y};
  var gcx  = globalCenter.x, gcy=globalCenter.y;
  var sx   = gcx+(cent.x-gcx)*spreadFactor;
  var sy   = gcy+(cent.y-gcy)*spreadFactor;
  return {
    x: sx+(n.x-cent.x)+dd.dx,
    y: sy+(n.y-cent.y)+dd.dy,
  };
}

// Push computed positions into the DataSet (no physics required).
// excludeId: skip this node (used while it is being dragged by vis.js)
function applyPositions(excludeId){
  var updates=[];
  nodesDS.get().forEach(function(node){
    if(excludeId!==undefined && node.id===excludeId) return;
    var orig=nodeMap[node.id]; if(!orig) return;
    var p=getCanvasPos(orig);
    updates.push({id:node.id, x:p.x, y:p.y});
  });
  if(updates.length) nodesDS.update(updates);
}

// ── build vis arrays ──────────────────────────────────────────────────────────
function buildGraph(threshold, showCoauth, commFilter){
  var visibleIds=new Set([0]);
  ALL_NODES.forEach(function(n){
    if(n.is_chris) return;
    if(n.chris_count<threshold) return;
    if(commFilter!==null&&commFilter!==undefined&&n.community!==commFilter) return;
    visibleIds.add(n.id);
  });

  var visNodes=ALL_NODES.filter(function(n){return visibleIds.has(n.id);})
    .map(function(n){
      var p=getCanvasPos(n);
      return {
        id:n.id,
        label:n.is_chris?'Chris\\nDickman':n.label.replace(', ','\\n'),
        x:p.x, y:p.y,
        size:nodeSize(n),
        color:{
          background:n.is_chris?'#ffffff':cColour(n.community),
          border:    n.is_chris?'#e0c060':cBorder(n.community),
          highlight:{background:n.is_chris?'#ffffff':cColour(n.community),border:'#fff'},
        },
        opacity:1,
        font:{
          color:n.is_chris?'#1a1a2e':'#fff',
          size:n.is_chris?13:Math.max(9,Math.min(12,8+n.chris_count*0.08)),
          bold:n.is_chris,
        },
        shape:'dot', borderWidth:n.is_chris?3:1.5,
      };
    });

  var visEdges=ALL_EDGES
    .filter(function(e){
      return visibleIds.has(e.from)&&visibleIds.has(e.to)&&(e.is_chris_edge||showCoauth);
    })
    .map(function(e){
      return {
        id:e.id,from:e.from,to:e.to,
        width:edgeWidth(e.weight,e.is_chris_edge),
        color:e.is_chris_edge
          ?{color:'#e0c060',opacity:0.55,highlight:'#fff0a0'}
          :{color:'#2a4a6a',opacity:0.40,highlight:'#57cc99'},
        smooth:{type:'curvedCW',roundness:0.35},
        hoverWidth:e.is_chris_edge?3:1.5,
        _w:e.weight, _ce:e.is_chris_edge,
      };
    });

  document.getElementById('stat-nodes').textContent=visNodes.length;
  document.getElementById('stat-edges').textContent=visEdges.length;
  return {visNodes:visNodes,visEdges:visEdges};
}

// ── init ──────────────────────────────────────────────────────────────────────
function init(){
  var threshold =parseInt(document.getElementById('threshold').value);
  var showCoauth=document.getElementById('coauthor-edges-toggle').checked;
  var g=buildGraph(threshold,showCoauth,null);

  nodesDS=new vis.DataSet(g.visNodes);
  edgesDS=new vis.DataSet(g.visEdges);

  var opts={
    nodes:{scaling:{min:8,max:55}},
    edges:{smooth:{type:'curvedCW',roundness:0.35},arrows:{to:false}},
    physics:{
      enabled:true,
      stabilization:{enabled:true,iterations:400,updateInterval:20,fit:true},
      barnesHut:{gravitationalConstant:-5000,centralGravity:0.1,
                 springLength:150,springConstant:0.02,damping:0.1},
    },
    interaction:{hover:true,tooltipDelay:80,hideEdgesOnDrag:true,multiselect:false},
  };
  network=new vis.Network(document.getElementById('network'),
                          {nodes:nodesDS,edges:edgesDS},opts);

  document.getElementById('settling').style.display='inline';
  network.once('stabilizationIterationsDone',function(){
    network.setOptions({physics:{enabled:false}});
    document.getElementById('settling').style.display='none';
    // Record stabilised positions as the canonical baseline
    var pos=network.getPositions();
    ALL_NODES.forEach(function(n){ if(pos[n.id]){n.x=pos[n.id].x;n.y=pos[n.id].y;} });
    recomputeCentroids();
  });

  // ── tooltips ──────────────────────────────────────────────────────────────
  var tooltip=document.getElementById('tooltip');
  network.on('hoverNode',function(params){
    var n=nodeMap[params.node]; if(!n) return;
    var c=n.community,theme=(c>=0&&c<LEGEND.length)?LEGEND[c].theme:'';
    var col=c>=0?cColour(c):'#aaa';
    var h='<div class="tt-name">'+n.label+'</div>';
    if(n.is_chris){
      h+='<div class="tt-row">Publications (with co-authors): <span>'+n.pub_count+'</span></div>';
    } else {
      h+='<div class="tt-row">Co-authored with Chris: <span>'+n.chris_count+' papers</span></div>';
      h+='<div class="tt-row">Total publications listed: <span>'+n.pub_count+'</span></div>';
      if(theme) h+='<div class="tt-comm" style="background:'+col+'">'+theme+'</div>';
    }
    tooltip.innerHTML=h; tooltip.style.display='block';
  });
  network.on('hoverEdge',function(params){
    var e=edgesDS.get(params.edge); if(!e) return;
    var fn=nodeMap[e.from],tn=nodeMap[e.to]; if(!fn||!tn) return;
    var l1=fn.is_chris?'Chris Dickman':fn.label;
    var l2=tn.is_chris?'Chris Dickman':tn.label;
    tooltip.innerHTML='<div class="tt-name">'+l1+' &#8596; '+l2+'</div>'
      +'<div class="tt-row">Co-authored: <span>'+e._w+' paper'+(e._w>1?'s':'')+'</span></div>';
    tooltip.style.display='block';
  });
  network.on('blurNode',function(){tooltip.style.display='none';});
  network.on('blurEdge',function(){tooltip.style.display='none';});
  document.addEventListener('mousemove',function(ev){
    if(tooltip.style.display==='block'){
      tooltip.style.left=(ev.clientX+15)+'px';
      tooltip.style.top =(ev.clientY-10)+'px';
    }
  });

  // ── theme drag ────────────────────────────────────────────────────────────
  network.on('dragStart',function(params){
    if(!isDragMode||!params.nodes.length) return;
    dragNodeId=params.nodes[0];
    var n=nodeMap[dragNodeId];
    if(!n||n.is_chris){dragNodeId=null;return;}
    dragCommId=n.community;
    dragStartCanvasPos=network.getPositions([dragNodeId])[dragNodeId];
    dragBaseOffset={dx:(commDragDelta[dragCommId]||{dx:0}).dx,
                    dy:(commDragDelta[dragCommId]||{dy:0}).dy};
    document.getElementById('network').classList.add('dragging');
  });

  network.on('dragging',function(params){
    if(!isDragMode||!dragNodeId||!params.nodes.length||
       params.nodes[0]!==dragNodeId) return;
    var cur=network.getPositions([dragNodeId])[dragNodeId];
    if(!cur||!dragStartCanvasPos) return;
    commDragDelta[dragCommId]={
      dx:dragBaseOffset.dx+(cur.x-dragStartCanvasPos.x),
      dy:dragBaseOffset.dy+(cur.y-dragStartCanvasPos.y),
    };
    // Move all other community nodes (dragged node handled by vis.js)
    applyPositions(dragNodeId);
  });

  network.on('dragEnd',function(params){
    document.getElementById('network').classList.remove('dragging');
    if(!isDragMode){
      // Individual node drag: back-transform dropped canvas position into canonical space
      // so the spacing slider and theme drag continue to work correctly.
      if(params.nodes&&params.nodes.length){
        var nid=params.nodes[0];
        var orig=nodeMap[nid];
        if(orig){
          var pos=network.getPositions([nid])[nid];
          if(pos){
            if(orig.is_chris){
              // Chris: canonical pos is stored directly
              var dd0=commDragDelta[orig.community]||{dx:0,dy:0};
              orig.x=pos.x-dd0.dx; orig.y=pos.y-dd0.dy;
            } else {
              var c=orig.community;
              var dd=commDragDelta[c]||{dx:0,dy:0};
              var cent=commCentroids[c]||{x:orig.x,y:orig.y};
              var sx=globalCenter.x+(cent.x-globalCenter.x)*spreadFactor;
              var sy=globalCenter.y+(cent.y-globalCenter.y)*spreadFactor;
              orig.x=pos.x-sx+cent.x-dd.dx;
              orig.y=pos.y-sy+cent.y-dd.dy;
            }
            recomputeCentroids();
          }
        }
      }
      return;
    }
    if(!dragNodeId) return;
    // Snap dragged node to its exact formula position too
    var cur=network.getPositions([dragNodeId])[dragNodeId];
    if(cur&&dragStartCanvasPos){
      commDragDelta[dragCommId]={
        dx:dragBaseOffset.dx+(cur.x-dragStartCanvasPos.x),
        dy:dragBaseOffset.dy+(cur.y-dragStartCanvasPos.y),
      };
    }
    applyPositions();
    dragNodeId=null;dragCommId=null;dragStartCanvasPos=null;dragBaseOffset=null;
  });
}

// ── controls ──────────────────────────────────────────────────────────────────
function update(){
  var threshold =parseInt(document.getElementById('threshold').value);
  var showCoauth=document.getElementById('coauthor-edges-toggle').checked;
  document.getElementById('threshold-val').textContent=threshold;
  var g=buildGraph(threshold,showCoauth,highlightComm);
  network.setOptions({physics:{enabled:false}});
  nodesDS.clear(); nodesDS.add(g.visNodes);
  edgesDS.clear(); edgesDS.add(g.visEdges);
  if(highlightComm!==null) network.fit();
}

document.getElementById('threshold').addEventListener('input',function(){
  document.getElementById('threshold-val').textContent=this.value;
});
document.getElementById('threshold').addEventListener('change',update);
document.getElementById('coauthor-edges-toggle').addEventListener('change',update);

// ── spacing slider ────────────────────────────────────────────────────────────
document.getElementById('spacing').addEventListener('input',function(){
  spreadFactor=parseFloat(this.value);
  document.getElementById('spacing-val').textContent=spreadFactor.toFixed(2)+'x';
  applyPositions();
});

// ── drag mode toggle ──────────────────────────────────────────────────────────
function toggleDragMode(){
  isDragMode=!isDragMode;
  var btn=document.getElementById('drag-mode-btn');
  var net=document.getElementById('network');
  btn.classList.toggle('active',isDragMode);
  net.classList.toggle('drag-mode',isDragMode);
  // dragNodes always stays true — individual dragging is handled by mode checks
  network.setOptions({interaction:{dragNodes:true}});
}

// ── theme isolation ───────────────────────────────────────────────────────────
function toggleHighlight(commId){
  if(highlightComm===commId){clearHighlight();return;}
  highlightComm=commId;
  document.querySelectorAll('.leg-item').forEach(function(el){
    el.classList.toggle('active',parseInt(el.dataset.comm)===commId);
  });
  document.getElementById('show-all-btn').style.display='block';
  document.getElementById('filter-note').style.display='none';
  var threshold =parseInt(document.getElementById('threshold').value);
  var showCoauth=document.getElementById('coauthor-edges-toggle').checked;
  var g=buildGraph(threshold,showCoauth,highlightComm);
  network.setOptions({physics:{enabled:false}});
  nodesDS.clear(); nodesDS.add(g.visNodes);
  edgesDS.clear(); edgesDS.add(g.visEdges);
  network.fit();
}

function clearHighlight(){
  highlightComm=null;
  document.querySelectorAll('.leg-item').forEach(function(el){
    el.classList.remove('active');
  });
  document.getElementById('show-all-btn').style.display='none';
  document.getElementById('filter-note').style.display='block';
  var threshold =parseInt(document.getElementById('threshold').value);
  var showCoauth=document.getElementById('coauthor-edges-toggle').checked;
  var g=buildGraph(threshold,showCoauth,null);
  network.setOptions({physics:{enabled:false}});
  nodesDS.clear(); nodesDS.add(g.visNodes);
  edgesDS.clear(); edgesDS.add(g.visEdges);
  network.fit();
}

// ── legend ────────────────────────────────────────────────────────────────────
function buildLegend(){
  var container=document.getElementById('legend-items');
  LEGEND.forEach(function(entry){
    var el=document.createElement('div');
    el.className='leg-item'; el.dataset.comm=entry.id;
    el.innerHTML='<div class="leg-swatch" style="background:'+entry.colour+'"></div>'
      +'<div><div class="leg-label">'+entry.theme+'</div>'
      +'<div class="leg-size">'+entry.size+' authors</div></div>';
    el.addEventListener('click',function(){toggleHighlight(entry.id);});
    container.appendChild(el);
  });
}

window.addEventListener('load',function(){buildLegend();init();});
</script>
</body>
</html>""")

out='/sessions/confident-loving-ritchie/mnt/outputs/chris_coauthor_network.html'
with open(out,'w',encoding='utf-8') as f:
    f.write('\n'.join(parts))

with open(out,'r',encoding='utf-8') as f:
    c=f.read()
print(f"Size: {len(c):,} chars")
print(f"Ends OK: {repr(c[-40:])}")
print(f"Has </html>: {'</html>' in c}")
