#!/usr/bin/env python3
"""
Launch script for the S3 Vector POC Main Application

This script provides a convenient way to launch the complete demo suite
with all examples integrated as individual pages.
"""

import os
import sys
import argparse
from pathlib import Path

# Add parent directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from frontend.main_app import S3VectorMainApp
from src.utils.logging_config import get_logger

logger = get_logger(__name__)

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Launch S3 Vector POC Main Application",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python frontend/launch_main.py                    # Launch complete demo suite
  python frontend/launch_main.py --unified-only    # Launch only Unified Video Search
  python frontend/launch_main.py --port 8080       # Launch on custom port
  python frontend/launch_main.py --share           # Enable public sharing
  python frontend/launch_main.py --debug           # Enable debug mode
        """
    )
    
    parser.add_argument(
        '--host',
        default='0.0.0.0',
        help='Host to bind to (default: 0.0.0.0)'
    )
    
    parser.add_argument(
        '--port',
        type=int,
        default=7860,
        help='Port to bind to (default: 7860)'
    )
    
    parser.add_argument(
        '--share',
        action='store_true',
        help='Enable public URL sharing via Gradio'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug mode'
    )
    
    parser.add_argument(
        '--inbrowser',
        action='store_true',
        help='Automatically open in browser'
    )
    
    parser.add_argument(
        '--auth',
        nargs=2,
        metavar=('USERNAME', 'PASSWORD'),
        help='Enable basic authentication (username password)'
    )
    
    parser.add_argument(
        '--ssl-keyfile',
        help='Path to SSL key file'
    )
    
    parser.add_argument(
        '--ssl-certfile',
        help='Path to SSL certificate file'
    )
    
    parser.add_argument(
        '--quiet',
        action='store_true',
        help='Reduce logging output'
    )
    
    parser.add_argument(
        '--unified-only',
        action='store_true',
        help='Launch only the Unified Video Search demo'
    )
    
    return parser.parse_args()

def main():
    """Main entry point."""
    args = parse_args()
    
    try:
        # Set up environment
        if args.quiet:
            import logging
            logging.getLogger().setLevel(logging.WARNING)
        
        print("=" * 80)
        print("🎬 S3 Vector Embedding POC - Complete Demo Suite")
        print("=" * 80)
        print()
        print("🚀 Launching comprehensive multi-modal search demo...")
        print()
        print("📋 Features included:")
        print("   ⭐ NEW: Unified Video Search (Complete Pipeline)")
        print("   • Real Video Processing (TwelveLabs + S3 Vector)")
        print("   • Cross-Modal Search (Text ↔ Video)")
        print("   • Multi-Video Index Management")
        print("   • Custom Content Support")
        print("   • Cost Analysis & Tracking")
        print("   • Video/Text Preview")
        print("   • Resource Management")
        print()
        print(f"🌐 Server: http://{args.host}:{args.port}")
        if args.share:
            print("🔗 Public sharing: Enabled")
        if args.auth:
            print("🔒 Authentication: Enabled")
        print()
        print("💡 Tip: Check the Documentation tab for usage guidelines")
        print("=" * 80)
        print()
        
        # Create application
        if args.unified_only:
            # Launch only the unified video search demo
            from frontend.pages.unified_video_search_page import UnifiedVideoSearchPage
            print("🎯 Launching Unified Video Search Demo only...")
            print()
            demo_page = UnifiedVideoSearchPage()
            app = demo_page.create_page()
        else:
            # Launch full demo suite
            app = S3VectorMainApp()
        
        # Prepare launch parameters
        launch_params = {
            'server_name': args.host,
            'server_port': args.port,
            'share': args.share,
            'debug': args.debug,
            'inbrowser': args.inbrowser,
            'quiet': args.quiet,
            'show_error': not args.quiet
        }
        
        # Add authentication if specified
        if args.auth:
            launch_params['auth'] = tuple(args.auth)
        
        # Add SSL if specified
        if args.ssl_keyfile and args.ssl_certfile:
            launch_params['ssl_keyfile'] = args.ssl_keyfile
            launch_params['ssl_certfile'] = args.ssl_certfile
        
        # Launch the application
        app.launch(**launch_params)
        
    except KeyboardInterrupt:
        print("\n\n🛑 Application stopped by user")
        print("👋 Thank you for using S3 Vector POC Demo Suite!")
        
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        print(f"\n❌ Error: {e}")
        print("\n🔧 Troubleshooting tips:")
        print("   1. Check AWS credentials and permissions")
        print("   2. Verify S3 Vector bucket configuration")
        print("   3. Ensure all required dependencies are installed")
        print("   4. Check the system status in the application")
        sys.exit(1)

if __name__ == "__main__":
    main()