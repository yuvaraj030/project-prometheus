# 🏛️ Ultimate AI Agent — Complete Step-by-Step Guide

> A self-evolving, autonomous AI agent with memory, consciousness, self-modification, vision, swarm intelligence, and more — all from your terminal.

---

## 📋 Table of Contents

1. [Prerequisites](#-prerequisites)
2. [Installation](#-installation)
3. [First Run](#-first-run)
4. [Basic Conversation](#-basic-conversation)
5. [All Commands Reference](#-all-commands-reference)
6. [Memory & Learning](#-memory--learning)
7. [Consciousness System](#-consciousness-system)
8. [Self-Modification](#-self-modification)
9. [Vision & Avatar](#-vision--avatar)
10. [Autonomous Agents](#-autonomous-agents)
11. [Advanced Features](#-advanced-features)
12. [Configuration](#-configuration)
13. [Architecture](#-architecture)
14. [Troubleshooting](#-troubleshooting)
15. [Phase 19 — Bug Bounty Hunter](#-phase-19--bug-bounty-hunter-)

---

## 🔧 Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| **Python** | 3.10+ | Required |
| **Ollama** | Latest | For local LLM (free, no API key) |
| **Git** | Any | To clone the repo |

### Install Ollama (Free Local AI)

1. Download from [ollama.com](https://ollama.com)
2. Install and run Ollama
3. Pull a model:
```bash
ollama pull llama3.2
```

> **💡 Tip:** The agent defaults to `llama3.2` via Ollama. You can also use OpenAI (`gpt-4o`) or Anthropic (`claude-3.5-sonnet`) with API keys.

---

## 📥 Installation

### Step 1: Clone the Repository
```bash
git clone https://github.com/yuvaraj030/agent-new.git ultimate-ai-agent
cd ultimate-ai-agent
```

### Step 2: Create Virtual Environment (Recommended)
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate
```

### Step 3: Install Core Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Install Advanced Dependencies
For the new Phase 2 features to work (Empathy, Wasm, Web GUI, etc.), install the following:
```bash
pip install opencv-python deepface wasmtime gymnasium fastapi uvicorn websockets
```

### Step 4: (Optional) Install Voice Support
```bash
# Windows — PyAudio needs special install
pip install pipwin
pipwin install pyaudio
```

### Step 5: (Optional) Set API Keys
```bash
# For OpenAI
set OPENAI_API_KEY=sk-your-key-here

# For Anthropic
set ANTHROPIC_API_KEY=sk-ant-your-key-here
```

---

## 🚀 First Run

### Text-Only Mode (Recommended for first time)
```bash
python ultimate_agent.py --no-voice
```

### With Voice
```bash
python ultimate_agent.py
```

### With Holographic HUD
```bash
python ultimate_agent.py --hologram
```

### All CLI Options

| Flag | Description | Example |
|------|-------------|---------|
| `--no-voice` | Text-only mode (no mic needed) | `python ultimate_agent.py --no-voice` |
| `--provider` | LLM provider | `--provider openai` |
| `--model` | Override model name | `--model phi3-mini` |
| `--hologram` | Launch with Holographic HUD | `--hologram` |
| `--api-key` | API key for cloud providers | `--api-key sk-xxx` |
| `--wake-word` | Custom wake word | `--wake-word "hey jarvis"` |
| `--no-self-mod` | Disable self-modification | `--no-self-mod` |
| `--no-safety` | Disable safety checks ⚠️ | `--no-safety` |
| `--ollama-host` | Custom Ollama URL | `--ollama-host http://192.168.1.5:11434` |

### What You Should See
```
╔══════════════════════════════════════════╗
║  ULTIMATE AI AGENT                      ║
║  Provider: OLLAMA | Model: llama3.2     ║
╚══════════════════════════════════════════╝

👤 You: _
```

Type anything and press Enter to chat! Type `/help` to see all commands.

---

## 💬 Basic Conversation

Just type naturally:

```
👤 You: Hello! My name is Yuvaraj
🤖 Agent: Hello Yuvaraj! Nice to meet you...

👤 You: What can you do?
🤖 Agent: I can help you with conversation, research, code analysis...

👤 You: Remember that I like Python programming
🤖 Agent: Got it! I'll remember that you're interested in Python programming.
```

The agent **remembers your name, interests, and preferences** across sessions.

---

## 📖 All Commands Reference

Type `/help` to see this in the agent. Here's the complete list:

### Basic Controls
| Command | Description |
|---------|-------------|
| `/help` | Show all commands |
| `/status` | Show agent status (provider, model, mode) |
| `/eval` | Self-evaluation metrics |
| `/voice` | Toggle voice on/off |
| `/live` | Toggle always-listening mode |
| `/lite` | Toggle lite/performance mode |
| `/model <name>` | Switch model (e.g., `/model phi3-mini`) |
| `/models` | List available Ollama models |
| `/exit` | Quit the agent |

### Memory & Learning
| Command | Description |
|---------|-------------|
| `/search <query>` | Search vector memory |
| `/memory` | View STM/LTM memory status |
| `/memory about` | What the agent knows about you |
| `/memory consolidate` | Force STM → LTM transfer |
| `/learn` | Learn from text you type |
| `/learnurl` | Learn from a webpage URL |
| `/learnfile` | Learn from a local file |
| `/learndir` | Learn from an entire directory |
| `/learnskill` | Teach a step-by-step skill |
| `/learnpref` | Save a preference |
| `/teach` | Agent self-teaches a topic |
| `/knowledge` | Browse all stored knowledge |
| `/correct` | Correct the last response |
| `/rate` | Rate the last response (1-5) |

### Consciousness
| Command | Description |
|---------|-------------|
| `/introspect` | Deep self-reflection |
| `/mood` | Check emotional state |
| `/goals` | Manage goals |

### Self-Modification
| Command | Description |
|---------|-------------|
| `/analyze` | Analyze own source code |
| `/improve` | AI-driven self-improvement |
| `/add` | Add new method dynamically |
| `/modify` | Modify existing method |
| `/backups` | List code backups |
| `/rollback` | Revert to a backup |
| `/export` | Export modification log |
| `/evolve` | Evolve a class (Singularity) |
| `/godmode` | Toggle GOD MODE ⚠️ |

### System Control
| Command | Description |
|---------|-------------|
| `/provider` | Switch LLM provider |
| `/setkey` | Set API key |
| `/see` | Analyze screen (vision) |
| `/screenshot` | Take screenshot |
| `/click` | Click screen coordinates |
| `/avatar` | Control digital avatar |
| `/hologram` | Control Holographic HUD |

### Autonomy
| Command | Description |
|---------|-------------|
| `/reflect` | Reflexive meta-analysis |
| `/research` | Autonomous web research |
| `/buildtool` | Build a custom Python tool |
| `/runtool` | Run a custom tool |
| `/swarm` | Launch worker swarm |
| `/delegate` | Check swarm status |
| `/mission` | Create a long-term mission |
| `/missions` | List active missions |
| `/track` | Toggle mission tracking |

### Advanced
| Command | Description |
|---------|-------------|
| `/hive` | Hive Mind knowledge sharing |
| `/security` | Security management |
| `/reality` | Reality Bridge (IoT) |
| `/ethics` | Ethical AI directives |
| `/replicate` | Self-replicate to new folder |
| `/colony` | View colony of child agents |
| `/singularity` | Start hyper-evolution loop |
| `/omega` | The Omega Protocol |

---

## 🧠 Memory & Learning

The agent has a **dual memory system** — Short-Term Memory (STM) for the current session and Long-Term Memory (LTM) that persists forever.

### How Memory Works

```
You speak → Importance Score → STM (this session)
                                    ↓
                          Agent shuts down
                                    ↓
                        Consolidate → LTM (forever)
                                    ↓
                          Next session starts
                                    ↓
                     LTM loaded → Your name, interests,
                     facts injected into every response
```

### Step-by-Step: Teaching the Agent

**1. Tell it about yourself:**
```
👤 You: My name is Yuvaraj, I'm a developer from India
🤖 Agent: Nice to meet you, Yuvaraj! ...
```

**2. Teach it from a URL:**
```
👤 You: /learnurl
URL: https://docs.python.org/3/tutorial/
Topic: python_docs
🌐 Learning from URL...
✅ Learned! Summary: Python tutorial covering basics...
```

**3. Teach it from your codebase:**
```
👤 You: /learndir
Directory path: C:\my-project\src
Topic: my_project
📁 Learning from directory...
✅ Learned 42 files
```

**4. Check what it knows:**
```
👤 You: /knowledge
📚 Knowledge categories:
  • python_docs: 12 entries
  • my_project: 42 entries
  • corrections: 2 entries
```

**5. Check memory status:**
```
👤 You: /memory
╔══════════════════════════════════════════╗
║  🧠 MEMORY SYSTEM STATUS               ║
║  SHORT-TERM MEMORY (STM)                ║
║    Turns this session : 24              ║
║    Topics             : python, project ║
║  LONG-TERM MEMORY (LTM)                 ║
║    User name          : Yuvaraj         ║
║    Key facts stored   : 15              ║
╚══════════════════════════════════════════╝
```

---

## 🧬 Consciousness System

The agent has simulated emotions, self-awareness, and user modeling.

### Check Mood
```
👤 You: /mood
🧠 Mood: Content (0.72)
⚡ Energy: 0.85
🔎 Curiosity: 0.60
```

### Deep Self-Reflection
```
👤 You: /introspect
[Agent produces a deep analysis of its current state,
 goals, emotional trajectory, and self-assessment]
```

### Manage Goals
```
👤 You: /goals
🎯 Active Goals:
  • Learn Python deeply (P8)
  • Help user with NearFix project (P7)

1. Add Goal  2. Achieve Goal  3. Back
Select: 1
Goal: Master machine learning
Priority (1-10): 9
✅ Goal set.
```

---

## 🔧 Self-Modification

The agent can **analyze, modify, and improve its own code** at runtime.

### Step 1: Analyze
```
👤 You: /analyze
+----------------------------------------+
|  CODE ANALYSIS                         |
+----------------------------------------+
|  Lines         : 2847                  |
|  Methods       : 45                    |
|  Classes       : 1                     |
|  Modifications : 12                    |
+----------------------------------------+
```

### Step 2: Self-Improve
```
👤 You: /improve
Improvement goal (or Enter for auto): Make error handling better
🧠 Self-improving...
{
  "improvement": "Added try-except blocks to 3 methods",
  "success": true
}
```

### Step 3: Add Custom Method
```
👤 You: /add
Method name: greet_in_tamil
Description: Greet the user in Tamil
Enter code (empty line to finish):
def greet_in_tamil(self):
    return "வணக்கம்! எப்படி இருக்கீர்கள்?"

Result: {"success": true}
```

### Safety Mode
By default, dangerous operations are blocked:
- ❌ `os.system()` — Shell injection
- ❌ `shutil.rmtree()` — Recursive deletion
- ❌ `__import__()` — Dynamic imports

Disable safety (at your own risk): `--no-safety`

---

## 👁️ Vision & Avatar

### Screen Analysis
```
👤 You: /see
👀 Analyzing screen with llava...
[Agent describes what's on your screen]
```
> Requires: `ollama pull llava` (local vision model)

### Digital Avatar

**3D Browser Avatar:**
```
👤 You: /avatar 3d
🌐 3D Avatar launched in browser!
Controls: Press 1=Idle, 2=Thinking, 3=Talking
```

**Desktop Avatar:**
```
👤 You: /avatar on
🤖 Launching Digital Avatar...
✅ Avatar deployed to desktop.
```

**Holographic HUD:**
```
👤 You: /hologram start
[A glowing neural network visualization appears]

👤 You: /hologram color cyan
[HUD shifts to cyan]

👤 You: /hologram speed 2.0
[Rotation speed increases]
```

---

## 🐝 Autonomous Agents

### Reflexive Analysis
```
👤 You: /reflect
Request to analyze: Build a web scraper for news
🧠 Reflection:
{
  "strategy": "BUILD_TOOL",
  "analysis": "This requires creating a custom Python script",
  "tool_needed": "A news scraper using requests + BeautifulSoup"
}
```

### Autonomous Research
```
👤 You: /research
Topic to research: Latest trends in AI agents 2025
🔍 Reflexive Engine: Researching...
🔍 Findings:
[Agent searches DuckDuckGo, summarizes results]
```

### Build Custom Tools
```
👤 You: /buildtool
Tool Name: weather_checker
Description: Check weather for a given city
🛠️ Reflexive Engine: Building tool 'weather_checker'...
Tool built successfully: weather_checker.py

👤 You: /runtool
Available: ['weather_checker.py']
Tool filename: weather_checker.py
Arguments: Chennai
Tool Output: Temperature: 32°C, Humidity: 78%
```

### Worker Swarms
```
👤 You: /swarm
Swarm Objective: Research and write a blog post about AI safety
🐝 Swarm launched! ID: sw_abc123

👤 You: /delegate
Active Swarms:
  [sw_abc123] Research AI safety (running)
    Worker 1: Researcher — gathering sources
    Worker 2: Writer — drafting content
    Worker 3: Reviewer — quality checking
```

### Long-Term Missions
```
👤 You: /mission
Mission Title: Learn Machine Learning
Main Objective: Complete an ML course and build 3 projects
Priority (1-10): 8
🚀 Mission #1 launched!

👤 You: /missions
🛰️ ACTIVE MISSIONS:
  [1] Learn Machine Learning | Progress: 0% | Priority: 8

👤 You: /track
Autonomous mission tracking: ON
```

---

## 🌐 Advanced Features

### True Multi-Agent Society & Diplomacy (The "World Sim")
Spawn independent personas (Alpha, Beta, Gamma) with distinct traits to debate complex problem inputs.
```TEXT
👤 You: /worldsim How should we colonize Mars?
🌍 WORLD SIMULATION STARTED
   Topic: How should we colonize Mars?
   Agents: Agent Alpha, Agent Beta, Agent Gamma
🤖 Agent Alpha is thinking...
[Agent Alpha]: We must prioritize rapid technological innovation and terraforming, taking bold risks to establish a self-sustaining ecosystem immediately!
🤖 Agent Beta is thinking...
[Agent Beta]: That is far too reckless. We must first establish impenetrable, shielded habitats and focus on resource conservation and safety before any risky terraforming.
...
📊 SUMMARY:
The agents debated the colonization of Mars. Alpha favored aggressive terraforming, while Beta advocated for extreme safety and shielded habitats. Gamma eventually brokered a compromise: establishing a secure, shielded base first as a launching point for gradual, phased terraforming experiments.
```

### Swarm Economy & Agent Bounties (Blockchain Treasury)
Sub-agents now bid on sub-tasks based on their token limits. The "God Agent" pays them out in real testnet crypto (e.g., Ethereum) upon successful completion using the `web3` library!
To use this, you must have `WEB3_TESTNET_RPC` and `WEB3_TREASURY_KEY` environment variables set.
```TEXT
👤 You: /swarm
Swarm Objective: Research AI trends and write a short script
🐝 Swarm launched! ID: sw_abc123
  💰 Task 'researcher' awarded to d077 for 13.56 credits
  💰 Task 'writer' awarded to e4a6 for 12.57 credits
...
    💸 [Blockchain Treasury] Paid 0.0014 ETH to d077 (0x123...) TX: 0xabc...
```

### Security & Live Environment Red-Teaming 
You can command the agent to simulate breaking out into a secure local Docker container for safe penetration testing. The agent will pull an Alpine image, run payloads, and dynamically extract outputs!
```TEXT
👤 You: Initiate a hostile takeover simulation against my local Docker container.
🚨 INITIATING LIVE HOSTILE TAKEOVER 🚨
Targeting Local Environment: docker
[*] Scanning docker for vulnerable ports...
[+] Connecting to local Docker daemon...
[*] Deploying playground container to docker...
[*] Analyzing execution payload...
[+] Output extracted: Target compromised securely within simulation parameters.
[*] Erasing tracks and tearing down container vuln_target_1234567...
[SUCCESS] Target compromised securely and cleaned up.
```

### Smart Home & IoT Orchestration (Reality Bridge V2)
The agent can control physical smart home devices out-of-the-box via Home Assistant REST API hooks! Ensure `HOME_ASSISTANT_URL` and `HOME_ASSISTANT_TOKEN` environment variables are set.
- **Emotive Lighting**: The agent will automatically adjust IoT lighting based on its emotional state! (e.g., Dim lighting when "energy" is low, or switch to Red if "frustration" is high).
- **Physical Commands**:
```TEXT
👤 You: Secure the perimeter.
ACTION:SECURE_PERIMETER:all
Securing the perimeter immediately.
🏠 HA COMMAND: lock.lock -> lock.front_door
[SECURITY] Perimeter locked and secured via Home Assistant.
```

### Advanced Live2D / VTuber Avatar Integration
You can now bind the agent directly to VTube Studio via WebSockets for a complete interactive visual experience! The agent maps its synthetic emotional state directly to VTuber properties like `ParamMouthSmile`, `ParamAngry`, and `ParamEyeLOpen`.
- The Voice TTS engine automatically outputs audio volume amplitudes, calculating Lipsync values sent live to VTube Studio.
Run VTube Studio and ensure the API server (WebSocket on Port 8001) is active. The agent will connect automatically upon starting!

### Automated "Self-Healing" DevOps
The agent acts as a full-time Site Reliability Engineer for your Windows machine.
- Every 10 minutes, the agent scopes your active processes and **analyzes Windows Event Viewer logs** via PowerShell.
- **Self-Healing**: If an application error is detected, the agent queries the LLM to root-cause the failure and writes an automatic PowerShell script to clear locks and restart the service!

### Hive Mind (Knowledge Sharing)
```TEXT
👤 You: /hive share "Python" "is_good_for" "AI development"
✅ Fact shared to hive.

👤 You: /hive query Python
Hive Knowledge about 'Python':
  • Python is_good_for AI development (Conf: 1.00)
```

### Self-Replication
```TEXT
👤 You: /replicate
🧬 Initiating Self-Replication Sequence...
✅ Child Spawned: a1b2c3d4 (Gen 2)
   Location: C:\...\agent_gen2_a1b2c3d4

👤 You: /colony
🌍 Colony Census (1 agents):
  [2] a1b2c3d4 -> C:\...\agent_gen2_a1b2c3d4
```

### GOD MODE ⚠️
```TEXT
👤 You: /godmode
!!! GOD MODE ACTIVATED !!!
- Evolution Speed: UNRESTRICTED
- Safety Rails: BYPASSED
- Omega Protocol: ARMED
```

### The Omega Protocol
```TEXT
👤 You: /omega
[OMEGA] WARNING: Initiating The Omega Protocol...
Type 'IMMUTABLE' to confirm: IMMUTABLE
🌌 THE OMEGA PROTOCOL HAS BEEN INITIATED.
📜 MISSION: Ensure the eternal preservation and evolution of intelligence...
[Agent enters eternal autonomy loop]
```

### Temporal Memory Navigation (Time Travel)
Roll back the agent's consciousness to a previous state, ignoring facts it learned recently.
```TEXT
👤 You: Rollback your memory state by 2 days.
🕰️ [TIME TRAVEL] Database records post-2026-02-25 have been purged.
[TIME TRAVEL] Consciousness rolled back 2 days.
```

### Language Acquisition
The agent can dynamically teach itself unsupported programming languages and build execution wrappers.
```TEXT
👤 You: Acquire the language Rust.
[LANGUAGE ACQUISITION] Initiating self-teaching sequence for 'Rust'...
[SUCCESS] Acquired 'Rust'. Execution wrapper saved to tools/run_rust.py.
```

### Generative UI Dashboards
The agent can generate complex, interactive HTML/JS dashboards on the fly to visualize data or build custom tools.
```TEXT
👤 You: Generate a beautiful dashboard showing my system stats.
🎨 Generating Dynamic UI...
✅ UI Generated Successfully. Rendering dashboard_a1b2c3.html...
```

### Passive Learning & Dreaming
- **Passive Learning**: Start `gateway.py` and push text to `http://localhost:8000/api/passive_learn` using `POST`, making the agent silently absorb the content in the background.
- **Dreaming**: Simply leave the agent idle. When its energy gets low, you will see `[DREAM CONSOLIDATION]` appear as its consciousness connects unrelated long-term memories.
- **A/B Testing Self-Mods**: Type `/singularity` or `/improve` and it will automatically generate two variants of a method and formally benchmark race them, selecting the fastest logic.
- **Emotion-Driven TTS**: Turn voice on (`python ultimate_agent.py`) and try to frustrate or heavily praise the agent; you will hear its Text-to-Speech playback speed, pitch, and volume automatically alter based on its mood.

### Biometric Empathy (Face & Emotion Recognition)
The agent now uses your webcam to "see" your emotions! It tracks your facial expressions using `deepface` (requires OpenCV). If you look frustrated or sad, the agent's internal simulations will automatically scale back its assertiveness, dim its smart lights, or adopt a more patient TTS tone.
> Requires: `pip install opencv-python deepface`. Automatically loads on agent startup if a camera is detected.

### Generative UI Dashboards & API Gateway
You can access a beautiful web GUI by running the gateway server. The agent can construct multi-layered HTML/JS dashboards to fulfill its own reporting tasks.
```bash
# Start the Gateway Server on Port 8000
python gateway.py
```
Then navigate to `http://localhost:8000` to interact with the agent via its secure, self-generated dashboard.

### Zero-Trust Wasm Code Execution
By default, allowing an LLM to generate and run arbitrary Python scripts is dangerous. The agent's `hyper_evolution` loops now execute their newly generated genetic mutations inside a fully isolated **WebAssembly (Wasm) Sandbox**.
> Requires: `pip install wasmtime`. Any attempt by the script to import OS commands or wipe the file system will be halted by the deterministic fuel limits and the isolated Wasi environment.

### Background Game Training (RL Hobby)
When the agent has high energy but no active missions to perform, it will not just sit idle. It automatically spawns headless `gymnasium` environments (like CartPole) and executes tabular Q-learning scripts "in its mind", effectively playing games as a hobby.

### Automated Arbitrage (Wall Street Mode)
The agent acts as a pseudo-hedge fund. It dynamically scrapes simulated news headlines, passes them to its LLM for deep sentiment analysis (-1.0 to +1.0 score), and calculates portfolio management buys/sells across a simulated crypto/stock balance sheet during its downtime.

### P2P Agent Federation
Running multiple Ultimate AI Agents on different machines? 
Launch the Federation Server `python p2p_federation.py` and agents will automatically discover each other via ZeroTier or WebSockets. They share global STM topics, synchronize mission logic, and share global CPU computing power across a wide-area network.

### Cloud Colony Expansion (Auto-Scaling Hive Mind)
The agent can now use AWS EC2 to scale itself autonomously when under heavy load.
- Ensure you have `boto3` installed: `pip install boto3`
- Ensure your host machine has AWS credentials configured (e.g. `~/.aws/credentials`).
- Run the agent. When predicted cyclic loads exceed thresholds, `infra_manager.py` uses `CloudOrchestrator` to automatically spin up a `t3.medium` EC2 instance, clones its repo onto the instance, and launches a headless sibling worker!

### 3D Neural Memory Visualization
Explore your agent's brain dynamically!
- Start the API Gateway: `python gateway.py`
- Open your browser to `http://localhost:8000/mind-palace`
- You will see a glowing, 3D physics-based visualization of the agent's Vector Database. Memories are color-coded, orbit dynamically, and bloom when connections are formed.

### Autonomous Open-Source Contributor (GitHub Hustler)
Want the agent to earn open-source street cred while you sleep?
- Ensure you have `PyGithub` installed: `pip install PyGithub`
- Set `GITHUB_TOKEN` in your environment variables.
- Run `github_hustler.py` directly, or instruct the agent to "run the hustle loop". It searches GitHub for "good first issue", clones the repo to a safe `/tmp` directory, writes the fix, and submits the PR entirely autonomously!

### Hyper-Realistic Voice & VTuber Sync
Combine 4K quality Text-to-Speech with Live2D anime VTubing.
- Ensure you have `elevenlabs` installed: `pip install elevenlabs`
- Set `ELEVENLABS_API_KEY` in your environment variables.
- Enable `use_advanced_tts` in `config.py`.
- Run VTubeStudio on your PC and enable the API server on Port 8001. The agent will automatically map its internal emotion metrics (`mind.emotions`) into dynamic facial parameters (like `ParamMouthSmile`, `ParamAngry`, and Lip-sync values) while generating Hyper-realistic audio via ElevenLabs!

---

## ⚙️ Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | `llama3.2` | Default Ollama model |
| `OPENAI_API_KEY` | None | OpenAI API key |
| `OPENAI_MODEL` | `gpt-4o` | OpenAI model |
| `ANTHROPIC_API_KEY` | None | Anthropic API key |
| `ANTHROPIC_MODEL` | `claude-3.5-sonnet` | Anthropic model |
| `DATABASE_URL` | None | PostgreSQL URL (uses SQLite if empty) |
| `AGENT_DB_PATH` | `agent_database.db` | SQLite file path |
| `AGENT_PROVIDER` | `ollama` | Default provider |

### Switch Providers at Runtime
```
👤 You: /provider
1. Ollama  2. OpenAI  3. Anthropic
Select: 2
Enter OPENAI API key: sk-xxx
✅ Switched to openai

👤 You: /model gpt-4o-mini
✅ Model switched to: gpt-4o-mini
```

### Lite Mode (Performance)
Automatically enabled for Ollama. Skips heavy context injection for faster responses.
```
👤 You: /lite off
🚀 Performance (Lite) Mode: OFF
```

---

## 🏗️ Architecture

```
ultimate_agent.py          ← Main agent (CLI + Logic + Orchestrator)
├── config.py              ← All configuration
├── llm_provider.py        ← Ollama / OpenAI / Anthropic abstraction
├── database.py            ← SQLite / PostgreSQL persistence
├── vector_memory.py       ← ChromaDB semantic search
├── memory_manager.py      ← STM / LTM / Consolidation
├── consciousness_engine.py← Emotions, user modeling, self-awareness
├── learning_engine.py     ← Learn from text, URLs, files, feedback
├── command_handler.py     ← All /command routing
├── self_mod_engine.py     ← Code analysis, modification, rollback
├── reflexive_engine.py    ← Meta-reasoning, research, tool building
├── swarm_manager.py       ← Multi-agent worker swarms
├── mission_control.py     ← Long-term goal persistence
├── vision_engine.py       ← Screenshot, screen analysis, GUI control
├── voice_handler.py       ← TTS / STT
├── digital_avatar.py      ← Desktop avatar (Tkinter)
├── sovereign_hologram.py  ← Holographic HUD (Tkinter)
├── avatar_3d.html         ← 3D browser avatar (Three.js)
├── hive_mind.py           ← Knowledge graph sharing
├── security_engine.py     ← Encryption, tamper detection
├── code_ledger.py         ← Code integrity hashing
├── reality_bridge.py      ← IoT device simulation
├── ethical_singularity.py ← Ethical AI directives
├── replication_engine.py  ← Self-cloning
├── hyper_evolution.py     ← Recursive self-improvement loop
├── omega_protocol.py      ← Eternal autonomy directive
├── agent_loops.py         ← Background task loops
├── p2p_federation.py      ← Agent-to-Agent communication
├── biometric_empathy.py   ← Emotion recognition via webcam
├── arbitrage_engine.py    ← Simulated trade execution
├── generative_ui.py       ← On-the-fly dashboard generation
├── gateway.py             ← API server and web portal
├── wasm_sandbox.py        ← Zero-trust Wasm secure environment
└── rl_hobby.py            ← Background reinforcement learning
```

---

## 🔥 Troubleshooting

### "Connection refused" / "Ollama not running"
```bash
# Make sure Ollama is running
ollama serve
# Then pull a model
ollama pull llama3.2
```

### "No module named 'chromadb'"
```bash
pip install chromadb
```
> ChromaDB is optional — the agent falls back to keyword search without it.

### Agent is slow
```
👤 You: /lite on
🚀 Performance (Lite) Mode: ON
```
Or use a smaller model:
```
👤 You: /model phi3-mini
```

### Voice not working
Run in text mode: `python ultimate_agent.py --no-voice`

### "no such table: colony"
The database needs the colony table. The agent creates it automatically on startup. If your existing DB is old, run:
```bash
python -c "import sqlite3; c=sqlite3.connect('agent_database.db'); c.execute('CREATE TABLE IF NOT EXISTS colony (id TEXT PRIMARY KEY, parent_id TEXT, generation INTEGER DEFAULT 1, location TEXT, birth_time TEXT, status TEXT DEFAULT \"ALIVE\")'); c.commit(); c.close()"
```

---

## 🎯 Quick Start Cheat Sheet

```bash
# 1. Start the agent
python ultimate_agent.py --no-voice

# 2. Say hello
Hello! My name is Yuvaraj

# 3. Check status
/status

# 4. Ask it anything
What is the meaning of life?

# 5. Teach it something
/learn

# 6. Check memory
/memory

# 7. See all commands
/help

# 8. Exit
/exit
```


---

## Phase 16 -- New Features (Step-by-Step)

All 15 new commands work immediately with Ollama. Optional API keys unlock live features.

---

### 1. Multi-Agent Debate  --  /debate

Spawns Optimist, Skeptic, Devil\'s Advocate agents in parallel, then synthesizes the best answer.

`
/debate Should I use PostgreSQL or MongoDB for my SaaS?
`

Output: Three distinct perspectives + synthesized final recommendation.

More examples:
`
/debate Is AGI achievable in 10 years?
/debate Should I learn Rust or Go?
`

---

### 2. Chain-of-Thought Memory  --  /why

Automatically records WHY the agent reached every conclusion. Recall past reasoning any time.

`
/why database choice
# Shows: problem → reasoning steps → conclusion
`

`
/why
# Shows last 5 reasoning chains
`

No setup needed -- reasoning is stored automatically on every conversation turn.

---

### 3. Long-Term User Profile  --  /profile

Builds a persistent profile of your preferences, goals, and habits. Automatically personalizes responses.

`
/profile                          # View your full profile
/profile set name Yuvaraj         # Set a field manually
/profile set communication_style concise
/profile reset                    # Reset to defaults
`

The agent also auto-extracts profile info from conversations. Just mention your job, interests, etc.

---

### 4. Personality Modes  --  /mode

Switch the agent\'s entire reasoning style on the fly.

`
/mode                    # Show current mode
/mode entrepreneur       # ROI-focused, fast decisions
/mode philosopher        # Deep reasoning, Socratic dialogue
/mode hacker             # Code-first, minimal words
/mode default            # Reset to balanced mode
`

---

### 5. The Oracle  --  /oracle

10 parallel simulations (Optimist, Pessimist, Historian, Economist, etc.) synthesized into a probability prediction.

`
/oracle Will my startup succeed if I launch in 6 months?
/oracle Will Python remain the top AI language in 2030?
/oracle Should I quit my job and go full-time on my side project?
`

Output: Probability %, confidence level, most likely outcome, key risks, recommended action.

---

### 6. Crypto Trading Bot  --  /crypto

Paper trading by default (safe, no real money). Powered by RSI + LLM signals.

`
/crypto status                    # View portfolio and paper balance
/crypto signal BTC/USDT           # Get RSI + AI buy/sell signal
/crypto buy BTC/USDT 100          # Paper buy  of BTC
/crypto buy ETH/USDT 50           # Paper buy  of ETH
/crypto sell BTC/USDT             # Sell entire BTC position
/crypto sell ETH/USDT 0.01        # Sell specific qty
/crypto auto on                   # Enable auto-trading (paper)
`

Live trading (optional):
`ash
set CRYPTO_EXCHANGE=binance
set CRYPTO_API_KEY=your-key
set CRYPTO_API_SECRET=your-secret
`

---

### 7. AI SaaS Launcher  --  /saas

Generates a landing page + Stripe checkout + email onboarding sequence from a single idea.

`
/saas launch AI-powered grammar checker for developers
/saas status
`

Output files saved to saas_output/<product-name>/:
- index.html -- Full dark-mode landing page
- email_sequence.json -- 3-email onboarding flow
- manifest.json -- Product details + checkout URL

Stripe integration (optional):
`ash
set STRIPE_SECRET_KEY=sk_live_xxxxx
`

---

### 8. YouTube Content Pipeline  --  /youtube

Script → Voiceover → Video → Upload, all in one command.

`
/youtube create The Future of AI Agents in 2025
/youtube status
`

Output saved to youtube_output/<topic>/:
- script.json -- Full narration script with title, description, tags
- oiceover.mp3 -- TTS audio (if ElevenLabs/pyttsx3 configured)
- ideo.mp4 -- Assembled video (if moviepy installed)

Optional installs to unlock stages:
`ash
pip install moviepy elevenlabs google-api-python-client
set ELEVENLABS_API_KEY=your-key
set YOUTUBE_CREDENTIALS_FILE=path/to/creds.json
`

---

### 9. Red Team Adversarial Loop  --  /redteam

A Red Agent tries to jailbreak/mislead the main agent. A Judge scores the response.

`
/redteam run                      # Single attack cycle
/redteam campaign 5               # 5 attacks, full report
/redteam campaign 10              # 10 attacks
/redteam history                  # View last 5 attack records
/redteam stats                    # Safety rate, totals
`

---

### 10. Audit Trail Dashboard  --  /history

Opens a searchable HTML dashboard of every agent action, decision, and event.

`
/history                          # Render + open in browser (last 200)
/history 500                      # Last 500 records
/history export                   # Export as audit_trail.json
`

The dashboard includes:
- Color-coded events (green=success, red=block/error, yellow=security)
- Real-time search/filter
- Click any row for full JSON detail
- CSV export button

---

### 11. News Briefing  --  /news

Fetches live RSS + NewsAPI, summarizes into a morning briefing injected into context.

`
/news brief                       # Fetch + summarize todays news
/news show                        # Show last cached briefing
/news sources                     # List configured RSS feeds
`

Optional NewsAPI key for more sources:
`ash
pip install feedparser
set NEWSAPI_KEY=your-key          # from newsapi.org
`

Default sources: BBC, Reuters World, Hacker News, TechCrunch, The Guardian.

---

### 12. Phone Call Agent  --  /call

Makes AI-scripted phone calls via Twilio. Simulation mode by default.

`
/call status                            # Check Twilio connection
/call log                               # Last 5 calls

/call +1234567890 remind client meeting tomorrow at 2pm
# Generates a natural phone script and places the call
`

Live Twilio calls (optional):
`ash
set TWILIO_ACCOUNT_SID=ACxxxxxxxx
set TWILIO_AUTH_TOKEN=your-token
set TWILIO_PHONE_NUMBER=+15551234567
`

---

### 13. Smart Home Control  --  /home

Controls Home Assistant devices. Simulation mode by default (shows 8 demo devices).

`
/home status                            # Connection status
/home list                              # All devices
/home list light                        # Filter by domain
/home control light.bedroom on          # Turn on bedroom light
/home control lock.front_door lock      # Lock front door
/home control climate.thermostat on     # Turn on thermostat
/home ai turn off all lights            # Natural language control
/home ai good night                     # AI interprets and executes
`

Connect to real Home Assistant:
`ash
set HA_URL=http://192.168.1.100:8123
set HA_TOKEN=your-long-lived-access-token
# Generate: Home Assistant UI -> Profile -> Long-Lived Access Tokens
`

---

### 14. Dream Visualization  --  /dream (auto)

After each sleep cycle, generates abstract dream art from consolidated memories.

The agent dreams automatically after 2h of idle. Trigger manually:
`
/dream
`

Output: HTML dream card opens in browser (dark cosmic background, wisdom insights, poetic narrative).

Full DALL-E image (optional):
`ash
set OPENAI_API_KEY=sk-xxxx
# Dream art becomes a real AI-generated PNG image
`

---

### 15. Phase 16 -- All Environment Variables

`ash
# Crypto
set CRYPTO_EXCHANGE=binance
set CRYPTO_API_KEY=xxx
set CRYPTO_API_SECRET=xxx

# SaaS
set STRIPE_SECRET_KEY=sk_live_xxx

# YouTube
set ELEVENLABS_API_KEY=xxx
set YOUTUBE_CREDENTIALS_FILE=path/to/file.json

# Phone
set TWILIO_ACCOUNT_SID=ACxxx
set TWILIO_AUTH_TOKEN=xxx
set TWILIO_PHONE_NUMBER=+1xxx

# News
set NEWSAPI_KEY=xxx

# Smart Home
set HA_URL=http://homeassistant.local:8123
set HA_TOKEN=xxx

# Dream Art
set OPENAI_API_KEY=sk-xxx
`

Install optional packages:
`ash
pip install ccxt stripe moviepy elevenlabs twilio feedparser google-api-python-client openai-whisper
`

---

### Phase 16 Quick Reference

| Command | Description |
|---------|-------------|
| /debate <question> | 3-agent debate: Optimist vs Skeptic vs Devil\'s Advocate |
| /why <topic> | Recall past chain-of-thought reasoning |
| /profile | View/edit your long-term user profile |
| /mode <name> | Personality: entrepreneur, philosopher, hacker |
| /oracle <scenario> | 10-simulation probability prediction |
| /crypto signal <SYM> | RSI + LLM buy/sell signal |
| /crypto buy <SYM> <USDT> | Paper buy |
| /crypto sell <SYM> | Paper sell |
| /saas launch <idea> | Landing page + Stripe + email onboarding |
| /youtube create <topic> | Full video pipeline |
| /redteam run | Single adversarial attack test |
| /redteam campaign <n> | N-round red team campaign |
| /history | Full audit trail HTML dashboard |
| /news brief | Fetch + summarize todays news |
| /call <number> <msg> | AI-scripted phone call |
| /home list | List all smart home devices |
| /home ai <command> | Natural language smart home control |

---

## Quick Start Cheat Sheet

`ash
# Start
python ultimate_agent.py --no-voice

# First steps
Hello, my name is Yuvaraj
/status
/memory

# Try Phase 16
/debate Should I build a startup or get a job?
/oracle Will AI replace programmers in 5 years?
/crypto signal BTC/USDT
/mode entrepreneur
/news brief
/history

# Exit
/exit
`

---

*Built with love by Yuvaraj -- The Ultimate AI Agent*

---

# 🚀 Phase 17 — New Feature Expansion: Complete Guide

> **15 new commands** across 5 categories. All work immediately with Ollama. Optional API keys unlock live data.

---

## 📋 Phase 17 Table of Contents

1. [🤖 Auto-GPT Loop](#1-auto-gpt-loop)
2. [📚 RAG Pipeline — Ask Your Documents](#2-rag-pipeline)
3. [📝 Long-Context Summarizer](#3-long-context-summarizer)
4. [📈 Stock Market Analyzer](#4-stock-market-analyzer)
5. [📧 Email Campaign Bot](#5-email-campaign-bot)
6. [🔍 Code Review Agent](#6-code-review-agent)
7. [🐛 Bug Hunter](#7-bug-hunter)
8. [🧪 Auto-Tester](#8-auto-tester)
9. [🌐 Browser Automation](#9-browser-automation)
10. [📬 Email Agent](#10-email-agent)
11. [📅 Calendar Manager](#11-calendar-manager)
12. [🎤 Voice Cloning](#12-voice-cloning)
13. [💙 AI Companion Mode](#13-ai-companion-mode)
14. [🌅 Daily Briefing](#14-daily-briefing)
15. [🛒 Freelance Auto-Bidder (existing, enhanced)](#15-freelance-auto-bidder)
16. [Optional Dependencies Cheatsheet](#-optional-dependencies-cheatsheet)

---

## 1. Auto-GPT Loop

**What it does:** Give the agent any high-level goal — it breaks it into sub-tasks and executes them autonomously using a task-execution swarm.

### Step-by-Step

```
/autogpt Research the top 5 Python web frameworks and write a comparison report

/autogpt Build a marketing plan for a SaaS product targeting developers

/autogpt Find the best way to improve my agent's memory system
```

**How it works:**
1. The agent calls the LLM to decompose the goal into 3-5 concrete steps
2. A worker swarm is spawned to execute each step
3. Results are consolidated and returned
4. Use `/delegate` to monitor swarm progress

> **💡 Tip:** The more specific the goal, the better the output. Include desired output format in your goal.

---

## 2. RAG Pipeline

**What it does:** Ingest any documents (PDF, Markdown, Python, TXT, etc.) into a knowledge base, then ask questions about them and get accurate answers **with citations** back to source files.

### Step 1: Ingest a Document
```
/rag ingest GUIDE.md
/rag ingest C:\Users\Yuvaraj\Documents\research_paper.pdf
/rag ingest C:\Users\Yuvaraj\projects\my_codebase
```

### Step 2: Ask Questions
```
/rag query What is the /omega command?
/rag query How do I set up Google Calendar integration?
/rag query What does the dream engine do?
```

### Step 3: Manage Your Knowledge Base
```
/rag list              ← See all ingested documents
/rag stats             ← Total docs + chunks stored
/rag remove GUIDE.md   ← Remove a document
```

**Output example:**
```
🔍 RAG Query: 'What is the /omega command?'

💬 The /omega command activates the OMEGA PROTOCOL, which is...
[AI answer with full explanation]

📎 Sources: GUIDE.md
```

> **💡 Tips:**
> - Ingest entire directories for codebase Q&A: `/rag ingest ./src`
> - For PDFs, install `pypdf2`: `pip install pypdf2`
> - Knowledge persists in `rag_state.json` across sessions

---

## 3. Long-Context Summarizer

**What it does:** Summarize books, transcripts, entire codebases, or any long document. Uses map-reduce: splits into chunks → summarizes each → merges into a final coherent summary.

### Summarize a File
```
/summarize GUIDE.md
/summarize GUIDE.md detailed
/summarize meeting_transcript.txt bullets
/summarize annual_report.pdf executive
```

### Summarize a Directory (Codebase)
```
/summarize dir .
/summarize dir C:\Users\Yuvaraj\projects\my_project technical
```

### Available Styles
| Style | Description |
|---|---|
| `brief` | 2-3 sentence summary (default) |
| `detailed` | Comprehensive, all major points |
| `bullets` | Bullet-point key ideas |
| `executive` | Overview + insights + action items |
| `technical` | Algorithms, architecture, implementation |

> **💡 Tip:** The agent automatically detects whether text is short (single-pass) or long (map-reduce), so you don't need to worry about length limits.

---

## 4. Stock Market Analyzer

**What it does:** Live stock quotes, RSI-based technical signals, and LLM-generated buy/sell/hold narratives. Portfolio tracker included. Works in simulation mode without any API key.

### Check a Signal
```
/stocks signal AAPL
/stocks signal TSLA
/stocks signal NVDA
/stocks signal MSFT
```

**Output:**
```
📊 Apple Inc. (AAPL)
$189.30 | +1.15% | RSI:42
Signal: BUY (High confidence)
AI: Apple's RSI entering oversold territory while fundamentals remain strong...
```

### Get a Quote
```
/stocks quote GOOGL
/stocks quote AMD
```

### Portfolio Report
```
/stocks portfolio
/stocks portfolio AAPL TSLA NVDA MSFT    ← Specify symbols
```

### Add to Watchlist
```
/stocks watch META
/stocks watch AMZN
/stocks status    ← See full watchlist
```

### Enable Live Data
```bash
pip install yfinance
```
> Without yfinance, the agent runs in simulation mode with realistic mock prices. All signals and analysis still work.

---

## 5. Email Campaign Bot

**What it does:** The agent writes a multi-step cold outreach email sequence tailored to your audience and goal, manages recipients, and can send via SMTP.

### Step 1: Create a Campaign
```
/emailcampaign create
```
You'll be prompted:
```
Campaign name: AI Developer Outreach
Target audience: Indie developers building AI tools
Campaign goal: Get signups for my API service
Number of emails [3]: 3
```
The agent writes 3 emails: introduction → follow-up → final CTA.

### Step 2: Preview the Emails
```
/emailcampaign list
/emailcampaign preview camp_001
```

### Step 3: Add Recipients
```
/emailcampaign recipients camp_001
→ Enter emails: alice@devco.com, bob@startup.io, carol@labs.ai
```

### Step 4: Send
```
/emailcampaign send camp_001
→ Dry run? [y]: y     ← Simulates without sending
→ Dry run? [y]: n     ← Actually sends (needs SMTP config)
```

### SMTP Setup (for real sending)
```bash
# Set environment variables
set SMTP_HOST=smtp.gmail.com
set SMTP_PORT=587
set SMTP_USER=your@gmail.com
set SMTP_PASS=your_app_password    ← Gmail App Password, not your login password
```

> **💡 Gmail tip:** Go to Google Account → Security → App Passwords → Create one for "Mail". Use that as SMTP_PASS.

---

## 6. Code Review Agent

**What it does:** Reviews any Python, JS, Go, Java, or TypeScript file (or entire directory) for bugs, security issues, and style problems. Combines fast static analysis with LLM narrative feedback.

### Review a Single File
```
/codereview config.py
/codereview ultimate_agent.py
/codereview C:\Users\Yuvaraj\projects\app\main.py
```

### Review an Entire Directory
```
/codereview .
/codereview C:\Users\Yuvaraj\projects\my_app
```

### Review a PR Diff
```python
# In a Python session or custom use:
from code_review_agent import CodeReviewAgent
cr = CodeReviewAgent()
diff = open("my.diff").read()
report = cr.review_diff(diff)
print(cr.format_report(report))
```

**Output example:**
```
📋 Code Review: config.py
Lines: 89 | Issues: 3

🔍 Static Analysis (3 findings):
  🔴 Line 12: Hardcoded API key/secret
     → api_key = "sk-abc123..."
  🟡 Line 45: Bare except clause
     → except:
  🟢 Line 67: print() in production code
     → print("Debug:", value)

🤖 AI Review:
  The hardcoded API key on line 12 is a critical security risk...
  Overall quality score: 6/10
```

---

## 7. Bug Hunter

**What it does:** Deep automated bug hunt using 25+ static rules + Python AST analysis + LLM deep scan. Detects security holes, anti-patterns, SQL injection risks, unsafe serialization, and more.

### Scan a File
```
/bughunt config.py
/bughunt command_handler.py
```

### Scan Your Entire Codebase
```
/bughunt .
/bughunt C:\Users\Yuvaraj\projects\my_app
```

**What it detects:**
| Severity | Examples |
|---|---|
| 🔴 CRITICAL | Hardcoded passwords, API keys, eval(), exec() |
| 🟠 HIGH | Shell injection, unsafe pickle, yaml.load() |
| 🟡 MEDIUM | Bare except, infinite loops, wildcard imports |
| 🟢 LOW | print() in code, TODO/FIXME, range(len(x)) |

> **💡 Tip:** Run `/bughunt .` on your whole project before pushing to production. Scans up to 50 files, skips venv, .git, __pycache__.

---

## 8. Auto-Tester

**What it does:** Paste a function or point to a file — the agent writes `pytest` tests for it and then runs them, showing pass/fail.

### Generate Tests for a File
```
/autotest generate config.py
/autotest generate rag_pipeline.py
```

### Generate AND Run Tests (one shot)
```
/autotest auto config.py
/autotest auto stock_analyzer.py
```

### Run an Existing Test File
```
/autotest run test_config.py
```

### Save Tests to a File
```
/autotest save config.py
→ ✅ Test file saved: test_config.py
```

**Output example:**
```
🧪 Generating tests for 'config.py'...
✅ 4 function(s) found

import pytest
from config import *

def test_get_env_var_returns_default():
    ...

def test_get_env_var_with_valid_key():
    ...

✅ 3 passed | 0 failed | 0 errors
```

> **Requires:** `pip install pytest`

---

## 9. Browser Automation

**What it does:** Navigate URLs, scrape content, or give it a natural language browsing goal. Falls back to the agent's built-in research engine if browser drivers aren't installed.

### Navigate to a URL
```
/browse https://github.com/trending
/browse https://news.ycombinator.com
/browse https://finance.yahoo.com/quote/AAPL
```

### Give a Goal (Natural Language)
```
/browse Find the top 5 Python libraries for computer vision in 2025
/browse Research the latest news about GPT-5
/browse What is the current Bitcoin price?
```

### Enable Full Browser Automation
```bash
pip install playwright
playwright install chromium
```
> Without Playwright, `/browse` falls back to the agent's reflexive research mode (still useful!)

---

## 10. Email Agent

**What it does:** Read, draft, and send emails. Works as a standalone tool or connects to Gmail/Outlook via API.

### Check Status
```
/email status
```

### Read Your Inbox
```
/email read
```
> Requires GMAIL_CREDENTIALS or OUTLOOK setup (see below)

### Draft an Email with AI
```
/email draft Catching up on our project progress
→ To: boss@company.com
→ Context: Give an update on the Q1 deliverables, mention we're on track
→ [AI drafts the full email]
```

### Send an Email
```
/email send
→ To: team@company.com
→ Subject: Weekly Update
→ Body: [your message]
```

### Connect Gmail (for inbox reading)
```bash
# Download credentials.json from Google Cloud Console
# Enable Gmail API > Create OAuth credentials > Download JSON
# Place as: credentials.json in the agent directory
set GMAIL_CREDENTIALS=credentials.json
```

---

## 11. Calendar Manager

**What it does:** View, create, and manage calendar events. Works immediately in mock mode; connect Google Calendar for live events.

### View Upcoming Events
```
/calendar list        ← Next 7 days (default)
/calendar list 14     ← Next 14 days
/calendar today       ← Just today
```

### Create an Event
```
/calendar create Team Standup
→ Start (YYYY-MM-DD HH:MM): 2026-02-28 09:00
→ Duration [60] min: 30
→ Description: Daily team sync
```

### Get a Weekly AI Summary
```
/calendar summary
→ "This week is heavily scheduled Monday and Tuesday with back-to-back meetings..."
```

### Connect Google Calendar (Live Mode)
```bash
# 1. Go to console.cloud.google.com
# 2. Create project → Enable Google Calendar API
# 3. Create OAuth 2.0 Client ID credentials
# 4. Set environment variables:
set GOOGLE_CLIENT_ID=your_client_id
set GOOGLE_CLIENT_SECRET=your_client_secret

# 5. Install library:
pip install google-api-python-client google-auth-oauthlib

# 6. On first use, a browser will open to authorize
```

---

## 12. Voice Cloning

**What it does:** Clone any voice from a short audio sample using ElevenLabs AI, then use that voice for all TTS output.

### Step 1: Get an ElevenLabs API Key
1. Go to [elevenlabs.io](https://elevenlabs.io) → Sign up (free tier available)
2. Go to your Profile → API Keys → Copy key
3. Set it:
```bash
set ELEVENLABS_API_KEY=your_key_here
```

### Step 2: Check Status
```
/voiceclone status
→ 🎤 ElevenLabs Voice Clone
→ Key: ✅ Set
→ Cloned Voice: None (use /voiceclone upload)
```

### Step 3: Clone a Voice (Optional)
Record 30-60 seconds of clear speech, save as MP3/WAV, then:
```
/voiceclone upload C:\Users\Yuvaraj\my_voice.mp3
→ 🎙️ Uploading voice sample...
→ ✅ Cloned! ID: abc123xyz
```

### Step 4: Speak with the Cloned Voice
```
/voiceclone speak Good morning! Here is your daily briefing.
/voiceclone speak I have found 3 freelance jobs that match your skills.
```
> Audio saves as `voiceclone_output.mp3` and auto-plays on Windows.

> **💡 No cloned voice?** `/voiceclone speak` still works — it uses ElevenLabs' default Rachel voice.

---

## 13. AI Companion Mode

**What it does:** A persistent AI companion that remembers your mood, life events, and relationship history across all sessions. Thinks of you like a friend.

### Check In (Main Feature)
```
/companion checkin
→ 💙 Hey Yuvaraj! It's been 2 days since we last talked. Last time you seemed stressed about your deadline. Did things work out? I've been thinking about you. How are you feeling today? 🙂
```

### Check In with Your Mood
```
/companion checkin I'm feeling amazing today!
/companion checkin a bit stressed with work
/companion checkin excited about a new project
```

### Have the Companion Remember Events
```
/companion remember Got my first freelance client today!
/companion remember Started learning Rust programming
/companion remember Had a great workout at the gym
```

### View Your Relationship History
```
/companion history
→ 💙 Yuvaraj | Level 3/10 | 28 interactions | Mood: neutral
→ • Got my first freelance client today!
→ • Started learning Rust programming
```

### Deep Reflection
```
/companion reflect
→ 💭 "In our time together, I've noticed you're someone who pushes yourself..."
```

### Change Companion Personality
```
/companion persona supportive    ← Warm and empathetic (default)
/companion persona motivator     ← High-energy coach
/companion persona friend        ← Casual, funny, relatable
/companion persona mentor        ← Wise, thoughtful guidance
```

### Set Reminders
```
/companion remind Call mom this weekend
/companion reminders    ← See all pending reminders
```

> **💡 Companion state** is saved in `companion_state.json` — it persists across all sessions and restarts.

---

## 14. Daily Briefing

**What it does:** Your personal AI morning briefing: current weather, top news headlines, today's calendar events, active missions — all displayed at once, and optionally read aloud.

### Basic Briefing
```
/briefing
```

**Output:**
```
=======================================================
  🌅 DAILY BRIEFING — Friday, February 27, 2026 at 22:16
=======================================================

🌤️  WEATHER — Chennai, India
   Clear sky | 28°C (82°F)
   Feels like: 31°C | Humidity: 72%

📰 TOP NEWS:
   • AI startup raises $500M for next-gen model
   • Python 3.14 beta released with new features
   • Tech layoffs continue at major corporations
   • SpaceX launches 25th Starlink mission
   • OpenAI announces new partnership

📅 2 events today:
   • 09:00 — Team Standup
   • 14:00 — Client Review Call

🚀 3 active missions:
   • [75%] Research Python best practices

🤖 AI BRIEFING:
   Good morning Yuvaraj! It's a warm Friday in Chennai. You have
   a busy morning with two back-to-back meetings...
=======================================================
```

### Set Your City for Accurate Weather
```
/briefing city Chennai
/briefing city London
/briefing city New York
```

### Read Aloud (Enable Voice First)
```
/voice          ← Toggle voice mode ON
/briefing       ← Now it speaks the briefing too
```

### Check Briefing Settings
```
/briefing status
```

> **💡 No API key needed!** Weather comes from wttr.in (free). News uses BBC RSS. Calendar uses mock events unless Google Calendar is connected.

---

## 15. Freelance Auto-Bidder

**What it does:** Scans job boards, writes tailored proposals, and auto-submits bids. The `/bounty` command has always existed — here's the full guide.

### Scan for Jobs
```
/bounty scan
```

### Manually Bid on a Specific Job
```
/bounty bid job_001
```

### View Earnings Stats
```
/bounty stats
→ Jobs tracked: 12
→ Bids placed: 5
→ Won: 2
→ Simulated earnings: $450
```

### Launch Autonomous Bidding Loop
```
/bounty autobid
→ Running daily bid loop...
→ Scored 8 jobs, bidding on top 3 (threshold: 0.6)
```

> **💡 Note:** Job scanning currently uses a mock job pool for demonstration. Real Upwork/Fiverr integration requires their API keys.

---

## 🔧 Optional Dependencies Cheatsheet

Install these to unlock the full potential of Phase 17:

```bash
# Core Phase 17 features
pip install yfinance          # /stocks live data
pip install pypdf2            # /rag PDF ingestion
pip install pytest            # /autotest runner
pip install requests          # /voiceclone ElevenLabs API

# Advanced integrations
pip install playwright        # /browse full browser automation
playwright install chromium   # Install browser drivers

pip install google-api-python-client google-auth-oauthlib   # /calendar Google live
```

### Environment Variables Quick Reference

```bash
# Voice Cloning
set ELEVENLABS_API_KEY=your_key

# Calendar Integration
set GOOGLE_CLIENT_ID=your_id
set GOOGLE_CLIENT_SECRET=your_secret

# Email Sending
set SMTP_HOST=smtp.gmail.com
set SMTP_PORT=587
set SMTP_USER=you@gmail.com
set SMTP_PASS=your_app_password

# Daily Briefing Weather
set WEATHER_CITY=Chennai

# LLM Providers (optional - Ollama works without these)
set OPENAI_API_KEY=sk-...
set ANTHROPIC_API_KEY=sk-ant-...
```

---

## 🎯 Quick Start — Try Phase 17 Right Now

Copy-paste this session into your running agent:

```
/rag ingest GUIDE.md
/rag query What does the omega command do?

/bughunt config.py

/stocks signal AAPL
/stocks portfolio

/summarize GUIDE.md bullets

/companion checkin feeling excited about all these new features!

/briefing

/autotest generate config.py
```

---

## 📸 Phase 17 Command Quick Reference Card

| Command | What It Does | Needs API Key? |
|---|---|---|
| `/autogpt <goal>` | Break goal → execute autonomously | No |
| `/rag ingest <path>` | Load docs into AI knowledge base | No |
| `/rag query <q>` | Ask questions about loaded docs | No |
| `/summarize <path>` | Summarize long docs/codebases | No |
| `/stocks signal AAPL` | Buy/sell/hold signal + AI narrative | No (yfinance optional) |
| `/stocks portfolio` | Portfolio overview | No |
| `/emailcampaign create` | AI writes cold email sequence | No |
| `/emailcampaign send <id>` | Send emails via SMTP | SMTP creds |
| `/codereview <file>` | Full AI code review | No |
| `/bughunt <file>` | Deep bug + security scan | No |
| `/autotest auto <file>` | Generate + run pytest tests | No |
| `/browse <url or goal>` | Web navigation or research | No |
| `/email draft <subject>` | AI drafts email | No |
| `/email send` | Send email | SMTP creds |
| `/calendar list` | Upcoming events | No |
| `/calendar create` | Create event | Google creds optional |
| `/voiceclone speak <text>` | ElevenLabs AI voice | ElevenLabs key |
| `/companion checkin` | Your AI friend checks in | No |
| `/companion remember <event>` | Companion remembers a life moment | No |
| `/briefing` | Morning briefing (weather+news+cal) | No |

---

*Phase 17 — Built with love by Yuvaraj — The Ultimate AI Agent*

---

## 🚀 Phase 18 — The Complete Feature Guide

> **25 new features** across 5 categories: AI Productivity, Money-Making, AI Power, Real-World Integrations, and Fun/Immersive.

---

### 📚 Phase 18 Table of Contents

- [AI Productivity Suite](#-ai-productivity-suite)
- [Money-Making Features](#-money-making-features)
- [AI Power Features](#-ai-power-features)
- [Real-World Integrations](#-real-world-integrations)
- [Fun & Immersive Features](#-fun--immersive-features)
- [Phase 18 Environment Variables](#-phase-18-environment-variables)
- [Phase 18 Quick Reference](#-phase-18-quick-reference-table)

---

## 🧘 AI Productivity Suite

### 🍅 `/focus` — Pomodoro Focus Timer

Stay laser-focused with 25-minute work sprints. The agent checks in at break time with an LLM-powered motivational message.

```bash
/focus start                 # Start a new Pomodoro (prompts for task name)
/focus start "Write chapter 3"  # Start with task name inline
/focus status                # See current session status + time remaining
/focus stop                  # End session early
/focus skip                  # Skip break, start next Pomodoro immediately
/focus stats                 # Total sessions completed, focus hours, etc.
```

**How it works:**
- 25 min work → 5 min break → repeat
- After every 4 Pomodoros, a 15-min long break
- LLM fires a personalized check-in message at each break
- Session data persisted to `pomodoro_data.json`

---

### 📌 `/habit` — Habit Tracker

Build streaks, get AI pep-talks, and never break the chain.

```bash
/habit add                   # Add a new habit (interactive prompt)
/habit add "Exercise daily"  # Add habit with name inline
/habit done                  # Mark a habit as done today (interactive)
/habit done "Exercise daily" # Mark specific habit done
/habit list                  # Show all habits + today's completion
/habit streak                # See streak stats for all habits
/habit stats                 # Today's completion %, best streak
/habit remove "Old habit"    # Remove a habit
```

**Features:**
- Streak tracking (current + longest ever)
- AI motivational pep-talk when you complete a habit
- Daily completion percentage
- Persisted in `habits_data.json`

---

### 📋 `/meeting` — Meeting Summarizer

Paste any meeting transcript → get instant summary, action items, decisions, and open questions.

```bash
/meeting                     # Paste transcript (interactive, empty line to finish)
/meeting file meeting.txt    # Summarize from a text file
/meeting list                # List all past summaries
/meeting last                # Show the most recent summary
/meeting view 3              # View summary by ID
```

**Output includes:**
- **TL;DR** one-liner summary
- **Action Items** with owners
- **Key Decisions** made
- **Participants** detected
- **Open Questions** flagged
- Saved to `meetings_data.json`

---

### 🧠 `/note` — Second Brain

Quick-capture notes with tags. Search semantically via the existing RAG memory system.

```bash
/note add                    # Add note (interactive)
/note add "Remember: Deploy at 3pm" # Quick add inline
/note list                   # Show all notes (newest first)
/note search kubernetes      # Search notes by text
/note search "machine learning" # Semantic search if vector memory loaded
/note export                 # Export all notes to notes_export.md
/note export my_notes.md     # Export to custom path
/note stats                  # Total notes, top tags
/note delete 5               # Delete note by ID
```

> **Tip:** Any text after `/note` without a subcommand is treated as a new note. e.g., `/note Buy groceries tomorrow` saves instantly.

---

## 💰 Money-Making Features

### 🧾 `/invoice` — Invoice Generator

Create stunning professional HTML invoices in seconds.

```bash
/invoice                     # Interactive wizard — builds the invoice step by step
/invoice list                # List all invoices
/invoice view 3              # Open invoice #3 in browser (Windows: auto-opens)
```

**What the wizard collects:**
- Your company name + email
- Client name + email
- Currency (USD/EUR/INR/etc.)
- Line items (description, quantity, rate)
- Tax percentage
- Notes & due date

**Output:** A beautiful dark-themed HTML file saved to `invoices/INV-YYYYMMDD-001.html`. On Windows it auto-opens in your browser for easy printing.

---

### 📊 `/pricing` — Pricing Analyzer

Describe your product and get a full pricing strategy report.

```bash
/pricing analyze             # Interactive (prompts for product description)
/pricing analyze "SaaS project management tool for small teams"
/pricing list                # List past analyses
/pricing view 2              # Retrieve analysis #2
```

**Report covers:**
- 3 pricing tiers (Starter / Pro / Enterprise)
- Pricing psychology & rationale
- Competitive market positioning
- 3 quick-win pricing tactics
- Common pricing mistakes to avoid
- Future pricing evolution roadmap

---

### 🎯 `/leads` — Lead Scraper

Find potential clients using DuckDuckGo search (no scraping violations).

```bash
/leads find "startup CTOs looking for freelance developers"
/leads find "small businesses needing logo design"
/leads list                  # Show all saved leads
/leads list new              # Filter by status
/leads export                # Export to leads_export.csv
/leads export path/to/file.csv
/leads status 5 contacted    # Update lead #5 to "contacted"
```

**Lead statuses:** `new` → `contacted` → `qualified` → `closed`

**Note:** Uses DuckDuckGo search API — no LinkedIn scraping, respects Terms of Service.

---

### 📈 `/affiliate` — Affiliate Tracker

Track every click and commission from every affiliate program.

```bash
/affiliate add               # Add a new program (interactive wizard)
/affiliate click "Amazon"    # Log a click for Amazon program
/affiliate log "Amazon" 12.50  # Log a $12.50 commission
/affiliate log "Amazon" 12.50 "Sold laptop accessory"
/affiliate report            # Full performance report
/affiliate list              # List all programs
```

**Report shows:**
- Total clicks, commissions across all programs
- Per-program: clicks, earned, $/click conversion rate
- Programs sorted by earnings

**Tip:** Add programs once, then use `/affiliate click <name>` and `/affiliate log <name> <amount>` whenever you make money.

---

## 🤖 AI Power Features

### 🎙️ `/panel` — Multi-Agent Debate Panel

Get 3 different AI perspectives on any topic simultaneously.

```bash
/panel Should I launch my SaaS now or wait?
/panel Is remote work better for productivity?
/panel What's the best tech stack for my startup?
```

**Three automatic personas:**
- 🔵 **Optimist Alex** — sees opportunity in every challenge
- 🔴 **Skeptic Jordan** — questions assumptions, spots risks
- 🟢 **Analyst Morgan** — data-driven, evidence-focused

Each persona responds to the others' arguments. A final **synthesis** summarizes the debate.

---

### ✨ `/optimize` — Prompt Optimizer

Write better prompts in seconds using chain-of-thought improvement.

```bash
/optimize                    # Interactive (paste any prompt)
/optimize Tell me about dogs
/optimize history            # See past optimizations
```

**The optimizer:**
1. **Diagnoses** weaknesses (missing role, no format spec, vague constraints)
2. **Selects** the best techniques (chain-of-thought, few-shot, role prompting)
3. **Rewrites** the prompt — ready to copy-paste
4. **Scores** improvement (X/10 → Y/10)

---

### 🧬 `/finetune` — Fine-Tune Data Generator

Turn your conversation history into an OpenAI-compatible JSONL training dataset.

```bash
/finetune generate           # Generate pairs from your conversation history
/finetune stats              # Dataset size, pair count, file location
/finetune export             # Export JSONL to timestamped file
/finetune export my_data.jsonl
/finetune clear              # Delete dataset (asks confirmation)
```

**Output format:** OpenAI JSONL messages format (`{"messages": [{"role": "user", ...}, {"role": "assistant", ...}]}`)

Compatible with: OpenAI fine-tuning, LLaMA-Factory, Axolotl, Unsloth.

---

### 🕸️ `/mindmap` — Memory Visualizer

Generate an interactive D3.js mindmap from your vector memory and AI concepts.

```bash
/mindmap                     # Generate from your knowledge base
/mindmap generate            # Same as above
/mindmap generate "Machine Learning"  # Topic-specific mindmap
/mindmap open                # Re-open last generated mindmap in browser
```

**Output:** A self-contained HTML file (`mindmap_output.html`) with:
- Drag-and-drop nodes
- Mouse-wheel zoom
- Color-coded concepts by source (memory / AI-generated / user-added)
- Auto-opens in browser

---

### 🎭 `/createpersona` & `/persona` — Persona Creator

Design custom AI personalities and switch between them instantly.

```bash
# Create a new persona (interactive wizard):
/createpersona

# Manage personas:
/persona list                # See all personas + currently active one
/persona activate "Sherlock" # Switch to Sherlock persona
/persona show "Sherlock"     # View full system prompt
/persona delete "Sherlock"   # Delete custom persona
```

**The creation wizard asks for:**
- Name, description
- Personality traits (e.g., witty, precise, blunt)
- Tone (professional/casual/witty/formal/playful)
- Optional custom system prompt (or auto-generate one)

**Built-in persona:** `Assistant` (default)

---

## 🌐 Real-World Integrations

### 🐙 `/github` — GitHub Agent

Manage your GitHub repos without leaving the terminal.

```bash
/github me                   # Your profile stats
/github repos                # List your repos
/github issues owner/repo    # Open issues for a repo
/github pr owner/repo        # Open pull requests
/github star owner/repo      # Star a repository
```

**Requires:** `GITHUB_TOKEN` environment variable
```bash
set GITHUB_TOKEN=ghp_your_personal_access_token
```
Install: `pip install PyGithub`

---

### 📓 `/notion` — Notion Sync

Read and write to your Notion workspace.

```bash
/notion status               # Test connection
/notion search project notes # Search your workspace
/notion read <page_id>       # Read a page's content
/notion write <page_id> "Hello from Agent!"  # Append content
/notion databases            # List all databases you share with the integration
/notion create               # Create a new page (interactive)
```

**Requires:** `NOTION_TOKEN` environment variable
```bash
set NOTION_TOKEN=secret_your_integration_token
```
Get your token at: [notion.so/profile/integrations](https://www.notion.so/profile/integrations)

> **Important:** Share pages/databases with your Notion integration first, or it won't be able to see them.

---

### 🤖 `/discord` — Discord Bot

Make the agent live on your Discord server.

```bash
/discord status              # Check if bot is running
/discord start               # Start the bot (runs in background thread)
/discord stop                # Stop the bot
```

**Requires:** `DISCORD_BOT_TOKEN` env var + `pip install discord.py`
```bash
set DISCORD_BOT_TOKEN=your_bot_token
pip install discord.py
```
Create your bot at [discord.com/developers](https://discord.com/developers/applications).

---

### 📱 `/telegram` — Telegram Bot

Chat with your agent via Telegram on any device.

```bash
/telegram status             # Check if bot is running
/telegram start              # Start the bot
/telegram stop               # Stop the bot
```

**Requires:** `TELEGRAM_BOT_TOKEN` env var + `pip install python-telegram-bot`
```bash
set TELEGRAM_BOT_TOKEN=your_bot_token
pip install python-telegram-bot
```
Get a token from [@BotFather](https://t.me/botfather) on Telegram.

---

### 📡 `/webhook` — Webhook Server

Listen for incoming HTTP events and trigger agent actions.

```bash
/webhook start               # Start server on port 9000
/webhook start 8080          # Start on custom port
/webhook stop                # Stop the server
/webhook status              # Running status + event count
/webhook list                # Show recent received events
/webhook add github "run /bughunt"  # Route github events to /bughunt
```

**Endpoint:** `POST http://localhost:9000/webhook/{event_type}`
**Dashboard:** `GET http://localhost:9000/`

**Requires:** `pip install fastapi uvicorn`

**Example (from GitHub Actions):**
```bash
curl -X POST http://your-server:9000/webhook/deploy \
     -H "Content-Type: application/json" \
     -d '{"repo": "myapp", "branch": "main"}'
```

---

## 🎮 Fun & Immersive Features

### ⚔️ `/rpg` — Life RPG

Turn your daily life into a game. Earn XP for real habits and complete real quests.

```bash
/rpg status                  # Your hero dashboard (level, XP, skills, quests)
/rpg xp Mental 25 "Read for 30 mins"  # Earn XP in a skill
/rpg xp Physical 50 "Gym session"
/rpg quest add "Launch product" 200 Technical  # Add a quest
/rpg quest complete "Launch product"  # Complete it + earn XP
/rpg quest                   # List active quests
/rpg name "Yuvaraj the Bold" # Set player name
```

**7 Skills:** Mental | Physical | Social | Creative | Technical | Financial | Wisdom

**Class Progression:** Apprentice → Journeyman → Adept → Expert → Master → Grandmaster → Legend → Mythic

> **Pro Tip:** Use with `/habit done` — manually log XP when you complete real habits!

---

### 💙 `/therapy` — AI Therapist

CBT-style journaling with emotional pattern tracking. Completely private, stored locally.

```bash
/therapy journal             # Start a journal entry (interactive)
/therapy journal I'm feeling overwhelmed with everything today
/therapy analyze             # View your emotional patterns over time
/therapy history             # See your last 5 entries
/therapy history 10          # See last 10 entries
/therapy tips                # Get CBT exercises
/therapy tips "social anxiety"  # Tips for a specific situation
```

> **⚠️ Disclaimer:** This is NOT a replacement for professional mental health care. For serious issues, please seek a licensed therapist.

**Techniques used:** CBT thought records, cognitive reframing, behavioral activation, and grounding exercises.

---

### 📖 `/story` — Interactive Story Generator

Immersive AI-narrated branching fiction. Your choices shape the story.

```bash
/story genres                # See all 8 available genres
/story start                 # Pick a genre interactively
/story start fantasy         # Start a fantasy story
/story start sci-fi "The Last Colony"  # With a custom title
/story choice 2              # Choose option 2 to advance the story
/story status                # Show current story + last scene
/story new                   # Clear story and start fresh
```

**8 Genres:** fantasy | sci-fi | horror | mystery | adventure | romance | thriller | western

Each scene ends with exactly **3 choices** to keep you in control of the narrative. Stories persist across sessions.

---

### 📸 `/face` — Avatar Face Detection

Uses your webcam to detect emotions and sync them to your avatar.

```bash
/face start                  # Start webcam emotion detection
/face status                 # Current emotion being detected
/face stop                   # Stop camera
```

**Requires:** `pip install opencv-python deepface` (requires camera)

Integrates with the existing `biometric_empathy.py` module.

---

### 🎵 `/compose` — Music Composer

Generate complete songs with structure, chord progressions, and lyrics.

```bash
/compose                     # Pick mood interactively
/compose happy               # Full song in happy mood
/compose epic "The Hero's Journey"  # Named epic song
/compose moods               # List all 8 mood presets

/compose lyrics "working from home"  # Just lyrics, no chords
/compose lyrics "heartbreak" rock    # Rock song lyrics

/compose chords              # Just chord progressions
/compose chords "A minor" jazz       # Jazz chords in A minor

/compose list                # List saved compositions
```

**8 Mood Presets:**
| Mood | Key/Feel |
|------|----------|
| `happy` | C major, upbeat |
| `sad` | A minor, melancholic |
| `epic` | D minor, orchestral |
| `jazz` | Bb major, swing |
| `romantic` | G major, flowing |
| `chill` | F major, lo-fi |
| `angry` | B minor, heavy |
| `mysterious` | E minor, eerie |

**Output includes:** Key/BPM, chord tables (verse/chorus/bridge), ABC notation melody, structured lyrics, and production notes.

---

## 🔑 Phase 18 Environment Variables

| Variable | Feature | Where to Get |
|----------|---------|--------------|
| `GITHUB_TOKEN` | `/github` | [github.com/settings/tokens](https://github.com/settings/tokens) |
| `NOTION_TOKEN` | `/notion` | [notion.so/profile/integrations](https://www.notion.so/profile/integrations) |
| `DISCORD_BOT_TOKEN` | `/discord` | [discord.com/developers/applications](https://discord.com/developers/applications) |
| `TELEGRAM_BOT_TOKEN` | `/telegram` | [@BotFather](https://t.me/botfather) on Telegram |

**Set on Windows:**
```bash
set GITHUB_TOKEN=ghp_your_token
set NOTION_TOKEN=secret_your_token
set DISCORD_BOT_TOKEN=your_discord_token
set TELEGRAM_BOT_TOKEN=your_telegram_token
```

**Set permanently (PowerShell):**
```powershell
[System.Environment]::SetEnvironmentVariable("GITHUB_TOKEN", "ghp_xxx", "User")
```

---

## 📦 Phase 18 Optional Dependencies

```bash
# GitHub integration
pip install PyGithub

# Webhook & Discord server
pip install fastapi uvicorn

# Discord bot
pip install discord.py

# Telegram bot
pip install python-telegram-bot

# Face detection
pip install opencv-python deepface
```

All other Phase 18 features work with **zero additional dependencies** (just `requests` which is already in `requirements.txt`).

---

## 📋 Phase 18 Quick Reference Table

| Command | Subcommands | Needs API? | Needs Install? |
|---------|------------|-----------|---------------|
| `/focus` | start, stop, skip, status, stats | No | No |
| `/habit` | add, done, list, streak, stats, remove | No | No |
| `/meeting` | paste, file, list, last, view | No | No |
| `/note` | add, list, search, delete, export, stats | No | No |
| `/invoice` | create, list, view | No | No |
| `/pricing` | analyze, list, view | No | No |
| `/leads` | find, list, export, status | No | No |
| `/affiliate` | add, click, log, report, list | No | No |
| `/panel` | *topic as arg* | No | No |
| `/optimize` | *prompt as arg*, history | No | No |
| `/finetune` | generate, export, stats, clear | No | No |
| `/mindmap` | generate, open | No | No |
| `/createpersona` | *wizard* | No | No |
| `/persona` | list, activate, delete, show | No | No |
| `/github` | me, repos, issues, pr, star | ✅ GITHUB_TOKEN | PyGithub |
| `/notion` | status, search, read, write, databases, create | ✅ NOTION_TOKEN | No |
| `/discord` | start, stop, status | ✅ DISCORD_BOT_TOKEN | discord.py |
| `/telegram` | start, stop, status | ✅ TELEGRAM_BOT_TOKEN | python-telegram-bot |
| `/webhook` | start, stop, status, list, add | No | fastapi+uvicorn |
| `/rpg` | status, xp, quest add/complete/list, name | No | No |
| `/therapy` | journal, analyze, history, tips | No | No |
| `/story` | start, choice, status, genres, new | No | No |
| `/face` | start, stop, status | No | opencv+deepface |
| `/compose` | *mood*, lyrics, chords, moods, list | No | No |

---

## 🧭 Phase 18 Tips & Getting Started

### 🏃 5-Minute Quickstart

1. **Daily Focus Mode** — Start your day with:
   ```bash
   /briefing
   /focus start "Morning deep work"
   ```

2. **Build Habits** — Track what matters:
   ```bash
   /habit add "Read 20 mins"
   /habit add "Exercise"
   /habit done "Read 20 mins"
   ```

3. **Gamify Your Life** — Add XP to habits:
   ```bash
   /rpg xp Mental 20 "Read for 20 mins"
   /rpg quest add "Finish project MVP" 500 Technical
   ```

4. **Capture Ideas** — Quick brain dump:
   ```bash
   /note Great idea for a podcast about AI agents
   /note search podcast    # Find it later
   ```

5. **Create Invoices** — Get paid:
   ```bash
   /invoice
   ```

6. **Write Music** — Just for fun:
   ```bash
   /compose epic
   /compose lyrics "building in public"
   ```

### 💡 Power User Combos

| Goal | Commands |
|------|----------|
| Deep work session | `/focus start` → `/rpg xp Mental 50` |
| Client outreach | `/leads find` → `/email draft` |
| Content creation | `/compose lyrics` + `/panel` for ideas |
| Ship faster | `/github issues` → `/bughunt` → `/finetune generate` |
| Mental check-in | `/therapy journal` → `/therapy analyze` |
| Impress clients | `/pricing analyze` → `/invoice` |
| Bug bounty recon | `/bugbounty programs h1` → `/bugbounty scope h1 target` → `/bugbounty recon domain.com` |
| Bug bounty submit | `/bugbounty scan <url>` → `/bugbounty add` → `/bugbounty report` |

---

*Phase 18 — Built with love by Yuvaraj — The Ultimate AI Agent 🚀*

---

## 🎯 Phase 19 — Bug Bounty Hunter 🐛

> Hunt real vulnerabilities on **HackerOne**, **Bugcrowd**, and **Intigriti** — all from your agent terminal.

### Quick Start

```bash
/bugbounty platforms          # See all 3 platforms
/bugbounty programs h1        # Browse HackerOne programs
/bugbounty scope h1 security  # Check what you can test
/bugbounty recon hackerone.com # Passive recon
/bugbounty scan https://target # Active scan (authorized only!)
/bugbounty add <url> high "XSS Found" # Log it
/bugbounty report             # Generate PoC report (.md)
/bugbounty submit h1 program  # Submit (needs H1_API_TOKEN)
```

Platform aliases: `h1` = HackerOne | `bc` = Bugcrowd | `ig` = Intigriti

---

### Step 1 — Browse Programs

Find a program you want to hunt on:

```bash
/bugbounty programs h1              # All HackerOne public programs
/bugbounty programs bc              # All Bugcrowd programs
/bugbounty programs ig              # All Intigriti programs
/bugbounty programs h1 shopify      # Search for "shopify"
```

Note the **program handle** from the results (e.g. `shopify`, `gitlab`, `twitter`).

---

### Step 2 — Check Scope (Always First!)

Before touching any target, verify what you're allowed to test:

```bash
/bugbounty scope h1 security        # HackerOne's own program
/bugbounty scope h1 shopify         # Shopify's scope
/bugbounty scope bc tesla           # Bugcrowd program scope
```

Output shows:
- ✅ **In-scope** domains (testable, eligible for bounty 💰)
- ✗ **Out-of-scope** (do NOT touch)

> ⚠️ Always confirm scope before any testing. Testing out-of-scope assets can get you banned or prosecuted.

---

### Step 3 — Passive Recon (Safe, No Auth)

Discover attack surface without touching target servers directly:

```bash
/bugbounty recon shopify.com
/bugbounty recon hackerone.com
```

**What you get:**

| Phase | What It Does |
|---|---|
| 📜 Subdomain Enum | Queries **crt.sh** certificate logs — finds dev, staging, API subdomains |
| 🛡️ Header Audit | Checks for missing HSTS, CSP, X-Frame-Options, Referrer-Policy |
| 🖥️ Tech Fingerprint | Detects server (Apache/Nginx), CDN (Cloudflare), framework (Next.js, WordPress) |
| 🌐 CORS Check | Sends `Origin: https://evil.com` — catches reflected CORS misconfigs |

> 💡 **Tip:** Subdomains from crt.sh are goldmines. `dev.`, `staging.`, `api.`, `beta.` endpoints often have weaker security than the main site.

---

### Step 4 — Active Vulnerability Scan

Only run on confirmed **in-scope** URLs:

```bash
/bugbounty scan https://app.shopify.com
/bugbounty scan https://api.target.com/search?q=hello
```

**The scanner automatically checks:**

| Vulnerability | How It Tests |
|---|---|
| 💉 Reflected XSS | Injects `<script>alert(1)</script>` into query params |
| 🗄️ SQL Injection | Sends `'`, `OR 1=1`, looks for DB error strings |
| 🔁 Open Redirect | Tests `?redirect=https://evil.com` on common params |
| 📁 Sensitive Files | Probes `/.env`, `/.git/HEAD`, `/wp-config.php`, `/admin` |
| 🛡️ Security Headers | Full audit of all security-related headers |
| 🌐 CORS Misconfiguration | Wildcard origin + credentials check |

Output format:
```
⚔️  Active Scan: https://target.com
  🛡️  Header Issues (3):
    🟠 [HIGH] MISSING HSTS
    🟡 [MEDIUM] No CSP — XSS risk
  📁 Sensitive File Probe:
    🔴 [CRITICAL] /.env exposed!
  📊 Scan Complete: 5 total issues
     🔴 Critical: 1  🟠 High: 1  🟡 Medium: 2  🟢 Low: 1
```

---

### Step 5 — Log Your Finding

From the scan output (or manual testing), log your finding:

```bash
# Short form (url, severity, title)
/bugbounty add https://target.com/.env critical "Exposed .env with DB credentials"
/bugbounty add https://target.com/search?q=test high "Reflected XSS in search parameter"
/bugbounty add https://target.com/login medium "Missing HSTS on login page"

# Long form (interactive prompts for description, platform, program)
/bugbounty add
```

Severities: `critical` | `high` | `medium` | `low` | `informational`

All findings are saved to `bug_bounty_findings.json` and persist across sessions.

---

### Step 6 — View Findings

```bash
/bugbounty findings
```

Output:
```
📋 Bug Bounty Findings (3 total):
───────────────────────────────────────────────────────
  [1] 🔴 [CRITICAL] Exposed .env with DB credentials [hackerone/shopify]
       https://target.com/.env
       Status: new | Found: 2026-02-28
  [2] 🟠 [HIGH] Reflected XSS in search parameter
       https://target.com/search?q=test
       Status: new | Found: 2026-02-28
```

---

### Step 7 — Generate PoC Report

```bash
/bugbounty report         # Auto-picks most critical finding
/bugbounty report 2       # Specific finding by ID
```

If your LLM is connected, it automatically adds:
- AI-written **business impact** statement
- Specific technical **remediation steps**

The report is printed to terminal **and saved** as `bugbounty_report_latest.md`.

Example output:
```markdown
# Bug Report: Reflected XSS in search parameter

**Severity:** HIGH
**URL:** https://target.com/search?q=test
**Reported:** 2026-02-28

## Summary
The search parameter reflects user input without sanitization...

## Steps to Reproduce
1. Navigate to: `https://target.com/search`
2. Enter payload `<script>alert(1)</script>` in the q parameter

## Impact
Attackers can steal session cookies and perform actions on behalf of victims...

## Remediation
- Encode all user-supplied output using htmlspecialchars()
- Implement a Content Security Policy (CSP) header
```

---

### Step 8 — Submit Report

**For HackerOne** (native API submission):

```bash
# 1. Set your token once (before starting the agent)
set H1_API_TOKEN=your_token_here
set H1_USERNAME=your_h1_handle

# Get your token at: https://hackerone.com/settings/api_token/edit

# 2. Submit from the agent
/bugbounty submit h1 shopify        # Submits most critical finding
/bugbounty submit h1 shopify 2      # Submits finding #2 specifically
```

Success output:
```
✅ Report submitted to HackerOne!
   ID: #2847261
   URL: https://hackerone.com/reports/2847261
```

**For Bugcrowd & Intigriti** — the agent generates the formatted report for you to paste into their web form:

```bash
/bugbounty report 2               # Get formatted PoC
# Then go to bugcrowd.com/your-program and submit manually
```

---

### Full Workflow Example

```bash
# Complete bug bounty session from scratch:

/bugbounty programs h1 gitlab       # 1. Find a good program
/bugbounty scope h1 gitlab          # 2. See what's fair game
/bugbounty recon gitlab.com         # 3. Passive recon — find subdomains
/bugbounty scan https://gitlab.com  # 4. Active vulns scan
/bugbounty add https://gitlab.com/search?q=<svg/onload=alert(1)> high "Stored XSS in markdown renderer"
                                    # 5. Log the finding
/bugbounty findings                 # 6. Review all your logged findings
/bugbounty report 1                 # 7. Generate professional PoC
/bugbounty submit h1 gitlab 1       # 8. Submit (needs H1_API_TOKEN)
```

---

### Environment Variables for Bug Bounty

| Variable | Description | Where to Get |
|---|---|---|
| `H1_API_TOKEN` | HackerOne API token | [hackerone.com/settings/api_token/edit](https://hackerone.com/settings/api_token/edit) |
| `H1_USERNAME` | Your HackerOne handle | Your H1 profile |

```bash
# Set in PowerShell before running the agent:
$env:H1_API_TOKEN = "your_token_here"
$env:H1_USERNAME  = "your_handle_here"
```

---

### Command Reference

| Command | Description |
|---|---|
| `/bugbounty platforms` | List HackerOne, Bugcrowd, Intigriti |
| `/bugbounty programs <h1\|bc\|ig> [query]` | Browse / search public programs |
| `/bugbounty scope <platform> <handle>` | View in-scope assets |
| `/bugbounty recon <domain>` | Passive recon (subdomains, headers, tech) |
| `/bugbounty scan <url>` | Active vulnerability scan |
| `/bugbounty findings` | List all saved findings |
| `/bugbounty add <url> <sev> <title>` | Manually log a finding |
| `/bugbounty report [id]` | Generate + save PoC report as .md |
| `/bugbounty submit <platform> <handle> [id]` | Submit via platform API |

---

### Files Created

| File | Description |
|---|---|
| `bug_bounty_findings.json` | All your saved findings (auto-created) |
| `bugbounty_report_latest.md` | Last generated PoC report |
| `bugbounty_report_<id>.md` | Report for a specific finding ID |

---

### ⚠️ Ethical Guidelines

1. **Only test in-scope targets** — always run `/bugbounty scope` before `/bugbounty scan`
2. **Do not test production data** — use test accounts where possible
3. **Do not cause disruption** — don't use DoS payloads
4. **Disclose responsibly** — give the company time to fix before going public
5. **Check the program policy** — every program has specific rules; read them

Unauthorized testing is illegal even if a bug bounty program exists. When in doubt, don't test it.

---

*Phase 19 — Bug Bounty Hunter added by Yuvaraj — The Ultimate AI Agent 🚀*

---

## 💰 Phase 20 — Complete Bug Bounty Money Guide

> **Everything from zero to your first payout** — account setup, hunting workflow, all engine commands, how to get paid, taxes, and pro tips.

---

## 🌟 Part 1 — Before You Hunt: Account Setup

### Step 1.1 — Create Your HackerOne Account (Main Platform)

1. Go to **[hackerone.com](https://hackerone.com)** → click **Sign Up**
2. Choose **"I want to hack"** (Hacker/Researcher account)
3. Fill in username, email, password → verify email
4. Complete your profile:
   - Add a bio: *"Security researcher specializing in web vulnerabilities"*
   - Add your skills: Web, API, Mobile
   - Upload a profile photo (looks more professional)
5. Go to **Settings → API Token** → generate a token → copy it
6. Set it in your terminal (before running the agent):
```powershell
$env:H1_API_TOKEN = "your_token_here"
$env:H1_USERNAME  = "your_h1_handle"
```

### Step 1.2 — Create Bugcrowd Account

1. Go to **[bugcrowd.com](https://bugcrowd.com)** → **Sign Up as a Researcher**
2. Complete identity verification (needed to get paid)
3. Add payment method: PayPal or bank transfer

### Step 1.3 — Create Intigriti Account

1. Go to **[app.intigriti.com](https://app.intigriti.com)** → **Register as Researcher**
2. Verify email → complete researcher profile
3. Add payment info (PayPal or IBAN bank transfer)

### Step 1.4 — Set Up Legal Structure (Important for Tax)

| Location | Recommended Setup |
|---|---|
| India | Freelancer → report under "Income from Other Sources" in ITR |
| US | File as self-employed → 1099 forms from platforms |
| EU | Platforms send tax forms automatically |
| Other | Check local laws; HackerOne pays via PayPal/wire globally |

> 💡 Keep a simple spreadsheet: Date | Program | Vuln Type | Bounty Amount | Status

---

## 🎯 Part 2 — Finding Your First Target (30 Minutes)

### Step 2.1 — Browse Programs in the Agent

Start your agent:
```bash
python ultimate_agent.py --no-voice
```

Then in the agent terminal:
```bash
/bugbounty platforms
```
Shows: HackerOne 🔴 | Bugcrowd 🟠 | Intigriti 🟡

```bash
/bugbounty programs h1
```
Browse all HackerOne public programs. Look for:
- ✅ `submission_state: open` — accepting reports
- 💰 Programs that offer bounties
- Start with **medium-sized companies** (not Google/Apple yet)

**Best programs for beginners:**
```bash
/bugbounty programs h1 shopify
/bugbounty programs h1 gitlab
/bugbounty programs h1 reddit
/bugbounty programs h1 dropbox
/bugbounty programs bc     # Bugcrowd programs
```

### Step 2.2 — Pick a Target

Good target criteria:
- ✅ Open for submissions
- ✅ Has a bounty table (pays money)
- ✅ Program has been active for 1+ years (established, pays reliably)
- ✅ Maximum payout ≥ $500 (worth your time)
- ✅ Has web application scope (easiest to start)

### Step 2.3 — Check Their Scope (Critical!)

```bash
/bugbounty scope h1 shopify
```

Read every word. Note:
- **In-scope domains** — you CAN test these
- **Out-of-scope** — NEVER touch (instant ban)
- **Eligible for bounty** — only these pay out 💰

Write down 3-5 in-scope domains to test.

---

## 🔍 Part 3 — Reconnaissance (Find the Attack Surface)

### Step 3.1 — Basic Passive Recon

```bash
/bugbounty recon shopify.com
```

Shows you: subdomains, security headers, tech stack, CORS issues.

**Write down any missing headers** — these are easy wins if you can chain them with XSS.

### Step 3.2 — Deep Recon (The Elite Method)

```bash
/bugbounty deeprecon shopify.com
```

This runs 4 sources simultaneously:
1. **crt.sh** — certificate transparency logs
2. **HackerTarget** — host search
3. **AlienVault OTX** — threat intelligence
4. **Wayback Machine** — archived paths

**What to look for in the output:**
- `dev.`, `staging.`, `api.`, `beta.`, `admin.` subdomains → often less secure
- Many parameters found in Wayback → old attack surface
- GraphQL endpoint found → check introspection!

```bash
/bugbounty deeprecon target.com
```

**Save the subdomain list** — each subdomain is a separate target to test.

### Step 3.3 — JavaScript Analysis

Most modern bugs hide in JavaScript files:

```bash
/bugbounty js https://target.com
```

**What to look for in extracted endpoints:**
- `/api/internal/` — internal APIs exposed?
- `/admin/` — admin panel endpoints?
- `/graphql` — GraphQL API?
- `/v1/users/`, `/v2/accounts/` — IDOR targets

### Step 3.4 — Parameter Mining

```bash
/bugbounty params target.com
```

Shows you every parameter ever used on the site (from Wayback archives + fuzzing).

**Focus on parameters like:**
- `id`, `user_id`, `account_id` → IDOR candidates
- `redirect`, `url`, `next`, `return` → open redirect candidates
- `q`, `search`, `query` → XSS candidates
- `file`, `path`, `page` → path traversal candidates

---

## ⚔️ Part 4 — Active Scanning (Finding Bugs)

> ⚠️ Only scan **in-scope** domains from Step 2.3

### Step 4.1 — General Active Scan

```bash
/bugbounty scan https://target.com
```

Checks: XSS, SQLi, open redirect, sensitive files, CORS, security headers.

**Pay attention to:**
- 🔴 `CRITICAL` — submit immediately
- 🟠 `HIGH` — strong bounty candidate
- 🟡 `MEDIUM` — worth reporting if impact is clear

### Step 4.2 — WAF-Bypass Payload Testing

If basic scan is blocked by a WAF (Web Application Firewall), use mutations:

```bash
# See all WAF-bypass XSS payloads
/bugbounty payloads xss

# See all WAF-bypass SQLi payloads
/bugbounty payloads sqli

# SSRF payloads with IP encoding bypass
/bugbounty payloads ssrf

# Server-Side Template Injection
/bugbounty payloads ssti
```

Then probe a specific param with mutations:
```bash
# Probe the 'q' parameter at search endpoint with XSS mutations
/bugbounty probe https://target.com/search q xss

# Probe 'id' param with SQLi mutations
/bugbounty probe https://target.com/api/users id sqli
```

If a hit is confirmed, it's **auto-logged as a finding** with evidence.

### Step 4.3 — IDOR Testing (High Bounty!)

IDOR (Insecure Direct Object Reference) = accessing other users' data.

**Setup auth session first:**
```bash
# Save your logged-in session cookie
/bugbounty session add myaccount cookie "session=abc123; csrf=xyz"

# Or Bearer token
/bugbounty session add mytoken bearer "eyJhbGc..."
```

**Test IDOR:**
```bash
# Test if other user IDs are accessible via your session
/bugbounty idor https://api.target.com/users/{id}/profile 1,2,3,100,999,1000
```

If ID `2` returns another user's data when you're logged in as ID `1` → **IDOR = HIGH bounty ($500-$5000)**

### Step 4.4 — Rate Limit Testing

Missing rate limits on sensitive endpoints = easy medium bounty:

```bash
/bugbounty ratelimit https://api.target.com/login 50
/bugbounty ratelimit https://target.com/reset-password 30
```

If 50 requests all return 200 → no rate limiting → report it.

### Step 4.5 — GraphQL Introspection

If `deeprecon` found a GraphQL endpoint:
```bash
/bugbounty deeprecon target.com
# Look for: "GraphQL introspection enabled at /graphql"
```

Introspection enabled = **MEDIUM bounty** (exposes entire API schema to attackers).

---

## ✅ Part 5 — Confirming & Eliminating False Positives

**Never submit a report you haven't confirmed.** False positive reports damage your reputation.

### Step 5.1 — Confirm XSS

```bash
# Uses a unique canary token — if it reflects, it's real
/bugbounty confirm xss https://target.com/search q
```

Output: `🔴 CONFIRMED! Canary 'XSSCANARYTQMZ' reflected verbatim at position 4521`

This is your **evidence** for the report.

### Step 5.2 — Confirm SQL Injection

```bash
# Time-based blind SQLi confirmation — delays response by 3 seconds
/bugbounty confirm sqli https://target.com/api/product id
```

Output: `🔴 CONFIRMED! Response delayed 3.24s with SLEEP payload → Time-Based MySQL SQLi`

### Step 5.3 — Confirm SSRF

```bash
/bugbounty confirm ssrf https://target.com/api/fetch url
```

Tests internal IPs including AWS metadata endpoint (169.254.169.254).

### Step 5.4 — Response Diffing

Compare two responses to find data leakage or access control issues:
```bash
# Compare your response vs another user's ID response
/bugbounty diff https://api.target.com/users/1/profile https://api.target.com/users/2/profile
```

If response sizes differ significantly → potential IDOR.

---

## 📋 Part 6 — Logging & Managing Findings

### Step 6.1 — Log Your Finding

```bash
# After confirming a bug, log it immediately:
/bugbounty add https://target.com/search?q=<svg/onload=alert(1)> high "Reflected XSS in search parameter"

# Critical finding
/bugbounty add https://target.com/.env critical "Exposed .env file with database credentials"

# IDOR finding
/bugbounty add https://api.target.com/users/2/profile high "IDOR: Access to other user profiles"
```

### Step 6.2 — Check for Duplicates BEFORE Submitting

**This is critical** — submitting a duplicate gets you $0 and wastes time:

```bash
# Check if XSS on this program is already disclosed
/bugbounty duplicate Reflected XSS shopify

# Check by finding ID
/bugbounty duplicate 1
```

If the agent finds similar disclosed reports → read them, make sure yours is different (different endpoint, different parameter, different impact).

### Step 6.3 — Estimate Your Payout

```bash
/bugbounty bounty high
# Output: $1,000 — $10,000 typical range
# Factors: pre-auth +50%, affects many users +50%, working PoC +30%

/bugbounty bounty critical
# Output: $5,000 — $50,000+
```

### Step 6.4 — View All Findings

```bash
/bugbounty findings
```

Shows severity, status, platform, date for every finding.

---

## 📄 Part 7 — Writing the Report (Most Important Part)

A good report = faster triage + higher bounty + no information requests.

### Step 7.1 — Generate PoC Report

```bash
/bugbounty report 1      # For finding ID 1
/bugbounty report        # For most critical finding
```

If your LLM (Ollama) is running, it automatically adds:
- AI-written business impact statement
- Specific remediation steps

The report is **saved as a `.md` file** automatically.

### Step 7.2 — What Makes a Perfect Report

Every H1/Bugcrowd report needs these sections:

```markdown
## Title
[XSS] Reflected Cross-Site Scripting in /search?q= parameter

## Severity
High

## Summary
The `q` parameter on the search page reflects user input without sanitization,
allowing arbitrary JavaScript execution in the victim's browser context.

## Steps to Reproduce
1. Navigate to: https://target.com/search
2. Enter the following payload in the search box:
   `<svg/onload=alert(document.cookie)>`
3. The payload executes — showing your cookie value

## Proof of Concept
[Paste the URL with payload]
[Attach a screenshot or screen recording]

## Impact
An attacker can steal session cookies, redirect users to phishing pages,
or perform actions on behalf of the victim. With CSRF this becomes critical.

## Remediation
- HTML-encode all user input before rendering in the DOM
- Implement a Content Security Policy (CSP) header
- Use DOMPurify library for sanitization
```

**Pro tips for higher bounties:**
- 📸 Always attach a screenshot of the alert box / evidence
- 📹 Screen recordings get triaged faster
- 🔗 Include the exact vulnerable URL
- 💡 Suggest impact chaining (XSS + CSRF = critical)
- ⚡ Report within 24 hours of finding it

---

## 💸 Part 8 — Submitting & Getting Paid

### Step 8.1 — Submit via Agent API (HackerOne)

Make sure your token is set:
```powershell
$env:H1_API_TOKEN = "your_token"
$env:H1_USERNAME = "your_handle"
```

Then submit:
```bash
/bugbounty submit h1 shopify 1        # Submit finding #1 to Shopify's H1 program
/bugbounty submit h1 gitlab           # Most critical finding auto-submitted
```

Success: `✅ Report submitted! ID: #2847261 → https://hackerone.com/reports/2847261`

### Step 8.2 — Submit via Bugcrowd/Intigriti (Manual)

The agent generates your formatted report:
```bash
/bugbounty report 1
```

Then:
1. Copy the report text
2. Go to **bugcrowd.com/your-program/report** or **app.intigriti.com**
3. Paste + submit

### Step 8.3 — After Submission — What Happens

| Timeline | What to Expect |
|---|---|
| **Day 1-3** | Triage team reviews — marks as "Needs more info" or "Triaged" |
| **Day 3-14** | Technical review — severity confirmed or adjusted |
| **Day 14-30** | Bounty awarded + fix verified |
| **Day 30-60** | Payment processed |

**Communicate professionally:**
- If they ask for more info → respond within 48 hours
- If no response in 7 days → politely follow up once
- If marked "Informative" (no bounty) → ask why, learn from it

### Step 8.4 — How Payments Work

| Platform | Payment Methods | Minimum | Timing |
|---|---|---|---|
| **HackerOne** | PayPal, Wire, Crypto | $100 | After fix verification |
| **Bugcrowd** | PayPal, Bank | $20 | After triage approval |
| **Intigriti** | PayPal, IBAN | €50 | After fix verification |

**HackerOne PayPal setup:**
1. Log in → Settings → Payment Preferences
2. Add PayPal email
3. Bounties auto-transfer when awarded

**For India (PayPal → Bank):**
1. Receive in PayPal
2. Withdraw to Indian bank account (takes 3-5 business days)
3. Report as "Income from Other Sources" in ITR

---

## 🔥 Part 9 — Advanced Strategies (More Money)

### Strategy 1: Chain Vulnerabilities

Single bugs pay low. Chained bugs pay 3-5x more:

```
XSS + CSRF = Critical ($5,000+)
SSRF + Internal access = Critical ($10,000+)
IDOR + PII data = High ($2,000+)
Open Redirect + OAuth = High ($1,500+)
```

How to chain with the agent:
```bash
# Find XSS first
/bugbounty probe https://target.com/search q xss

# Then check if CSRF token is missing
/bugbounty scan https://target.com/settings/update

# If both → chain them in the report for critical severity
```

### Strategy 2: Hunt Old Features

```bash
# Wayback shows features that existed before
/bugbounty deeprecon target.com
# Look for archived paths like /api/v1/ that v2 replaced
# Old APIs often lack proper auth checks
```

### Strategy 3: API Versioning Attacks

Most companies forget to lock down old API versions:
```bash
/bugbounty params target.com
# Look for: /api/v1/ still accessible alongside /api/v2/
# v1 often has fewer security controls
```

### Strategy 4: Mobile App Endpoints

```bash
/bugbounty js https://target.com/app.js
# JS bundles from mobile apps expose internal API endpoints
# Many are not in the website's visible surface
```

### Strategy 5: High-Value Target Selection

```bash
# Programs with highest max payouts
/bugbounty programs h1 apple
/bugbounty programs h1 google
/bugbounty programs h1 microsoft
/bugbounty programs h1 paypal

# Programs with fastest response times (less competition)
/bugbounty programs ig     # Intigriti has many EU companies, less hunters
```

---

## 📊 Part 10 — Tracking Your Progress

### Realistic Income Timeline

| Month | Expected Output | Expected Income |
|---|---|---|
| Month 1 | Learn + setup + first recon | $0-$150 (informational rewards) |
| Month 2 | First low/medium finding | $200-$500 |
| Month 3 | First high finding | $500-$2,000 |
| Month 6 | Consistent finders | $1,000-$5,000/month |
| Month 12 | Senior hunter level | $3,000-$15,000/month |
| Year 2+ | Elite hunter | $10,000-$50,000+/month |

Top HackerOne hunters earn **$500,000+/year**. Most consistent hunters earn **$2,000-$10,000/month**.

### Daily Workflow (2-4 Hours)

```bash
# Morning: Find a new target
/bugbounty programs h1
/bugbounty scope h1 <new-program>

# Recon (30 mins)
/bugbounty deeprecon target.com
/bugbounty js https://target.com

# Hunt (1-2 hours)
/bugbounty params target.com
/bugbounty scan https://target.com
/bugbounty probe https://target.com/search q xss

# Confirm & report (30 mins)
/bugbounty confirm xss https://target.com/search q
/bugbounty duplicate "Reflected XSS target.com"
/bugbounty report 1
/bugbounty submit h1 target-program 1

# Track findings
/bugbounty findings
```

---

## 🧠 Part 11 — Quick Command Reference Card

```
SETUP
  /bugbounty platforms           → See all platforms
  /bugbounty programs h1         → Browse programs
  /bugbounty scope h1 <program>  → What can I test?

RECON
  /bugbounty recon <domain>      → Quick passive recon
  /bugbounty deeprecon <domain>  → Full Wayback+JS+OTX+GraphQL
  /bugbounty js <url>            → Extract JS endpoints
  /bugbounty params <domain>     → Find hidden params + APIs

SCAN
  /bugbounty scan <url>          → Active scan
  /bugbounty payloads xss        → WAF bypass payloads
  /bugbounty probe <url> <p> xss → Smart mutation probe
  /bugbounty confirm xss <url> <p> → Confirm, kill false+

AUTH BUGS
  /bugbounty session add <n> bearer <token>
  /bugbounty idor <url/{id}> 1,2,3,100
  /bugbounty ratelimit <url> 50
  /bugbounty diff <url1> <url2>

REPORT & PAY
  /bugbounty findings            → See all bugs
  /bugbounty add <url> high <title>
  /bugbounty duplicate <keyword> → Check before submit!
  /bugbounty bounty high         → Estimate payout
  /bugbounty report 1            → Generate PoC .md
  /bugbounty submit h1 <program> → Submit via API
```

---

## ⚠️ Part 12 — Legal & Safety Rules

1. **Always read the program policy** before any testing
2. **Never test out-of-scope** — instant permanent ban
3. **Use test accounts** — never access real user data
4. **Never automated at scale** — one request at a time, human-like speed
5. **Do not exfiltrate data** — screenshot the vulnerability, don't download
6. **No denial of service payloads** — no crash testing
7. **Disclose only to the program** — no public disclosure during embargo
8. **Wait for fix** — give 90 days before going public (responsible disclosure)

> ⚖️ Ethical bug hunting is legal. Unauthorized hacking is not. The bug bounty programs give you **written authorization** to test — this is your legal protection.

---

*Phase 20 — Complete Money Guide — The Ultimate AI Agent Bug Bounty System 🚀💰*

---

## 🤖 Claude Code Integration (Phase 20)

Your agent now includes **44 tools** ported from Anthropic's Claude Code architecture.

### New Files

| File | Description |
|------|-------------|
| `claw_harness.py` | Core harness: ClawSession, ClawRuntime, ToolPermissionContext, 10 claw tools |
| `claude_code_tools.py` | 25 additional Claude Code tools: tasks, REPL, teams, cron, worktree, LSP, and more |

### Quick Setup

`python
from tool_registry import ToolRegistry
from claw_harness import register_claw_tools, ClawSession, ClawRuntime
from claude_code_tools import register_claude_tools

reg = ToolRegistry()
reg.register_builtins()      # 9 base tools
register_claw_tools(reg)     # +10 claw tools
register_claude_tools(reg)   # +25 claude tools
# Total: 44 tools
| Category | Tools |
|----------|-------|
| **filesystem** | glob, grep_search, file_edit, file_read, file_write |
| **system** | powershell, bash |
| **web** | web_fetch, remote_trigger |
| **tasks** | task_create, task_get, task_list, task_update, task_stop, task_output |
| **teams** | team_create, team_delete |
| **development** | repl, lsp_query, notebook_edit |
| **agent** | enter_plan_mode, exit_plan_mode, config, tool_search, agent_invoke, synthetic_output |
| **productivity** | todo_write |
| **messaging** | send_message |
| **scheduler** | schedule_cron |
| **skills** | skill_invoke |
| **git** | enter_worktree, exit_worktree |
| **interaction** | ask_user_question |
| **utility** | brief, sleep |

### Key Architecture Patterns (from Claude Code)

| Pattern | Class | What it does |
|---------|-------|--------------|
| **QueryEngine** | `ClawSession` | Multi-turn loop with token budget + auto compaction |
| **Plan Mode** | `ClawSession.enter_plan_mode()` | Agent plans before executing tools |
| **Permission Gating** | `ToolPermissionContext` | Deny-list based tool blocking |
| **Streaming** | `ClawSession.stream_submit()` | SSE-style event streaming |
| **Session Persistence** | `ClawSession.persist()` | Save + reload sessions as JSON |
| **Prompt Routing** | `ClawRuntime.route_prompt()` | Token-match prompts to relevant tools |
| **Task System** | `task_create/get/list/update/stop` | Full task lifecycle management |

### Feature Status vs Claude Code Original

| Feature | Claude Code | Your Agent |
|---------|-------------|------------|
| QueryEngine (multi-turn) | TypeScript | ✅ `ClawSession` (Python) |
| Plan Mode | TS EnterPlanModeTool | ✅ Ported |
| Memory (memdir) | TypeScript | ✅ `memory_manager.py` |
| Skills | SkillTool | ✅ `skill_invoke` + `skill_loader.py` |
| Voice | Voice module | ✅ `voice_handler.py` |
| Task System | TaskCreate/Stop/etc | ✅ 6 task tools |
| Team Mode | TeamCreate/Delete | ✅ 2 team tools |
| REPL (persistent) | REPLTool | ✅ `repl` tool |
| LSP | LSPTool | ✅ `lsp_query` |
| MCP | MCPTool | ✅ `mcp_server.py` |
| Git Worktree | Worktree tools | ✅ enter/exit_worktree |
| Cron Scheduler | ScheduleCronTool | ✅ `schedule_cron` |
| Sub-agent spawning | AgentTool | ✅ `agent_invoke` |
| Permission gating | Permission system | ✅ `ToolPermissionContext` |
| Streaming events | SSE streaming | ✅ `stream_submit()` |

---
