"""SteamManifest Entry Point"""

import asyncio
import sys
from pathlib import Path

# Fix module import paths
sys.path.insert(0, str(Path(__file__).parent))

from src.main import main

if __name__ == "__main__":
    try:
        if sys.platform == 'win32':
            # Windows specific event loop policy for subprocesses if needed
            # asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
            pass
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)
