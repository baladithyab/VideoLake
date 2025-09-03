#!/usr/bin/env python3
"""
Launch Script for Unified S3Vector Demo

This script provides a convenient way to launch the unified S3Vector demo interface
that consolidates all frontend functionality into a single, professional application.
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Launch the Unified S3Vector Demo Interface",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python frontend/launch_unified_demo.py
  python frontend/launch_unified_demo.py --host 0.0.0.0 --port 8502
  python frontend/launch_unified_demo.py --browser --theme dark
        """
    )
    
    parser.add_argument(
        '--host',
        default='localhost',
        help='Host to bind to (default: localhost)'
    )
    
    parser.add_argument(
        '--port',
        type=int,
        default=8501,
        help='Port to bind to (default: 8501)'
    )
    
    parser.add_argument(
        '--theme',
        choices=['light', 'dark', 'auto'],
        default='auto',
        help='Streamlit theme (default: auto)'
    )
    
    parser.add_argument(
        '--browser',
        action='store_true',
        help='Automatically open in browser'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug mode'
    )
    
    return parser.parse_args()


def check_dependencies():
    """Check if required dependencies are available."""
    try:
        import streamlit
        import numpy
        import pandas
        print("✅ Core dependencies available")
        return True
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("Please install required packages:")
        print("pip install streamlit numpy pandas plotly")
        return False


def main():
    """Main entry point."""
    args = parse_args()
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    # Get the script directory
    script_dir = Path(__file__).parent
    app_path = script_dir / "unified_demo_app.py"
    
    if not app_path.exists():
        print(f"❌ Error: {app_path} not found")
        sys.exit(1)
    
    # Print banner
    print("=" * 80)
    print("🎬 S3Vector Unified Multi-Vector Demo")
    print("=" * 80)
    print("🚀 Starting unified demo interface...")
    print(f"📍 Host: {args.host}:{args.port}")
    print(f"🎨 Theme: {args.theme}")
    print()
    print("📋 Features:")
    print("   - Unified 5-section workflow interface")
    print("   - Proper StreamlitServiceManager integration")
    print("   - Multi-vector processing with Marengo 2.7")
    print("   - Interactive video player (coming soon)")
    print("   - Real-time cost tracking and analytics")
    print("🛡️ Safe Mode: 'Use Real AWS' defaults to OFF to prevent costs")
    print("=" * 80)
    print()
    
    # Build streamlit command
    cmd = [
        sys.executable, "-m", "streamlit", "run",
        str(app_path),
        "--server.address", args.host,
        "--server.port", str(args.port),
        "--theme.base", args.theme,
        "--server.headless", "true" if not args.browser else "false"
    ]
    
    if args.browser:
        cmd.extend(["--server.runOnSave", "true"])
    
    if args.debug:
        cmd.extend(["--logger.level", "debug"])
    
    try:
        # Launch Streamlit
        print(f"🚀 Launching: {' '.join(cmd)}")
        print()
        subprocess.run(cmd, check=True)
        
    except KeyboardInterrupt:
        print("\n\n🛑 Demo stopped by user")
        print("👋 Thank you for using S3Vector Unified Demo!")
        
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Failed to launch demo: {e}")
        sys.exit(1)
        
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
