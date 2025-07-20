# MaiCore Technology Stack

## Core Technologies
- **Python 3.10+**: Main programming language
- **AsyncIO**: Asynchronous programming for concurrent operations
- **TOML**: Configuration file format
- **SQLite**: Local database storage (Peewee ORM)
- **FastAPI**: Web framework for API endpoints
- **WebSockets**: Real-time communication
- **Docker**: Containerized deployment

## Key Dependencies
- **maim-message**: Custom message handling framework
- **openai**: LLM API client
- **faiss-cpu**: Vector similarity search for memory system
- **networkx**: Graph operations for memory relationships
- **jieba**: Chinese text segmentation
- **pypinyin**: Chinese pinyin conversion
- **structlog**: Structured logging
- **rich**: Enhanced terminal output
- **customtkinter**: GUI components

## LLM Integration
- **Multi-provider support**: SiliconFlow, DeepSeek, ChatAnywhere, Bailian
- **Model specialization**: Different models for different tasks (chat, memory, tools, etc.)
- **Token management**: Cost tracking and optimization
- **Streaming support**: Real-time response generation

## Architecture Patterns
- **Plugin system**: Modular component architecture
- **Event-driven**: Async task management
- **Memory system**: Graph-based persistent memory with forgetting/consolidation
- **Mood system**: Emotional state management
- **Expression learning**: Dynamic communication style adaptation

## Build & Development Commands

### Local Development
```bash
# Setup virtual environment
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt
# or with uv (faster)
uv pip install -r requirements.txt

# Run the bot
python bot.py
```

### Docker Deployment
```bash
# Build image
docker build -t maibot .

# Run with docker-compose
docker-compose up -d

# View logs
docker-compose logs -f core
```

### Configuration
- Copy `template/template.env` to `.env` and configure API keys
- Copy `template/bot_config_template.toml` to `config/bot_config.toml`
- Modify personality, identity, and model settings in TOML config

### Testing & Scripts
```bash
# Run specific analysis scripts
python scripts/log_viewer.py
python scripts/analyze_expressions.py
python scripts/view_hfc_stats.py

# Database migration
python scripts/mongodb_to_sqlite.py
```

## Code Style
- **Ruff**: Linting and formatting (configured in pyproject.toml)
- **Line length**: 120 characters
- **Quote style**: Double quotes
- **Import organization**: Structured imports with proper grouping
- **Type hints**: Encouraged but not strictly enforced
- **Async/await**: Preferred over callbacks for concurrent operations