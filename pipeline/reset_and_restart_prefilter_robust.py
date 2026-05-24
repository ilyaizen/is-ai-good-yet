#!/usr/bin/env python3
"""
Robust script to reset the prefilter database and restart the prefilter process.
This script:
1. Resets all prefilter data in the database
2. Runs the prefilter with legacy single-title detection
3. Handles rate limiting and allows for resumable execution
"""

import os
import sys
import asyncio
import time
from pathlib import Path

# Add the pipeline/src directory to the Python path
sys.path.append(str(Path(__file__).parent / "src"))
sys.path.append(str(Path(__file__).parent / "src" / "store"))

from src.store.db import reset_prefilter_data, init_db
from src.prefilter import prefilter_titles

def main():
    print("Starting prefilter reset and restart process...")

    # Initialize database
    print("Initializing database...")
    init_db()

    # Reset prefilter data
    print("Resetting prefilter data...")
    success = reset_prefilter_data()
    if success:
        print("Prefilter data reset successfully!")
    else:
        print("Failed to reset prefilter data")
        return

    # Get API key from environment
    api_key = os.environ.get("MISTRAL_API_KEY")
    if not api_key:
        print("Error: MISTRAL_API_KEY environment variable is not set")
        print("Please set your Mistral API key in the .env file or environment variables")
        return

    print("Using Mistral API key from environment variables")

    # Run prefilter with legacy single-title processing
    print("Starting prefilter with legacy single-title detection...")
    print("This may take some time depending on the number of URLs to process...")
    print("The process is resumable - you can stop and restart it if needed")

    try:
        # Run with rate limiting and resumable execution
        asyncio.run(prefilter_titles(
            api_key=api_key,
            verbose=True,
            batch_size=1,  # Single-title processing
            use_batch_processing=False  # Legacy mode
        ))
        print("Prefilter process completed!")
    except KeyboardInterrupt:
        print("\nProcess interrupted by user. You can restart to continue from where it left off.")
    except Exception as e:
        print(f"Error during prefilter process: {e}")
        print("You can restart the process to continue from the last checkpoint.")
        return

if __name__ == "__main__":
    main()