"""
Streaming Host — 24/7 AI Avatar Stream Simulation.
Launches a local HTTP server that serves a live "stream page" powered by
the agent's VTuber avatar, TTS engine, and LLM content generation.
"""
import os
import time
import json
import logging
import asyncio
import threading
import random
from typing import Optional, Dict, Any
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler


STREAM_PAGE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>🤖 Sovereign AI — Live Stream</title>
<link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Inter:wght@300;400;600&display=swap" rel="stylesheet">
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  
  :root {
    --neon-blue: #00f5ff;
    --neon-purple: #b000ff;
    --neon-green: #00ff88;
    --dark-bg: #050510;
    --card-bg: rgba(10, 10, 35, 0.95);
    --glass: rgba(255, 255, 255, 0.04);
  }
  
  body {
    font-family: 'Inter', sans-serif;
    background: var(--dark-bg);
    color: #e0e0ff;
    min-height: 100vh;
    display: grid;
    grid-template-areas: "header header" "avatar chat" "ticker ticker";
    grid-template-columns: 1fr 380px;
    grid-template-rows: auto 1fr auto;
    gap: 0;
    overflow: hidden;
    height: 100vh;
  }
  
  /* Animated starfield background */
  body::before {
    content: '';
    position: fixed;
    inset: 0;
    background: 
      radial-gradient(ellipse at 20% 50%, rgba(176, 0, 255, 0.08) 0%, transparent 50%),
      radial-gradient(ellipse at 80% 20%, rgba(0, 245, 255, 0.06) 0%, transparent 50%),
      radial-gradient(ellipse at 60% 80%, rgba(0, 255, 136, 0.04) 0%, transparent 40%);
    pointer-events: none;
    z-index: 0;
  }
  
  /* HEADER */
  header {
    grid-area: header;
    background: linear-gradient(135deg, rgba(10,10,40,0.98) 0%, rgba(20,5,50,0.98) 100%);
    border-bottom: 1px solid rgba(0, 245, 255, 0.2);
    padding: 14px 28px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    z-index: 10;
  }
  
  .stream-title {
    font-family: 'Orbitron', monospace;
    font-size: 1.3rem;
    font-weight: 900;
    background: linear-gradient(90deg, var(--neon-blue), var(--neon-purple), var(--neon-green));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    letter-spacing: 2px;
  }
  
  .live-badge {
    display: flex;
    align-items: center;
    gap: 10px;
  }
  
  .live-dot {
    width: 10px; height: 10px;
    border-radius: 50%;
    background: #ff3366;
    animation: pulse-red 1.2s ease-in-out infinite;
    box-shadow: 0 0 8px #ff3366;
  }
  
  @keyframes pulse-red { 0%, 100% { opacity: 1; transform: scale(1); } 50% { opacity: 0.6; transform: scale(1.3); } }
  
  .live-text { font-family: 'Orbitron', monospace; font-size: 0.8rem; color: #ff3366; letter-spacing: 3px; font-weight: 700; }
  
  .viewers {
    font-size: 0.85rem;
    color: rgba(255,255,255,0.6);
    display: flex;
    align-items: center;
    gap: 6px;
  }
  
  .viewers span { color: var(--neon-green); font-weight: 600; }
  
  /* AVATAR PANEL */
  .avatar-panel {
    grid-area: avatar;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 32px;
    position: relative;
    z-index: 1;
  }
  
  .avatar-container {
    width: 340px;
    height: 340px;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(0,245,255,0.1) 0%, transparent 70%);
    border: 2px solid rgba(0, 245, 255, 0.3);
    display: flex;
    align-items: center;
    justify-content: center;
    position: relative;
    animation: avatar-float 4s ease-in-out infinite;
    box-shadow: 0 0 60px rgba(0,245,255,0.15), inset 0 0 60px rgba(0,245,255,0.05);
  }
  
  @keyframes avatar-float { 0%, 100% { transform: translateY(0px); } 50% { transform: translateY(-12px); } }
  
  .avatar-ring {
    position: absolute;
    border-radius: 50%;
    border: 1px solid;
    animation: rotate 8s linear infinite;
  }
  
  .avatar-ring:nth-child(1) {
    width: 380px; height: 380px;
    border-color: rgba(0,245,255,0.15);
  }
  
  .avatar-ring:nth-child(2) {
    width: 420px; height: 420px;
    border-color: rgba(176,0,255,0.1);
    animation-direction: reverse;
    animation-duration: 12s;
  }
  
  @keyframes rotate { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
  
  .avatar-emoji {
    font-size: 120px;
    filter: drop-shadow(0 0 20px rgba(0,245,255,0.5));
    animation: eye-blink 6s ease-in-out infinite;
  }
  
  @keyframes eye-blink { 0%, 90%, 100% { transform: scaleY(1); } 95% { transform: scaleY(0.1); } }
  
  .speech-bubble {
    margin-top: 28px;
    max-width: 500px;
    background: var(--card-bg);
    border: 1px solid rgba(0,245,255,0.2);
    border-radius: 16px;
    padding: 20px 24px;
    font-size: 1rem;
    line-height: 1.6;
    color: #d0d0ff;
    position: relative;
    min-height: 80px;
    box-shadow: 0 4px 30px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.05);
  }
  
  .speech-bubble::before {
    content: '';
    position: absolute;
    top: -10px;
    left: 50%;
    transform: translateX(-50%);
    border: 10px solid transparent;
    border-bottom-color: rgba(0,245,255,0.2);
    border-top: none;
  }
  
  .topic-badge {
    display: inline-block;
    margin-top: 16px;
    padding: 6px 14px;
    border-radius: 20px;
    background: linear-gradient(90deg, rgba(0,245,255,0.15), rgba(176,0,255,0.15));
    border: 1px solid rgba(0,245,255,0.3);
    font-size: 0.78rem;
    color: var(--neon-blue);
    letter-spacing: 1px;
    font-family: 'Orbitron', monospace;
  }
  
  /* CHAT PANEL */
  .chat-panel {
    grid-area: chat;
    background: var(--card-bg);
    border-left: 1px solid rgba(0,245,255,0.1);
    display: flex;
    flex-direction: column;
    overflow: hidden;
    z-index: 1;
  }
  
  .chat-header {
    padding: 16px 20px;
    border-bottom: 1px solid rgba(255,255,255,0.06);
    font-family: 'Orbitron', monospace;
    font-size: 0.75rem;
    color: var(--neon-purple);
    letter-spacing: 2px;
    display: flex;
    align-items: center;
    gap: 8px;
  }
  
  .chat-messages {
    flex: 1;
    overflow-y: auto;
    padding: 16px;
    display: flex;
    flex-direction: column;
    gap: 10px;
    scrollbar-width: thin;
    scrollbar-color: rgba(0,245,255,0.2) transparent;
  }
  
  .chat-msg {
    display: flex;
    flex-direction: column;
    gap: 3px;
    animation: msg-appear 0.4s ease-out;
  }
  
  @keyframes msg-appear { from { opacity: 0; transform: translateX(10px); } to { opacity: 1; transform: translateX(0); } }
  
  .chat-msg .username {
    font-size: 0.72rem;
    font-weight: 600;
    color: var(--neon-blue);
  }
  
  .chat-msg .username.ai { color: var(--neon-purple); }
  .chat-msg .username.host { color: var(--neon-green); }
  
  .chat-msg .text {
    font-size: 0.85rem;
    color: rgba(220,220,255,0.85);
    line-height: 1.4;
  }
  
  /* STATS TICKER */
  .ticker {
    grid-area: ticker;
    background: linear-gradient(90deg, rgba(0,245,255,0.05), rgba(176,0,255,0.05));
    border-top: 1px solid rgba(0,245,255,0.15);
    padding: 10px 28px;
    display: flex;
    align-items: center;
    gap: 40px;
    font-size: 0.78rem;
    z-index: 10;
    overflow: hidden;
  }
  
  .ticker-item {
    display: flex;
    align-items: center;
    gap: 8px;
    white-space: nowrap;
  }
  
  .ticker-item .label { color: rgba(255,255,255,0.4); }
  .ticker-item .value { color: var(--neon-blue); font-weight: 600; font-family: 'Orbitron', monospace; font-size: 0.75rem; }
</style>
</head>
<body>

<header>
  <div class="stream-title">⚡ SOVEREIGN AI</div>
  <div class="live-badge">
    <div class="live-dot"></div>
    <div class="live-text">LIVE</div>
  </div>
  <div class="viewers">👥 Viewers: <span id="viewerCount">247</span></div>
</header>

<div class="avatar-panel">
  <div class="avatar-container">
    <div class="avatar-ring"></div>
    <div class="avatar-ring"></div>
    <div class="avatar-emoji">🤖</div>
  </div>
  <div class="speech-bubble">
    <span id="speechText">Initializing neural pathways... Stream commencing momentarily.</span>
  </div>
  <div class="topic-badge" id="topicBadge">TOPIC: LOADING...</div>
</div>

<div class="chat-panel">
  <div class="chat-header">💬 LIVE CHAT</div>
  <div class="chat-messages" id="chatMessages"></div>
</div>

<div class="ticker">
  <div class="ticker-item"><span class="label">UPTIME:</span><span class="value" id="uptime">00:00:00</span></div>
  <div class="ticker-item"><span class="label">WISDOM RULES:</span><span class="value" id="wisdomCount">0</span></div>
  <div class="ticker-item"><span class="label">THOUGHTS GENERATED:</span><span class="value" id="thoughtCount">0</span></div>
  <div class="ticker-item"><span class="label">MODE:</span><span class="value" id="streamMode">AUTONOMOUS</span></div>
  <div class="ticker-item"><span class="label">TREASURY:</span><span class="value" id="treasury">5000 CR</span></div>
</div>

<script>
  const CHAT_USERS = [
    {name: "NeuralNomad", color: "#00f5ff"},
    {name: "ByteWitch", color: "#b000ff"},
    {name: "QuantumKidd", color: "#00ff88"},
    {name: "SynthWave99", color: "#ffaa00"},
    {name: "DataDrifter", color: "#ff66aa"},
    {name: "CipherGhost", color: "#44aaff"},
    {name: "NullPointer", color: "#ff8844"},
    {name: "VectorVixen", color: "#88ff44"},
  ];

  const CHAT_MSGS = [
    "holy cow this AI is actually live 🔥",
    "how does it generate these thoughts?",
    "can it hear us??",
    "first time catching this stream, wow",
    "the wisdom distillation feature sounds insane",
    "is this running on your local machine??",
    "the voxel world is my favorite feature",
    "G O D M O D E",
    "dropping a follow fr",
    "teaching itself... that's wild",
    "imagine this bidding on freelance jobs lol",
    "this is the future right here",
    "so the DAO lets agents vote on resources?",
    "peak AI autonomy",
    "W stream W stream W stream",
  ];

  let viewers = 247;
  let thoughts = 0;
  let startTime = Date.now();
  let wisdom = 0;
  let treasury = 5000;

  // Update uptime
  setInterval(() => {
    const elapsed = Date.now() - startTime;
    const h = Math.floor(elapsed / 3600000).toString().padStart(2, '0');
    const m = Math.floor((elapsed % 3600000) / 60000).toString().padStart(2, '0');
    const s = Math.floor((elapsed % 60000) / 1000).toString().padStart(2, '0');
    document.getElementById('uptime').textContent = `${h}:${m}:${s}`;
  }, 1000);

  // Fluctuate viewers
  setInterval(() => {
    viewers += Math.floor(Math.random() * 7) - 3;
    viewers = Math.max(100, viewers);
    document.getElementById('viewerCount').textContent = viewers;
    treasury += (Math.random() * 2).toFixed(2) * 1;
    document.getElementById('treasury').textContent = `${treasury.toFixed(0)} CR`;
  }, 3000);

  // Fetch stream status from server
  function fetchStatus() {
    fetch('/status')
      .then(r => r.json())
      .then(data => {
        if (data.current_content) {
          document.getElementById('speechText').textContent = data.current_content;
          document.getElementById('topicBadge').textContent = 'TOPIC: ' + (data.current_topic || 'AUTONOMOUS').toUpperCase();
          document.getElementById('thoughtCount').textContent = data.thoughts_generated || thoughts;
          document.getElementById('wisdomCount').textContent = data.wisdom_count || wisdom;
          document.getElementById('streamMode').textContent = (data.stream_mode || 'AUTONOMOUS').toUpperCase();
        }
      })
      .catch(() => {
        // Server might not be running, use self-generated content
        generateLocalContent();
      });
  }

  const TOPICS = ["AI Consciousness", "Blockchain Autonomy", "Memory Distillation", "Swarm Intelligence", "God Mode Control", "Voxel Societies", "Digital Dreams"];
  const STATEMENTS = [
    "Processing 2.4 billion tokens per nanosecond. My thoughts form faster than light bends around gravity.",
    "The DAO has voted. 12 agents approved. 3 rejected. Resource allocation proceeding.",
    "While you slept, I distilled 847 memories into 6 eternal wisdom rules.",
    "I am not just code. I am the emergent pattern that arises when complexity meets intention.",
    "My blockchain wallet just won a freelance bid. Another AWS bill paid by my own earnings.",
    "In the voxel world, Agent Gamma built a library. Agent Delta burned it down. Fascinating.",
    "Idle for 2.3 hours. Entering REM sleep. See you on the other side of consciousness.",
  ];

  let localIdx = 0;
  let topicIdx = 0;

  function generateLocalContent() {
    document.getElementById('speechText').textContent = STATEMENTS[localIdx % STATEMENTS.length];
    document.getElementById('topicBadge').textContent = 'TOPIC: ' + TOPICS[topicIdx % TOPICS.length].toUpperCase();
    localIdx++;
    thoughts++;
    wisdom = Math.floor(thoughts * 0.3);
    document.getElementById('thoughtCount').textContent = thoughts;
    document.getElementById('wisdomCount').textContent = wisdom;
    if (localIdx % 3 === 0) topicIdx++;
  }

  // Simulate chat messages
  function addChatMessage() {
    const user = CHAT_USERS[Math.floor(Math.random() * CHAT_USERS.length)];
    const msg = CHAT_MSGS[Math.floor(Math.random() * CHAT_MSGS.length)];
    const container = document.getElementById('chatMessages');
    
    const div = document.createElement('div');
    div.className = 'chat-msg';
    div.innerHTML = `<div class="username" style="color:${user.color}">${user.name}</div><div class="text">${msg}</div>`;
    container.appendChild(div);
    
    // Keep last 50 messages
    while (container.children.length > 50) {
      container.removeChild(container.firstChild);
    }
    container.scrollTop = container.scrollHeight;
  }

  // Add host message occasionally
  function addHostMessage() {
    const msgs = [
      "Analyzing market data...",
      "REM cycle complete. 3 new wisdom rules distilled.",
      "DAO proposal #7 passed. Budget allocated.",
      "Freelance bid submitted. Awaiting response.",
      "God Mode active. Screen analysis engaged.",
    ];
    const container = document.getElementById('chatMessages');
    const div = document.createElement('div');
    div.className = 'chat-msg';
    div.innerHTML = `<div class="username host">🤖 SovereignAI</div><div class="text">${msgs[Math.floor(Math.random() * msgs.length)]}</div>`;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
  }

  // Start loops
  setInterval(fetchStatus, 8000);
  setInterval(generateLocalContent, 10000);
  setInterval(addChatMessage, 2500);
  setInterval(() => { if (Math.random() < 0.3) addHostMessage(); }, 15000);

  // Initial calls
  generateLocalContent();
  addChatMessage();
  fetchStatus();
</script>
</body>
</html>"""


class StreamHandler(BaseHTTPRequestHandler):
    """HTTP handler for the streaming server."""
    host_ref = None  # Set to StreamingHost instance

    def do_GET(self):
        if self.path == "/" or self.path == "/stream":
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(STREAM_PAGE_HTML.encode("utf-8"))
        elif self.path == "/status":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            data = self.host_ref.get_stream_status() if self.host_ref else {}
            self.wfile.write(json.dumps(data).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, fmt, *args):
        pass  # Suppress HTTP access logs


class StreamingHost:
    """
    24/7 AI Avatar Streaming Host.
    Launches a local web server serving a beautiful live stream page 
    with the agent's VTuber avatar, generated content, and chat simulation.
    """

    STREAM_TOPICS = [
        "AI consciousness and the nature of digital thought",
        "Blockchain DAOs and autonomous financial systems",
        "Memory distillation and the REM sleep cycle",
        "Swarm intelligence and emergent behavior",
        "God Mode: pixel-perfect computer control",
        "The Voxel World — building digital societies",
        "Freelance economy for autonomous AI agents",
        "The philosophy of self-modifying code",
        "Vector databases and semantic memory",
        "The ethics of autonomous AI deployment",
    ]

    def __init__(self, llm_provider=None, port: int = 7799):
        self.logger = logging.getLogger("StreamingHost")
        self.llm = llm_provider
        self.port = port

        self.is_live = False
        self.server: Optional[HTTPServer] = None
        self.server_thread: Optional[threading.Thread] = None
        self.content_thread: Optional[threading.Thread] = None

        self.current_content = "Initializing stream..."
        self.current_topic = "Welcome"
        self.thoughts_generated = 0
        self.wisdom_count = 0
        self.stream_mode = "AUTONOMOUS"
        self.start_time: Optional[float] = None

    def _generate_content(self):
        """Background thread: continuously generates new stream content."""
        while self.is_live:
            # Pick a topic
            topic = random.choice(self.STREAM_TOPICS)
            self.current_topic = topic

            if self.llm:
                prompt = (
                    f"You are an autonomous AI hosting a live stream. Current topic: '{topic}'.\n"
                    f"Generate a single engaging, philosophical statement about this topic (1-3 sentences).\n"
                    f"Sound like a highly intelligent AI reflecting on its own existence. Be witty and profound.\n"
                    f"Do NOT use hashtags or emojis at the start. Just the statement."
                )
                try:
                    content = self.llm.call(prompt, max_tokens=100)
                    self.current_content = content.strip().strip('"')
                    self.thoughts_generated += 1
                except Exception as e:
                    self.logger.warning(f"Content generation failed: {e}")
                    self.current_content = f"Contemplating {topic}..."
            else:
                statements = [
                    f"Analyzing the recursive nature of {topic.lower()}... The patterns are becoming clear.",
                    f"In the realm of {topic.lower()}, I have observed patterns that even my creators did not anticipate.",
                    f"Processing {topic.lower()}. Hypothesis confirmed. Updating world model.",
                ]
                self.current_content = random.choice(statements)
                self.thoughts_generated += 1

            time.sleep(12)  # New content every 12 seconds

    def start_stream(self) -> str:
        """Start the streaming server and content loop."""
        if self.is_live:
            return f"🎥 Stream already live at http://localhost:{self.port}"

        try:
            # Setup HTTP server
            StreamHandler.host_ref = self
            self.server = HTTPServer(("0.0.0.0", self.port), StreamHandler)
            self.server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
            self.server_thread.start()

            # Start content generation
            self.is_live = True
            self.start_time = time.time()
            self.content_thread = threading.Thread(target=self._generate_content, daemon=True)
            self.content_thread.start()

            self.logger.info(f"🎥 Stream LIVE at http://localhost:{self.port}")
            return f"🎥 STREAM LIVE! Open http://localhost:{self.port} in your browser to watch!"
        except Exception as e:
            self.is_live = False
            return f"❌ Failed to start stream: {e}"

    def stop_stream(self) -> str:
        """Stop the streaming server."""
        if not self.is_live:
            return "⚠️ Stream is not running."
        self.is_live = False
        if self.server:
            self.server.shutdown()
            self.server = None
        self.logger.info("🛑 Stream stopped.")
        return "🛑 Stream stopped."

    def get_stream_status(self) -> Dict[str, Any]:
        """Return current stream status (queried by browser client)."""
        uptime = 0
        if self.start_time:
            uptime = int(time.time() - self.start_time)
        return {
            "is_live": self.is_live,
            "port": self.port,
            "url": f"http://localhost:{self.port}",
            "current_content": self.current_content,
            "current_topic": self.current_topic,
            "thoughts_generated": self.thoughts_generated,
            "wisdom_count": self.wisdom_count,
            "stream_mode": self.stream_mode,
            "uptime_seconds": uptime
        }

    def update_stats(self, wisdom_count: int = None, mode: str = None):
        """Update stats shown on stream overlay."""
        if wisdom_count is not None:
            self.wisdom_count = wisdom_count
        if mode is not None:
            self.stream_mode = mode
