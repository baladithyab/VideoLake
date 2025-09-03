#!/usr/bin/env python3
"""
Launcher for Refactored Unified S3Vector Demo

This launcher provides a clean way to start the refactored unified demo
with proper configuration and error handling.
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path


def setup_environment():
    """Setup the environment for running the demo."""
    # Add project root to Python path
    project_root = Path(__file__).parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    
    # Set environment variables if needed
    os.environ.setdefault('STREAMLIT_SERVER_HEADLESS', 'true')
    os.environ.setdefault('STREAMLIT_SERVER_ENABLE_CORS', 'false')


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Launch the Refactored Unified S3Vector Demo",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python launch_refactored_demo.py                    # Default settings
  python launch_refactored_demo.py --port 8502        # Custom port
  python launch_refactored_demo.py --host 0.0.0.0     # External access
  python launch_refactored_demo.py --browser          # Auto-open browser
  python launch_refactored_demo.py --debug            # Debug mode
        """
    )
    
    parser.add_argument(
        '--host',
        default='localhost',
        help='Host to bind the server to (default: localhost)'
    )
    
    parser.add_argument(
        '--port',
        type=int,
        default=8501,
        help='Port to run the server on (default: 8501)'
    )
    
    parser.add_argument(
        '--browser',
        action='store_true',
        help='Automatically open browser'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug mode'
    )
    
    parser.add_argument(
        '--theme',
        choices=['light', 'dark'],
        default='light',
        help='UI theme (default: light)'
    )
    
    return parser.parse_args()


def build_streamlit_command(args):
    """Build the streamlit command with arguments."""
    demo_file = Path(__file__).parent / "unified_demo_refactored.py"
    
    cmd = [
        'streamlit', 'run',
        str(demo_file),
        '--server.address', args.host,
        '--server.port', str(args.port),
        '--server.headless', 'true' if not args.browser else 'false',
        '--theme.base', args.theme,
        '--server.enableCORS', 'false',
        '--server.enableXsrfProtection', 'false'
    ]
    
    if args.browser:
        cmd.extend(['--server.headless', 'false'])
    
    if args.debug:
        cmd.extend(['--logger.level', 'debug'])
    
    return cmd


def check_dependencies():
    """Check if required dependencies are available."""
    required_packages = ['streamlit']
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"❌ Missing required packages: {', '.join(missing_packages)}")
        print("Please install them using: pip install streamlit")
        return False
    
    return True


def main():
    """Main launcher function."""
    print("🎬 S3Vector Unified Demo Launcher (Refactored)")
    print("=" * 50)
    
    # Parse arguments
    args = parse_arguments()
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    # Setup environment
    setup_environment()
    
    # Build command
    cmd = build_streamlit_command(args)
    
    # Display launch information
    print(f"🚀 Starting Refactored Unified S3Vector Demo...")
    print(f"📍 Host: {args.host}")
    print(f"🔌 Port: {args.port}")
    print(f"🌐 URL: http://{args.host}:{args.port}")
    print(f"🎨 Theme: {args.theme}")
    print(f"🐛 Debug: {'Enabled' if args.debug else 'Disabled'}")
    print(f"🌍 Browser: {'Auto-open' if args.browser else 'Manual'}")
    print()
    
    print("📋 Features Available:")
    print("• Modular component architecture")
    print("• Dual storage pattern comparison (Direct S3Vector vs OpenSearch Hybrid)")
    print("• Marengo 2.7 multi-vector processing")
    print("• Interactive search with performance metrics")
    print("• Safe demo mode (no AWS costs)")
    print("• Real AWS integration (when enabled)")
    print()
    
    print("🔧 Command:")
    print(" ".join(cmd))
    print()
    
    try:
        # Launch the application
        print("🎬 Launching application...")
        subprocess.run(cmd, check=True)
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to launch application: {e}")
        sys.exit(1)
    
    except KeyboardInterrupt:
        print("\n🛑 Application stopped by user")
        sys.exit(0)
    
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
