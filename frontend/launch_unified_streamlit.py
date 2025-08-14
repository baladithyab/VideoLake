#!/usr/bin/env python3
"""
Launch script for the Unified Streamlit App

This script provides a convenient way to launch the complete S3Vector
video search pipeline demo translated from the Gradio version.
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Launch S3Vector Unified Streamlit App",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python frontend/launch_unified_streamlit.py                    # Launch with defaults
  python frontend/launch_unified_streamlit.py --port 8501       # Launch on custom port
  python frontend/launch_unified_streamlit.py --host 0.0.0.0    # Bind to all interfaces
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
    
    return parser.parse_args()

def main():
    """Main entry point."""
    args = parse_args()
    
    # Get the script directory
    script_dir = Path(__file__).parent
    app_path = script_dir / "unified_streamlit_app.py"
    
    if not app_path.exists():
        print(f"❌ Error: {app_path} not found")
        sys.exit(1)
    
    print("=" * 80)
    print("🎬 S3Vector Enhanced Unified Demo - Streamlit Edition")
    print("=" * 80)
    print()
    print("🚀 Launching comprehensive video search pipeline...")
    print()
    print("📋 Enhanced Features:")
    print("   • Sample Video Library (6 Creative Commons videos)")
    print("   • Multiple Video Upload & Batch Processing")
    print("   • Index Creation & Management")
    print("   • Multi-Modal Search (Text-to-Video, Video-to-Video, Temporal)")
    print("   • PCA/t-SNE Embedding Visualization")
    print("   • Enhanced Query Suggestions")
    print("   • Cost Tracking & Analytics")
    print("   • Video Segment Playback")
    print("   • Real AWS Integration with Safety Toggles")
    print()
    print(f"🌐 Server: http://{args.host}:{args.port}")
    print()
    print("💡 Tips:")
    print("   - Start with 'Index Setup' to create your video search index")
    print("   - Try sample videos for quick testing")
    print("   - Use batch processing for multiple videos")
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
    
    try:
        # Launch Streamlit
        subprocess.run(cmd, check=True)
        
    except KeyboardInterrupt:
        print("\n\n🛑 Application stopped by user")
        print("👋 Thank you for using S3Vector Unified Demo!")
        
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Error launching Streamlit: {e}")
        print("\n🔧 Troubleshooting tips:")
        print("   1. Ensure Streamlit is installed: pip install streamlit")
        print("   2. Check that all dependencies are available")
        print("   3. Verify AWS credentials and configuration")
        print("   4. Try a different port if the current one is in use")
        sys.exit(1)
    
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()