
# ============================================
# Ultimate AI Agent - Environment Variables
# ============================================

# --- LLM Providers ---
# Choose: 'openai', 'ollama', or 'anthropic'
MODEL_PROVIDER=openai

# OpenAI (required if provider is 'openai')
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxxxxx

# Anthropic (required if provider is 'anthropic')
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxxxxxxx

# Ollama (required if provider is 'ollama')
# Use http://host.docker.internal:11434 for local access from Docker
OLLAMA_HOST=http://localhost:11434

# --- Database ---
# Path to SQLite DB file
DATABASE_URL=sqlite:///./data/agent_memory.db

# --- Logging ---
LOG_LEVEL=INFO
