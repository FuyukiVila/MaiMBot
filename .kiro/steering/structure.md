# MaiCore Project Structure

## Root Directory Layout
```
MaiBot/
├── bot.py                    # Main entry point
├── src/                      # Core source code
├── config/                   # Configuration files
├── data/                     # Runtime data and database
├── logs/                     # Application logs (organized by component)
├── plugins/                  # External plugins
├── scripts/                  # Utility and analysis scripts
├── template/                 # Configuration templates
├── depends-data/             # Static assets and dependencies
├── changelogs/               # Version history
├── docs/                     # Documentation
└── memory-bank/              # Project analysis and progress tracking
```

## Source Code Organization (`src/`)

### Core Modules
- **`src/main.py`**: Main system initialization and task scheduling
- **`src/config/`**: Configuration management and validation
- **`src/common/`**: Shared utilities (logging, database, messaging)
- **`src/manager/`**: System managers (async tasks, local storage)

### Chat System (`src/chat/`)
- **`message_receive/`**: Message processing and bot logic
- **`focus_chat/`**: Deep conversation mode with advanced processing
- **`heart_flow/`**: Emotional flow and observation systems
- **`memory_system/`**: Long-term memory storage and retrieval
- **`emoji_system/`**: Emoji management and expression
- **`express/`**: Expression learning and style adaptation
- **`willing/`**: Response willingness and frequency control
- **`utils/`**: Chat utilities and statistics
- **`replyer/`**: Response generation logic
- **`planner_actions/`**: Action planning for focus mode

### Supporting Systems
- **`src/individuality/`**: Personality and identity management
- **`src/mood/`**: Emotional state tracking
- **`src/person_info/`**: User relationship management
- **`src/tools/`**: Tool execution and management
- **`src/plugins/`**: Built-in plugin implementations
- **`src/plugin_system/`**: Plugin architecture and loading
- **`src/llm_models/`**: LLM integration utilities

## Configuration Structure (`config/`)
- **`bot_config.toml`**: Main bot configuration (personality, models, features)
- **`bot_config_dev.toml`**: Development environment settings
- **`bot_config_main.toml`**: Production environment settings
- **`lpmm_config.toml`**: LPMM (knowledge system) configuration

## Data Organization (`data/`)
- **`MaiBot.db`**: SQLite database for persistent storage
- **`lpmm_raw_data/`**: Raw knowledge data for processing

## Logging Structure (`logs/`)
Organized by component with separate directories for each major system:
- Component-specific logs (e.g., `chat/`, `memory/`, `mood/`)
- Feature-specific logs (e.g., `emoji/`, `expression/`, `tools/`)
- System logs (e.g., `main/`, `config/`, `api/`)

## Plugin Architecture
- **External plugins**: `plugins/` directory for user-added functionality
- **Built-in plugins**: `src/plugins/built_in/` for core plugin implementations
- **Plugin system**: `src/plugin_system/` for loading and management

## Development Conventions

### File Naming
- Snake_case for Python files and directories
- Descriptive names reflecting component purpose
- Manager/system suffixes for core system components

### Module Organization
- Each major feature has its own directory under `src/`
- Shared utilities in `src/common/`
- Configuration centralized in `src/config/`
- Clear separation between core logic and plugin systems

### Import Patterns
- Relative imports within modules
- Absolute imports from `src.` for cross-module dependencies
- Lazy imports for optional features (e.g., memory system)
- Singleton patterns for managers and global state

### Configuration Management
- TOML for structured configuration
- Environment variables for secrets and deployment settings
- Template files for easy setup
- Version-controlled configuration structure