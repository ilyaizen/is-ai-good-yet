import argparse
import asyncio
import sys
from src.utils import setup_logging

def main():
    """
    Entrypoint for the 'Is AI Good Yet?' pipeline.
    """
    parser = argparse.ArgumentParser(description="Run the data processing pipeline.")
    parser.add_argument("--phase", choices=["ingest", "scrape", "analyze", "all"], default="all", help="Pipeline phase to run")
    args = parser.parse_args()

    setup_logging() 
    
    print(f"Starting pipeline phase: {args.phase}")
    
    # TODO: Implement phase orchestration
    if args.phase in ["ingest", "all"]:
        # await run_ingestion()
        pass
    
    if args.phase in ["scrape", "all"]:
        pass

    if args.phase in ["analyze", "all"]:
        pass

if __name__ == "__main__":
    try:
        # asyncio.run(main_async()) # When async is ready
        main()
    except KeyboardInterrupt:
        print("\nPipeline interrupted by user.")
        sys.exit(0)
