# AI Agent Project Guide for Steam Manifest Tool

This document provides essential context for AI agents working on the Steam Manifest Tool codebase.

## 🏗️ Architecture Overview

This is an asynchronous Python CLI tool for retrieving Steam manifest files from GitHub repositories.

### Key Components

- **`src/main.py`**: Entry point for application logic. Orchestrates the workflow: Steam verification -> App lookup ->
  Manifest search -> Download.
    - The root `main.py` is a shim that imports and runs `src.main.main`.
- **`src/core/api_client.py`**: Centralized async HTTP client (`APIClient`).
    - **Pattern**: Wraps `aiohttp` with `tenacity` for retries, `cachetools` for caching, and `orjson` for fast JSON
      parsing.
    - **Usage**: Use `APIClient` instance from `src.core.api_client` for all network requests.
- **`src/services/steam_service.py`**: Manages Steam app identity and store data (`SteamService`).
    - Resolves App ID/Name and DLC information via Steam Web API.
- **`src/services/github_service.py`**: Handles GitHub interactions (`GitHubService`).
    - Searches repositories for manifest files and depot keys.
    - Manages rate limits and repository traversal.
- **`src/services/file_service.py`**: Handles file I/O and parsing (`FileService`).
    - **Pattern**: Offloads CPU-bound VDF/JSON parsing to thread pool executor to avoid blocking the event loop.
    - **Key Libs**: `vdf` (Valve Data Format), `orjson`, `aiofiles`.
- **`src/core/constants.py`**: Centralized configuration (`Urls`, `Files`, `Steam` classes) and constants.

## 🔄 Critical Workflows & Patterns

### Asynchronous Design

- **Core Principle**: The entire application is `async/await` based.
- **Concurrency**: `asyncio` is used extensively. IO-bound tasks run concurrently where possible.
- **CPU-Bound Tasks**: Must be offloaded to an executor:
  ```python
  # Example from src/services/file_service.py
  loop = asyncio.get_event_loop()
  data = await loop.run_in_executor(None, vdf.loads, content.decode())
  ```

### Dependency Injection

- **Service Pattern**: Services (`SteamService`, `GitHubService`, `FileService`) are instantiated in `main()` and
  injected where needed.
- `APIClient` is managed as an async context manager and passed to services.

### Error Handling & Logging

- **Logging**: Uses `loguru`.
    - Format: `<green>{time}</green> | <level>{level}</level> | <level>{message}</level>`
    - Usage: `logger.info()`, `logger.error()`, etc.
- **UI Output**: Uses `rich` for user-facing output (tables, progress bars).

## 🛠️ Development & Debugging

### Setup

- **Dependencies**: `pip install -r requirements.txt`
- **Structure**:
    - `src/core`: Core utilities and constants.
    - `src/services`: Business logic services.
    - `src/main.py`: Main application logic.

### Running

```powershell
# Run via root entry point
python main.py -a <APP_ID_OR_NAME>

# With Debug logging
python main.py -a <APP_ID> -d
```

### Common Tasks

- **Adding a new repository**: Update `DEFAULT_REPOS` in `src/core/constants.py`.
- **Modifying API behavior**: Edit `src/core/api_client.py`.
- **Adding new file processors**: Update `src/services/file_service.py`.

