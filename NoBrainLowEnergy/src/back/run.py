#!/usr/bin/env python3
"""
Startup script for NoBrainLowEnergy FastAPI backend
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path

def check_python_version():
    """Check if Python version is 3.8 or higher"""
    if sys.version_info < (3, 8):
        print("Error: Python 3.8 or higher is required")
        sys.exit(1)

def install_dependencies():
    """Install Python dependencies"""
    print("Installing Python dependencies...")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], check=True)
        print("Dependencies installed successfully!")
    except subprocess.CalledProcessError:
        print("Error: Failed to install dependencies")
        sys.exit(1)

def create_env_file():
    """Create .env file from example if it doesn't exist"""
    env_file = Path(".env")
    env_example = Path(".env.example")
    
    if not env_file.exists() and env_example.exists():
        print("Creating .env file from .env.example...")
        env_file.write_text(env_example.read_text())
        print("Please edit .env file with your configuration before running the server")
        return True
    return False

def generate_certificates():
    """Generate TLS certificates if they don't exist"""
    certs_dir = Path("certs")
    ca_cert = certs_dir / "ca.crt"
    
    if not ca_cert.exists():
        print("Generating TLS certificates...")
        try:
            subprocess.run([sys.executable, "generate_certs.py"], check=True)
        except subprocess.CalledProcessError:
            print("Warning: Failed to generate certificates automatically")
            print("You may need to generate them manually or disable TLS")

def run_server(host="0.0.0.0", port=8000, reload=True):
    """Run the FastAPI server"""
    print(f"Starting FastAPI server on {host}:{port}")
    try:
        import uvicorn
        uvicorn.run(
            "main:app",
            host=host,
            port=port,
            reload=reload,
            ssl_keyfile="./certs/server.key",
            ssl_certfile="./certs/server.crt"
        )
    except ImportError:
        print("Error: uvicorn not installed. Run with --install-deps first")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nServer stopped by user")

def main():
    parser = argparse.ArgumentParser(description="NoBrainLowEnergy FastAPI Backend")
    parser.add_argument("--install-deps", action="store_true", help="Install dependencies")
    parser.add_argument("--generate-certs", action="store_true", help="Generate TLS certificates")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument("--no-reload", action="store_true", help="Disable auto-reload")
    
    args = parser.parse_args()
    
    # Check Python version
    check_python_version()
    
    # Install dependencies if requested
    if args.install_deps:
        install_dependencies()
        return
    
    # Generate certificates if requested
    if args.generate_certs:
        generate_certificates()
        return
    
    # Create .env file if needed
    env_created = create_env_file()
    if env_created:
        print("Please configure your .env file and run again")
        return
    
    # Generate certificates if they don't exist
    generate_certificates()
    
    # Run the server
    run_server(
        host=args.host,
        port=args.port,
        reload=not args.no_reload
    )

if __name__ == "__main__":
    main()