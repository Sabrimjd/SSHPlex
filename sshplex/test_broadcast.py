#!/usr/bin/env python3
"""
Test script for SSHplex session manager with broadcast functionality.
"""

import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from textual.app import App
from lib.ui.session_manager import TmuxSessionManager

class TestSessionManagerApp(App):
    """Test app for session manager with broadcast."""
    
    def on_mount(self):
        """Show the session manager on startup."""
        self.push_screen(TmuxSessionManager())

if __name__ == "__main__":
    print("🧪 SSHplex Session Manager Broadcast Test")
    print("📡 Press 'b' to toggle broadcast mode")
    print("🔗 Press 'enter' to connect to sessions")
    print("❌ Press 'k' to kill sessions")
    print("🔄 Press 'r' to refresh")
    print("🚪 Press 'ESC' or 'q' to close")
    
    app = TestSessionManagerApp()
    app.run()
