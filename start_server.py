#!/usr/bin/env python3
"""
Simple script to start the invoice processing web interface
"""

import os
import sys
import subprocess
import webbrowser
import time
from pathlib import Path

def check_requirements():
    """Check if required packages are installed"""
    try:
        import uvicorn
        import fastapi
        return True
    except ImportError:
        print("❌ Missing required packages. Installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "uvicorn", "fastapi"])
        return True

def start_api_server():
    """Start the FastAPI backend server"""
    print("🚀 Starting API server...")
    
    # Change to the project directory
    project_dir = Path(__file__).parent
    os.chdir(project_dir)
    
    # Start the API server
    api_process = subprocess.Popen([
        sys.executable, "-m", "uvicorn", 
        "api.main:app", 
        "--host", "0.0.0.0", 
        "--port", "8000", 
        "--reload"
    ])
    
    return api_process

def start_frontend_server():
    """Start a simple HTTP server for the frontend"""
    print("🌐 Starting frontend server...")
    
    frontend_dir = Path(__file__).parent / "frontend"
    os.chdir(frontend_dir)
    
    # Start simple HTTP server
    frontend_process = subprocess.Popen([
        sys.executable, "-m", "http.server", "3000"
    ])
    
    return frontend_process

def main():
    """Main function to start both servers"""
    print("🎯 Invoice Processing System - Starting Web Interface")
    print("=" * 60)
    
    # Check requirements
    if not check_requirements():
        print("❌ Failed to install requirements")
        return
    
    try:
        # Start API server
        api_process = start_api_server()
        time.sleep(3)  # Give API server time to start
        
        # Start frontend server
        frontend_process = start_frontend_server()
        time.sleep(2)  # Give frontend server time to start
        
        print("\n✅ Servers started successfully!")
        print("📊 API Server: http://localhost:8000")
        print("🌐 Web Interface: http://localhost:3000")
        print("📚 API Docs: http://localhost:8000/docs")
        print("\n🎉 Opening web interface in browser...")
        
        # Open browser
        webbrowser.open("http://localhost:3000")
        
        print("\n⏹️  Press Ctrl+C to stop both servers")
        
        # Wait for user to stop
        try:
            api_process.wait()
        except KeyboardInterrupt:
            print("\n🛑 Stopping servers...")
            api_process.terminate()
            frontend_process.terminate()
            print("✅ Servers stopped")
            
    except Exception as e:
        print(f"❌ Error starting servers: {e}")
        return

if __name__ == "__main__":
    main()
