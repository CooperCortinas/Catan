from __future__ import annotations

import argparse
import json
import math
import secrets
import socket
import threading
from collections import Counter
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from catan_app import (
    BUILD_COSTS,
    CatanGame,
    LABEL_TO_RESOURCE,
    NUMBER_DOTS,
    RESOURCE_LABELS,
    RESOURCES,
    TERRAIN_LABELS,
    TERRAIN_RESOURCE,
)


HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Settlers Online</title>
<style>
*{box-sizing:border-box}html,body{min-height:100%;overscroll-behavior:none}body{margin:0;font:14px/1.35 Segoe UI,Arial,sans-serif;background:#eef3f4;color:#172026}
button,select,input{font:inherit;max-width:100%}button{border:1px solid #aeb8bd;background:#fff;border-radius:4px;padding:6px 10px;cursor:pointer;min-height:34px}button:hover{background:#f3f7f8}
.app{display:grid;grid-template-columns:250px minmax(520px,1fr) 330px;height:100vh;min-height:720px}
.left,.right{background:#f7f7f7;border-color:#d8dee2;padding:10px;overflow:auto}.left{border-right:1px solid #d8dee2}.right{border-left:1px solid #d8dee2}
h1{font-size:22px;margin:0 0 8px}h2{font-size:14px;margin:10px 0 6px}.small{font-size:12px;color:#5c6870}.panel{border:1px solid #d8dee2;background:#fff;padding:8px;margin:8px 0;border-radius:4px}
main{min-width:0;min-height:0}#board{display:block;width:100%;height:100%;background:#74b8d3;touch-action:manipulation}.row{display:flex;gap:6px;align-items:center;flex-wrap:wrap;margin:5px 0}
.grid{display:grid;grid-template-columns:1fr auto;gap:4px 12px}.scores div{display:flex;justify-content:space-between;border-bottom:1px solid #edf0f2;padding:2px 0}
.res{display:grid;grid-template-columns:repeat(2,1fr);gap:4px 14px}.res b{display:inline-block;min-width:24px}.log{height:55vh;overflow:auto;white-space:pre-wrap;background:#fffaf0;border:1px solid #e0d2a7;padding:8px}
.cards select,.trade select{width:100%;margin:3px 0}.hidden{display:none}.status{font-weight:600;margin:4px 0 8px}
.pending{border-color:#b88a2b;background:#fff8e4}.danger{color:#a33131}.ok{color:#276b3b}
@media (max-width: 820px){
  body{font-size:15px;overflow:auto}
  button,select,input{font-size:16px}button{min-height:42px;padding:8px 12px}
  .app{display:flex;flex-direction:column;height:auto;min-height:100vh}
  main{order:1;height:min(72vh,560px);min-height:430px;border-bottom:1px solid #d8dee2}
  .right{order:2;border-left:0;border-top:1px solid #d8dee2;overflow:visible}
  .left{order:3;border-right:0;border-top:1px solid #d8dee2;overflow:visible}
  .left,.right{width:100%;padding:10px 10px max(10px,env(safe-area-inset-bottom))}
  .right>h1,.left>h1{font-size:18px}
  #turnStatus{position:sticky;top:0;z-index:2;background:#fff;border:1px solid #d8dee2;border-radius:4px;padding:8px;margin-bottom:8px}
  .panel{margin:7px 0;padding:8px}.log{height:190px}
  .res{grid-template-columns:repeat(3,minmax(0,1fr));gap:6px}
  .row button{flex:1 1 120px}
  .trade label{display:inline-block;margin:2px 4px 2px 0}
  #offerBox,#requestBox{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:4px}
  #offerBox input,#requestBox input{width:52px}
}
@media (max-width: 480px){
  main{height:68vh;min-height:360px}
  .res{grid-template-columns:repeat(2,minmax(0,1fr))}
  .scores div{font-size:13px}
  #offerBox,#requestBox{grid-template-columns:1fr}
}
</style>
</head>
<body>
<div class="app">
  <aside class="left">
    <h1>Settlers Online</h1>
    <div class="panel">
      <div class="status" id="seatStatus">Not joined</div>
      <div class="row"><input id="nameInput" placeholder="Your name" style="width:135px"><button onclick="joinGame()">Join</button></div>
      <div class="row">
        <select id="newPlayers"><option value="4">4 players</option><option value="6">6 players</option></select>
        <button onclick="newGame()">New Game</button>
      </div>
      <div class="row">
        <select id="cpuDifficulty"><option value="normal">CPU normal</option><option value="easy">CPU easy</option><option value="hard">CPU hard</option></select>
        <button id="startBtn" onclick="startGame()">Start Game</button>
      </div>
      <div class="small">Host this server once. Everyone joins the same board URL.</div>
    </div>
    <h2>Turn Log</h2>
    <div class="log" id="log"></div>
  </aside>
  <main><canvas id="board"></canvas></main>
  <aside class="right">
    <h1>Game</h1>
    <div class="status" id="turnStatus"></div>
    <div class="panel scores"><h2>Scores</h2><div id="scores"></div><div class="small">Opponent VP excludes hidden development-card points.</div></div>
    <div class="panel">
      <div class="row"><button onclick="act({type:'roll'})">Roll</button><button onclick="act({type:'end_turn'})">End Turn</button></div>
      <h2>Action</h2>
      <label><input type="radio" name="action" value="inspect" checked> Inspect</label><br>
      <label><input type="radio" name="action" value="road"> Build Road</label><br>
      <label><input type="radio" name="action" value="settlement"> Build Settlement</label><br>
      <label><input type="radio" name="action" value="city"> Build City</label><br>
      <label><input type="radio" name="action" value="robber"> Move Robber</label>
    </div>
    <div class="panel res"><h2 style="grid-column:1/-1">Your Resources</h2><div>Brick <b id="r-brick">0</b></div><div>Wood <b id="r-lumber">0</b></div><div>Sheep <b id="r-wool">0</b></div><div>Wheat <b id="r-grain">0</b></div><div>Ore <b id="r-ore">0</b></div></div>
    <div class="panel cards"><h2>Development Cards</h2><select id="devSelect"></select><div id="devChoices"></div><button onclick="playDev()">Play Selected</button><button onclick="act({type:'buy_dev'})">Buy Development Card</button></div>
    <div class="panel trade"><h2>Bank / Harbor</h2><select id="bankGive"></select><select id="bankGet"></select><button onclick="bankTrade()">Trade</button><div class="small" id="rates"></div></div>
    <div class="panel trade"><h2>Player Trade</h2><select id="tradeTarget"></select><div class="small">You give</div><div id="offerBox"></div><div class="small">You get</div><div id="requestBox"></div><button onclick="proposeTrade()">Propose</button></div>
    <div class="panel pending hidden" id="pendingBox"><h2>Pending Trade</h2><div id="pendingText"></div><div class="row"><button onclick="respondTrade(true)">Accept</button><button onclick="respondTrade(false)">Decline</button></div></div>
  </aside>
</div>
<script>
const canvas=document.getElementById('board'), ctx=canvas.getContext('2d');
let state=null, token=localStorage.getItem('catan_token')||'', scale=1, ox=0, oy=0;
const resources=["brick","lumber","wool","grain","ore"], labels={brick:"Brick",lumber:"Wood",wool:"Sheep",grain:"Wheat",ore:"Ore"};
const terrainColors={hills:"#b7683f",forest:"#2f7d4a",pasture:"#80b855",fields:"#d7bd48",mountains:"#8a8d91",desert:"#d7b977"};
const playerColors=["#d63a2f","#f5f2e7","#2874d0","#ef8f28","#2f9e59","#8a5a35"];
function post(path,data){return fetch(path,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(data)}).then(r=>r.json()).then(j=>{if(!j.ok)alert(j.error||"Action failed");return j})}
function act(data){data.token=token;post("/api/action",data).then(fetchState)}
function newGame(){post("/api/new",{players:+document.getElementById('newPlayers').value}).then(j=>{if(j.ok){token='';localStorage.removeItem('catan_token')}fetchState()})}
function joinGame(){post("/api/join",{name:document.getElementById('nameInput').value||"Player"}).then(j=>{if(j.ok){token=j.token;localStorage.setItem('catan_token',token)}fetchState()})}
function startGame(){act({type:'start_game',difficulty:document.getElementById('cpuDifficulty').value})}
function fetchState(){fetch("/api/state?token="+encodeURIComponent(token)).then(r=>r.json()).then(j=>{state=j;renderAll()}).catch(()=>{})}
function renderAll(){if(!state)return;document.getElementById('seatStatus').textContent=state.you?`${state.you.name} (${state.you.color})`:"Not joined";document.getElementById('turnStatus').textContent=state.status;
document.getElementById('log').textContent=(state.log||[]).join("\n");document.getElementById('log').scrollTop=999999;
for(const r of resources)document.getElementById('r-'+r).textContent=state.you?state.you.resources[r]:0;
document.getElementById('scores').innerHTML=state.players.map(p=>`<div><span>${p.name}${p.cpu?" CPU":""}</span><b>${p.score} VP</b></div>`).join("");
document.getElementById('startBtn').disabled=!state.you||!state.you.host||state.started;
document.getElementById('startBtn').textContent=state.started?"Game Started":state.you&&state.you.host?"Start Game":"Host Starts Game";
fillSelect('bankGive',resources.map(r=>[r,labels[r]]));fillSelect('bankGet',resources.map(r=>[r,labels[r]]));document.getElementById('rates').textContent=state.you?resources.map(r=>`${labels[r]} ${state.you.rates[r]}:1`).join(" | "):"";
fillSelect('tradeTarget',state.players.filter(p=>!state.you||p.index!==state.you.index).map(p=>[p.index,p.name]));
fillResourceInputs('offerBox','offer');fillResourceInputs('requestBox','request');renderDev();renderPending();draw()}
function fillSelect(id,items){const el=document.getElementById(id), cur=el.value;el.innerHTML=items.map(([v,t])=>`<option value="${v}">${t}</option>`).join("");if(items.some(i=>String(i[0])===cur))el.value=cur}
function fillResourceInputs(id,prefix){const box=document.getElementById(id);if(box.childElementCount)return;box.innerHTML=resources.map(r=>`<label>${labels[r]} <input id="${prefix}-${r}" type="number" inputmode="numeric" min="0" max="20" value="0" style="width:46px"></label>`).join(" ")}
function renderDev(){const sel=document.getElementById('devSelect');let cards=(state.you&&state.you.dev_cards)||[];sel.innerHTML=cards.length?cards.map((c,i)=>`<option value="${i}">${i+1}. ${c.name}${c.playable?"":" ("+c.reason+")"}</option>`).join(""):`<option>No cards</option>`;let c=cards[sel.value]||cards[0];let box=document.getElementById('devChoices');box.innerHTML="";if(c&&c.name==="Monopoly")box.innerHTML=resourceDropdown('dev-one');if(c&&c.name==="Year of Plenty")box.innerHTML=resourceDropdown('dev-one')+resourceDropdown('dev-two')}
document.getElementById('devSelect').addEventListener('change',renderDev);
function resourceDropdown(id){return `<select id="${id}">${resources.map(r=>`<option value="${r}">${labels[r]}</option>`).join("")}</select>`}
function playDev(){let cards=(state.you&&state.you.dev_cards)||[], c=cards[document.getElementById('devSelect').value]||cards[0];if(!c)return;let data={type:'play_dev',card:c.name};if(c.name==="Monopoly")data.resource=document.getElementById('dev-one').value;if(c.name==="Year of Plenty")data.resources=[document.getElementById('dev-one').value,document.getElementById('dev-two').value];act(data)}
function bankTrade(){act({type:'bank_trade',give:document.getElementById('bankGive').value,get:document.getElementById('bankGet').value})}
function bundle(prefix){let b={};for(const r of resources)b[r]=+(document.getElementById(prefix+'-'+r)?.value||0);return b}
function proposeTrade(){act({type:'propose_trade',target:+document.getElementById('tradeTarget').value,offer:bundle('offer'),request:bundle('request')})}
function renderPending(){const p=state.pending_trade, box=document.getElementById('pendingBox');box.classList.toggle('hidden',!p);if(!p)return;document.getElementById('pendingText').textContent=`${p.from} offers ${p.offer} for ${p.request}.`}
function respondTrade(ok){act({type:ok?'accept_trade':'decline_trade'})}
function selectedAction(){return document.querySelector('input[name=action]:checked').value}
function resize(){const dpr=window.devicePixelRatio||1,w=Math.max(1,canvas.clientWidth),h=Math.max(1,canvas.clientHeight);canvas.width=Math.round(w*dpr);canvas.height=Math.round(h*dpr);ctx.setTransform(dpr,0,0,dpr,0,0);draw()}window.addEventListener('resize',resize);window.addEventListener('orientationchange',()=>setTimeout(resize,150));
function sx(x){return x*scale+ox}function sy(y){return y*scale+oy}function wx(x){return(x-ox)/scale}function wy(y){return(y-oy)/scale}
function draw(){if(!state||!state.board)return;let cw=canvas.clientWidth,ch=canvas.clientHeight;ctx.clearRect(0,0,cw,ch);let vs=Object.values(state.board.vertices), xs=vs.map(v=>v[0]), ys=vs.map(v=>v[1]);scale=Math.min(cw/(Math.max(...xs)-Math.min(...xs)+170),ch/(Math.max(...ys)-Math.min(...ys)+170));ox=cw/2-scale*(Math.min(...xs)+Math.max(...xs))/2;oy=ch/2-scale*(Math.min(...ys)+Math.max(...ys))/2;
for(const t of state.board.tiles){let pts=t.vertices.map(v=>state.board.vertices[v]);poly(pts,terrainColors[t.terrain],"#35545e",2);let c=center(t.q,t.r);ctx.fillStyle=["forest","hills","mountains"].includes(t.terrain)?"white":"#222";ctx.font="bold 13px Segoe UI";ctx.textAlign="center";ctx.fillText(t.label,sx(c[0]),sy(c[1])-12);if(t.number){ctx.beginPath();ctx.fillStyle="#f7efd5";ctx.strokeStyle="#5c4934";ctx.ellipse(sx(c[0]),sy(c[1])+18,18,20,0,0,Math.PI*2);ctx.fill();ctx.stroke();ctx.fillStyle=[6,8].includes(t.number)?"#b21f24":"#222";ctx.font="bold 16px Segoe UI";ctx.fillText(t.number,sx(c[0]),sy(c[1])+17);for(let i=0;i<t.dots;i++){let dx=(i-(t.dots-1)/2)*5;ctx.beginPath();ctx.arc(sx(c[0])+dx,sy(c[1])+31,2,0,Math.PI*2);ctx.fill()}}if(t.robber){ctx.fillStyle="#111";ctx.fillRect(sx(c[0])-8,sy(c[1])-10,16,24);ctx.beginPath();ctx.arc(sx(c[0]),sy(c[1])-18,11,0,Math.PI*2);ctx.fill()}}
for(const e of state.board.edges){if(e.owner===null)continue;let a=state.board.vertices[e.a],b=state.board.vertices[e.b];ctx.strokeStyle=playerColors[e.owner];ctx.lineWidth=6;ctx.lineCap="round";line(a,b)}
for(const p of state.board.ports){let v=state.board.vertices[p.v];ctx.beginPath();ctx.fillStyle="#e8f2ff";ctx.strokeStyle="#225d78";ctx.lineWidth=2;ctx.arc(sx(v[0]),sy(v[1]),14,0,Math.PI*2);ctx.fill();ctx.stroke();ctx.fillStyle="#111";ctx.font="bold 11px Segoe UI";ctx.fillText(p.label,sx(v[0]),sy(v[1])+4)}
if(selectedAction()==="settlement")for(const vId of state.legal.settlements||[]){let v=state.board.vertices[vId];ctx.beginPath();ctx.fillStyle="rgba(255,246,80,.65)";ctx.strokeStyle="#111";ctx.arc(sx(v[0]),sy(v[1]),9,0,Math.PI*2);ctx.fill();ctx.stroke()}
for(const b of state.board.buildings){let v=state.board.vertices[b.v];ctx.fillStyle=playerColors[b.owner];ctx.strokeStyle="#222";ctx.lineWidth=2;if(b.kind==="city"){ctx.fillRect(sx(v[0])-12,sy(v[1])-12,24,24);ctx.strokeRect(sx(v[0])-12,sy(v[1])-12,24,24)}else{ctx.beginPath();ctx.moveTo(sx(v[0])-12,sy(v[1])+10);ctx.lineTo(sx(v[0])-12,sy(v[1])-4);ctx.lineTo(sx(v[0]),sy(v[1])-15);ctx.lineTo(sx(v[0])+12,sy(v[1])-4);ctx.lineTo(sx(v[0])+12,sy(v[1])+10);ctx.closePath();ctx.fill();ctx.stroke()}}}
function poly(pts,fill,stroke,w){ctx.beginPath();ctx.moveTo(sx(pts[0][0]),sy(pts[0][1]));for(const p of pts.slice(1))ctx.lineTo(sx(p[0]),sy(p[1]));ctx.closePath();ctx.fillStyle=fill;ctx.fill();ctx.strokeStyle=stroke;ctx.lineWidth=w;ctx.stroke()}
function line(a,b){ctx.beginPath();ctx.moveTo(sx(a[0]),sy(a[1]));ctx.lineTo(sx(b[0]),sy(b[1]));ctx.stroke()}
function center(q,r){let size=46;return [size*Math.sqrt(3)*(q+r/2),size*1.5*r]}
function nearestVertex(x,y){let best=null,bd=1e9;for(const [id,v] of Object.entries(state.board.vertices)){let d=(v[0]-x)**2+(v[1]-y)**2;if(d<bd){bd=d;best=+id}}return Math.sqrt(bd)<22?best:null}
function nearestEdge(x,y){let best=null,bd=1e9;for(const e of state.board.edges){let a=state.board.vertices[e.a],b=state.board.vertices[e.b],d=distSeg(x,y,a,b);if(d<bd){bd=d;best=[e.a,e.b]}}return Math.sqrt(bd)<20?best:null}
function nearestHex(x,y){let best=null,bd=1e9;for(const t of state.board.tiles){let c=center(t.q,t.r),d=(c[0]-x)**2+(c[1]-y)**2;if(d<bd){bd=d;best=t.hid}}return best}
function distSeg(px,py,a,b){let dx=b[0]-a[0],dy=b[1]-a[1],t=Math.max(0,Math.min(1,((px-a[0])*dx+(py-a[1])*dy)/(dx*dx+dy*dy)));let x=a[0]+t*dx,y=a[1]+t*dy;return(x-px)**2+(y-py)**2}
canvas.addEventListener('click',ev=>{if(!state||!state.you)return;let r=canvas.getBoundingClientRect(),x=wx(ev.clientX-r.left),y=wy(ev.clientY-r.top),a=selectedAction();if(state.phase==="setup_settlement"||a==="settlement")act({type:'settlement',vertex:nearestVertex(x,y)});else if(state.phase==="setup_road"||a==="road"||state.awaiting==="free_road"){let e=nearestEdge(x,y);if(e)act({type:'road',edge:e})}else if(a==="city")act({type:'city',vertex:nearestVertex(x,y)});else if(a==="robber"||state.awaiting==="robber")act({type:'robber',hex:nearestHex(x,y)})});
resize();fetchState();setInterval(fetchState,1000);
</script>
</body>
</html>"""


class OnlineCatan:
    def __init__(self, players: int = 4):
        self.lock = threading.RLock()
        self.reset(players)

    def reset(self, players: int) -> None:
        names = [f"Player {i + 1}" for i in range(players)]
        self.game = CatanGame(players, players, names)
        self.claims: dict[str, int] = {}
        self.host_token: str | None = None
        self.started = False
        self.pending_trade: dict | None = None

    def join(self, name: str) -> dict:
        with self.lock:
            claimed = set(self.claims.values())
            for index in range(self.game.player_count):
                if index not in claimed:
                    token = secrets.token_urlsafe(18)
                    self.claims[token] = index
                    if self.host_token is None:
                        self.host_token = token
                    self.game.players[index].name = name[:20] or f"Player {index + 1}"
                    self.game.add_log(f"{self.game.players[index].name} joined seat {index + 1}.")
                    return {"ok": True, "token": token, "player": index, "host": self.host_token == token}
            return {"ok": False, "error": "All seats are already claimed."}

    def player_for(self, token: str) -> int | None:
        return self.claims.get(token)

    def require_turn(self, token: str) -> tuple[bool, int | str]:
        player = self.player_for(token)
        if player is None:
            return False, "Join the game first."
        if not self.started:
            return False, "The host has not started the game yet."
        if player != self.game.current:
            return False, "It is not your turn."
        if self.game.winner is not None:
            return False, "The game is over."
        return True, player

    def state(self, token: str) -> dict:
        with self.lock:
            viewer = self.player_for(token)
            g = self.game
            return {
                "ok": True,
                "started": self.started,
                "phase": g.phase,
                "awaiting": g.awaiting,
                "status": self._status(),
                "log": g.log[-28:],
                "players": [
                    {
                        "index": i,
                        "name": p.name,
                        "cpu": p.is_cpu,
                        "score": g.public_score(i, viewer if viewer is not None else -1),
                    }
                    for i, p in enumerate(g.players)
                ],
                "you": self._you(viewer) if viewer is not None else None,
                "board": self._board(),
                "legal": self._legal(viewer),
                "pending_trade": self._pending_for(viewer),
            }

    def action(self, token: str, data: dict) -> dict:
        with self.lock:
            kind = data.get("type")
            if kind == "start_game":
                return self.start_game(token, data.get("difficulty", "normal"))
            ok, player_or_error = self.require_turn(token)
            if not ok and kind not in ("accept_trade", "decline_trade"):
                return {"ok": False, "error": player_or_error}
            player = player_or_error if ok else self.player_for(token)
            g = self.game
            if kind == "roll":
                if g.phase != "play":
                    return {"ok": False, "error": "Finish setup first."}
                if g.turn_has_rolled:
                    return {"ok": False, "error": "You already rolled."}
                g.roll()
            elif kind == "settlement":
                vertex = data.get("vertex")
                if vertex is None:
                    return {"ok": False, "error": "Click a corner."}
                setup = g.phase == "setup_settlement"
                if not g.place_settlement(player, int(vertex), setup=setup):
                    return {"ok": False, "error": g.settlement_block_reason(player, int(vertex), setup=setup)}
                if setup:
                    g.pending_setup_vertex = int(vertex)
                    g.phase = "setup_road"
            elif kind == "road":
                edge = data.get("edge")
                if not edge:
                    return {"ok": False, "error": "Click a road edge."}
                edge_tuple = tuple(sorted((int(edge[0]), int(edge[1]))))
                if g.phase == "setup_road":
                    if not g.place_road(player, edge_tuple, setup_vertex=g.pending_setup_vertex):
                        return {"ok": False, "error": "That setup road is not legal."}
                    g.finish_setup_step()
                elif g.awaiting == "free_road":
                    if not g.place_road(player, edge_tuple, free=True):
                        return {"ok": False, "error": "That free road is not legal."}
                    g.free_roads_remaining -= 1
                    if g.free_roads_remaining <= 0 or not g.valid_road_edges(player):
                        g.awaiting = None
                        g.free_roads_remaining = 0
                        g.add_log("Road Building complete.")
                else:
                    if not g.place_road(player, edge_tuple):
                        return {"ok": False, "error": "That road is not legal or affordable."}
            elif kind == "city":
                if not g.place_city(player, int(data.get("vertex"))):
                    return {"ok": False, "error": "That city is not legal or affordable."}
            elif kind == "robber":
                if g.awaiting != "robber" and data.get("type") != "robber":
                    return {"ok": False, "error": "You are not moving the robber now."}
                g.move_robber(int(data.get("hex")))
            elif kind == "buy_dev":
                if not g.buy_dev(player):
                    return {"ok": False, "error": "You cannot buy a development card."}
            elif kind == "play_dev":
                card = data.get("card")
                choice = data.get("resource")
                if card == "Year of Plenty":
                    choice = ",".join(r for r in data.get("resources", []) if r in RESOURCES)
                if not g.play_dev(card, choice):
                    return {"ok": False, "error": "That development card cannot be played right now."}
            elif kind == "bank_trade":
                if not g.bank_trade(data.get("give"), data.get("get")):
                    return {"ok": False, "error": "That bank/harbor trade is not available."}
            elif kind == "propose_trade":
                target = int(data.get("target"))
                if target == player:
                    return {"ok": False, "error": "Choose another player."}
                offer = self._clean_bundle(data.get("offer", {}))
                request = self._clean_bundle(data.get("request", {}))
                if not any(offer.values()) and not any(request.values()):
                    return {"ok": False, "error": "Offer or request at least one card."}
                if not g._has_resources(g.players[player], offer):
                    return {"ok": False, "error": "You do not have the offered resources."}
                if not g._has_resources(g.players[target], request):
                    return {"ok": False, "error": f"{g.players[target].name} does not have those resources."}
                if g.players[target].is_cpu:
                    if self.cpu_accepts_trade(player, target, offer, request):
                        if not g.player_trade(player, target, offer, request):
                            return {"ok": False, "error": "That trade is no longer possible."}
                    else:
                        g.add_log(f"{g.players[target].name} declined {g.players[player].name}'s trade.")
                    return {"ok": True}
                self.pending_trade = {"from": player, "to": target, "offer": offer, "request": request}
                g.add_log(f"{g.players[player].name} proposed a trade to {g.players[target].name}.")
            elif kind == "accept_trade":
                if not self.pending_trade or self.pending_trade["to"] != player:
                    return {"ok": False, "error": "No trade is waiting for you."}
                trade = self.pending_trade
                if not g.player_trade(trade["from"], trade["to"], trade["offer"], trade["request"]):
                    self.pending_trade = None
                    return {"ok": False, "error": "That trade is no longer possible."}
                self.pending_trade = None
            elif kind == "decline_trade":
                if self.pending_trade and self.pending_trade["to"] == player:
                    g.add_log(f"{g.players[player].name} declined the trade.")
                    self.pending_trade = None
            elif kind == "end_turn":
                if g.phase != "play":
                    return {"ok": False, "error": "Setup is not finished."}
                if not g.turn_has_rolled:
                    return {"ok": False, "error": "Roll before ending your turn."}
                if g.awaiting:
                    return {"ok": False, "error": "Finish the pending action first."}
                g.next_turn()
                self.advance_cpus()
            else:
                return {"ok": False, "error": "Unknown action."}
            if kind not in ("end_turn",):
                self.advance_cpus()
            return {"ok": True}

    def start_game(self, token: str, difficulty: str) -> dict:
        if token != self.host_token:
            return {"ok": False, "error": "Only the first joined player can start the game."}
        if self.started:
            return {"ok": False, "error": "The game has already started."}
        difficulty = difficulty if difficulty in ("easy", "normal", "hard") else "normal"
        claimed = set(self.claims.values())
        for index, player in enumerate(self.game.players):
            if index not in claimed:
                player.is_cpu = True
                player.name = f"CPU {index + 1}"
                player.difficulty = difficulty
            else:
                player.is_cpu = False
        self.started = True
        self.game.add_log(f"Game started. Empty seats filled with {difficulty} CPUs.")
        self.advance_cpus()
        return {"ok": True}

    def advance_cpus(self) -> None:
        guard = 0
        while self.started and self.game.winner is None and self.game.active_player().is_cpu and guard < 24:
            guard += 1
            if self.game.phase.startswith("setup"):
                self.game.cpu_take_setup()
            else:
                self.game.cpu_take_turn()

    def _clean_bundle(self, raw: dict) -> dict[str, int]:
        return {r: max(0, int(raw.get(r, 0) or 0)) for r in RESOURCES}

    def cpu_accepts_trade(self, proposer: int, cpu_index: int, offer: dict[str, int], request: dict[str, int]) -> bool:
        g = self.game
        cpu = g.players[cpu_index]
        if not g._has_resources(cpu, request):
            return False
        offer_value = self._trade_bundle_value(cpu_index, offer)
        request_value = self._trade_bundle_value(cpu_index, request)
        proposer_score = g.public_score(proposer, cpu_index)
        cpu_score = g.public_score(cpu_index, cpu_index)
        difficulty = getattr(cpu, "difficulty", "normal")
        leader_penalty = 1.0
        if proposer_score >= cpu_score + 2:
            leader_penalty += 0.25
        if proposer_score >= 8:
            leader_penalty += 0.35
        margin = 0.2 if difficulty == "easy" else 0.45 if difficulty == "normal" else 0.75
        margin += max(0, proposer_score - cpu_score) * (0.1 if difficulty == "easy" else 0.18)
        if difficulty == "easy":
            return offer_value >= request_value * leader_penalty + margin and sum(offer.values()) >= sum(request.values())
        return offer_value >= request_value * leader_penalty + margin

    def _trade_bundle_value(self, player_index: int, bundle: dict[str, int]) -> float:
        return sum(amount * self._resource_trade_value(player_index, resource) for resource, amount in bundle.items())

    def _resource_trade_value(self, player_index: int, resource: str) -> float:
        g = self.game
        player = g.players[player_index]
        value = 1.0
        if player.resources[resource] == 0:
            value += 0.55
        if g.trade_rate(player_index, resource) <= 2:
            value -= 0.25
        for build, cost in BUILD_COSTS.items():
            missing = {r: max(0, n - player.resources[r]) for r, n in cost.items()}
            if missing.get(resource, 0) > 0:
                if build == "city" and g.valid_city_vertices(player_index):
                    value += 0.9
                elif build == "settlement" and g.valid_settlement_vertices(player_index):
                    value += 0.75
                elif build == "road" and g.valid_road_edges(player_index):
                    value += 0.35
                elif build == "development":
                    value += 0.25
        return max(0.2, value)

    def _status(self) -> str:
        g = self.game
        if not self.started:
            joined = len(self.claims)
            return f"Lobby: {joined}/{g.player_count} players joined. First player can start and fill open seats with CPUs."
        p = g.active_player()
        if g.winner is not None:
            return f"{g.players[g.winner].name} wins."
        if g.phase == "setup_settlement":
            return f"{p.name}: place a starting settlement."
        if g.phase == "setup_road":
            return f"{p.name}: place a road touching that settlement."
        if g.awaiting == "robber":
            return f"{p.name}: move the robber."
        if g.awaiting == "free_road":
            return f"{p.name}: place {g.free_roads_remaining} free road(s)."
        return f"{p.name}'s turn. " + ("Roll the dice." if not g.turn_has_rolled else "Trade, build, play a card, or end turn.")

    def _you(self, viewer: int) -> dict:
        g = self.game
        p = g.players[viewer]
        new_counts = {}
        for card in p.new_dev_cards:
            new_counts[card] = new_counts.get(card, 0) + 1
        playable = Counter(g.playable_dev_cards(viewer))
        cards = []
        for card in p.dev_cards:
            reason = ""
            can_play = False
            if card == "Victory Point":
                reason = "hidden VP"
            elif new_counts.get(card, 0):
                new_counts[card] -= 1
                reason = "new this turn"
            elif g.dev_played_this_turn:
                reason = "already played"
            else:
                can_play = playable[card] > 0
                if can_play:
                    playable[card] -= 1
                else:
                    reason = "not playable"
            cards.append({"name": card, "playable": can_play, "reason": reason})
        return {
            "index": viewer,
            "name": p.name,
            "color": f"Player {viewer + 1}",
            "host": self.host_token is not None and self.claims.get(self.host_token) == viewer,
            "resources": p.resources,
            "dev_cards": cards,
            "rates": {r: g.trade_rate(viewer, r) for r in RESOURCES},
        }

    def _legal(self, viewer: int | None) -> dict:
        if viewer is None or viewer != self.game.current:
            return {"settlements": []}
        if not self.started:
            return {"settlements": []}
        return {"settlements": self.game.valid_settlement_vertices(viewer)}

    def _pending_for(self, viewer: int | None) -> dict | None:
        if viewer is None or not self.pending_trade or self.pending_trade["to"] != viewer:
            return None
        trade = self.pending_trade
        return {
            "from": self.game.players[trade["from"]].name,
            "offer": self.game._resource_bundle_text(trade["offer"]),
            "request": self.game._resource_bundle_text(trade["request"]),
        }

    def _board(self) -> dict:
        g = self.game
        return {
            "vertices": {str(v): [x, y] for v, (x, y) in g.vertices.items()},
            "tiles": [
                {
                    "hid": t.hid,
                    "q": t.q,
                    "r": t.r,
                    "terrain": t.terrain,
                    "label": TERRAIN_LABELS[t.terrain],
                    "number": t.number,
                    "dots": NUMBER_DOTS[t.number] if t.number else 0,
                    "robber": t.robber,
                    "vertices": t.vertices,
                }
                for t in g.tiles
            ],
            "edges": [{"a": a, "b": b, "owner": owner} for (a, b), owner in g.edges.items()],
            "buildings": [{"v": v, "owner": b.owner, "kind": b.kind} for v, b in g.buildings.items()],
            "ports": [
                {"v": v, "partner": partner, "type": port, "label": "3" if port == "3:1" else RESOURCE_LABELS[port][:2].lower()}
                for v, partner, port in g.port_markers
            ],
        }


APP = OnlineCatan()


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self._send(200, HTML, "text/html; charset=utf-8")
        elif parsed.path == "/api/state":
            token = parse_qs(parsed.query).get("token", [""])[0]
            self._json(APP.state(token))
        else:
            self._json({"ok": False, "error": "Not found"}, 404)

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        data = json.loads(self.rfile.read(length) or b"{}")
        if self.path == "/api/new":
            players = int(data.get("players", 4))
            if players not in (4, 6):
                self._json({"ok": False, "error": "Choose 4 or 6 players."})
                return
            with APP.lock:
                APP.reset(players)
            self._json({"ok": True})
        elif self.path == "/api/join":
            self._json(APP.join(data.get("name", "Player")))
        elif self.path == "/api/action":
            self._json(APP.action(data.get("token", ""), data))
        else:
            self._json({"ok": False, "error": "Not found"}, 404)

    def log_message(self, _format: str, *_args) -> None:
        return

    def _json(self, payload: dict, status: int = 200) -> None:
        self._send(status, json.dumps(payload).encode("utf-8"), "application/json")

    def _send(self, status: int, body, content_type: str) -> None:
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def local_ip() -> str:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        try:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
        except OSError:
            return "127.0.0.1"


def main() -> None:
    parser = argparse.ArgumentParser(description="Host the online Settlers app.")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"Open on this computer: http://127.0.0.1:{args.port}")
    print(f"Other people on your network: http://{local_ip()}:{args.port}")
    print("Press Ctrl+C to stop.")
    server.serve_forever()


if __name__ == "__main__":
    main()
