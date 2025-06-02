#!/usr/bin/env python3
"""
Simple test for the TmuxSessionManager widget.
"""

import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lib.ui.session_manager import TmuxSessionManager
from lib.logger import setup_logging, get_logger

def test_session_manager_simple():
    """Simple test of the session manager."""
    
    # Setup logger
    setup_logging()
    logger = get_logger()
    
    print("🧪 Testing TmuxSessionManager import and basic functionality...")
    
    try:
        # Test creating the session manager
        session_manager = TmuxSessionManager()
        print("✅ TmuxSessionManager created successfully")
        logger.info("TmuxSessionManager created successfully")
        
        # Test loading sessions (this might fail if textual isn't properly imported)
        print("🔍 Testing session loading...")
        session_manager.load_sessions()
        print(f"✅ Found {len(session_manager.sessions)} tmux sessions")
        
        for session in session_manager.sessions:
            print(f"   📺 {session.name} - {session.windows} windows - {'Active' if session.attached else 'Detached'}")
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("💡 This is expected if textual is not available")
    except Exception as e:
        print(f"❌ Error: {e}")
        logger.error(f"Session manager test error: {e}")

if __name__ == "__main__":
    test_session_manager_simple()
