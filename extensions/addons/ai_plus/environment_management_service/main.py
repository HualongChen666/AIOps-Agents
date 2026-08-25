"""
Environment Management Service - Main Entry Point

This service provides comprehensive environment management capabilities including:
- Multi-environment management (dev, staging, prod)
- Configuration synchronization between environments
- Deployment orchestration
- Environment variable management
- Health checks
- Environment isolation
"""

import argparse
import logging
import sys
import os
import signal
import time

# Add the current directory to the path to allow imports
sys.path.insert(0, os.path.dirname(__file__))

from grpc.server import serve


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Environment Management Service'
    )
    
    parser.add_argument(
        '--host',
        type=str,
        default='[::]',
        help='Host to bind to (default: [::])'
    )
    
    parser.add_argument(
        '--port',
        type=int,
        default=50052,
        help='Port to bind to (default: 50052)'
    )
    
    parser.add_argument(
        '--workers',
        type=int,
        default=10,
        help='Maximum number of worker threads (default: 10)'
    )
    
    parser.add_argument(
        '--log-level',
        type=str,
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help='Logging level (default: INFO)'
    )
    
    return parser.parse_args()


def main():
    """Main entry point"""
    args = parse_args()
    
    # Set log level
    log_level = getattr(logging, args.log_level)
    logging.getLogger().setLevel(log_level)
    
    logger.info("=" * 60)
    logger.info("Environment Management Service Starting")
    logger.info("=" * 60)
    logger.info(f"Host: {args.host}")
    logger.info(f"Port: {args.port}")
    logger.info(f"Workers: {args.workers}")
    logger.info(f"Log Level: {args.log_level}")
    logger.info("=" * 60)
    
    # Handle graceful shutdown
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Start the server
        serve(
            host=args.host,
            port=args.port,
            max_workers=args.workers
        )
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
