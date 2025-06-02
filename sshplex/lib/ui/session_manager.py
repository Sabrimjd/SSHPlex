"""SSHplex TUI tmux session manager widget."""

from typing import List, Optional
from textual.containers import Container, Vertical
from textual.widgets import DataTable, Static
from textual.binding import Binding
from textual.screen import ModalScreen
from textual.app import ComposeResult
import libtmux

from ..logger import get_logger


class TmuxSession:
    """Simple tmux session data structure."""
    
    def __init__(self, name: str, session_id: str, created: str, windows: int, attached: bool = False):
        self.name = name
        self.session_id = session_id
        self.created = created
        self.windows = windows
        self.attached = attached
    
    def __str__(self) -> str:
        status = "📎" if self.attached else "💤"
        return f"{status} {self.name} ({self.windows} windows)"


class TmuxSessionManager(ModalScreen):
    """Modal screen for managing tmux sessions."""

    CSS = """
    TmuxSessionManager {
        align: center middle;
    }

    #session-dialog {
        width: 80;
        height: 20;
        border: thick $primary 60%;
        background: $surface;
    }

    #session-table {
        height: 1fr;
        margin: 1;
    }

    #session-header {
        height: 3;
        margin: 1;
        text-align: center;
        background: $primary;
        color: $text;
    }

    #session-footer {
        height: 3;
        margin: 1;
        text-align: center;
        background: $surface;
        color: $text-muted;
    }
    """

    BINDINGS = [
        Binding("enter", "connect_session", "Connect", show=True),
        Binding("k", "kill_session", "Kill", show=True),
        Binding("r", "refresh_sessions", "Refresh", show=True),
        Binding("escape", "close_manager", "Close", show=True),
        Binding("q", "close_manager", "Close", show=False),
    ]

    def __init__(self):
        """Initialize the tmux session manager."""
        super().__init__()
        self.logger = get_logger()
        self.sessions: List[TmuxSession] = []
        self.table: Optional[DataTable] = None
        self.tmux_server = None

    def compose(self) -> ComposeResult:
        """Create the session manager layout."""
        with Container(id="session-dialog"):
            yield Static("🖥️  SSHplex - tmux Session Manager", id="session-header")
            yield DataTable(id="session-table", cursor_type="row")
            yield Static("Enter: Connect | K: Kill | R: Refresh | ESC: Close", id="session-footer")

    def on_mount(self) -> None:
        """Initialize the session manager."""
        self.table = self.query_one("#session-table", DataTable)
        
        # Setup table columns
        self.table.add_column("Status", width=8)
        self.table.add_column("Session Name", width=25)
        self.table.add_column("Created", width=20)
        self.table.add_column("Windows", width=8)
        
        # Focus on the table
        self.table.focus()
        
        # Load sessions
        self.load_sessions()

    def load_sessions(self) -> None:
        """Load tmux sessions from the server."""
        try:
            # Initialize tmux server
            self.tmux_server = libtmux.Server()
            
            # Get all sessions
            tmux_sessions = self.tmux_server.list_sessions()
            self.sessions.clear()
            
            for session in tmux_sessions:
                # Check if session is attached (use session.attached property or check windows)
                try:
                    # libtmux sessions have an 'attached' property or we can check if it has windows
                    attached = hasattr(session, 'attached') and session.attached
                    if not hasattr(session, 'attached'):
                        # Fallback: check if session has active windows/panes
                        attached = len(session.windows) > 0 and any(len(w.panes) > 0 for w in session.windows)
                except:
                    attached = False
                
                # Get window count safely
                try:
                    window_count = len(session.windows) if hasattr(session, 'windows') else 0
                except:
                    window_count = 0
                
                tmux_session = TmuxSession(
                    name=session.session_name,
                    session_id=session.session_id,
                    created=session.created.strftime("%Y-%m-%d %H:%M:%S") if hasattr(session, 'created') else "Unknown",
                    windows=window_count,
                    attached=attached
                )
                self.sessions.append(tmux_session)
            
            # Populate table
            self.populate_table()
            
            self.logger.info(f"SSHplex: Loaded {len(self.sessions)} tmux sessions")
            
        except Exception as e:
            self.logger.error(f"SSHplex: Failed to load tmux sessions: {e}")
            # Show error in table
            self.table.clear()
            self.table.add_row("❌", "Error loading sessions", str(e), "0")

    def populate_table(self) -> None:
        """Populate the table with session data."""
        if not self.table:
            return

        # Clear existing data
        self.table.clear()

        if not self.sessions:
            self.table.add_row("ℹ️", "No tmux sessions found", "Create one with SSHplex", "0")
            return

        # Add sessions to table
        for session in self.sessions:
            status_icon = "📎" if session.attached else "💤"
            status_text = "Active" if session.attached else "Detached"
            
            self.table.add_row(
                f"{status_icon} {status_text}",
                session.name,
                session.created,
                str(session.windows),
                key=session.name
            )

    def action_connect_session(self) -> None:
        """Connect to the selected tmux session."""
        if not self.table or not self.sessions:
            return

        cursor_row = self.table.cursor_row
        if cursor_row >= 0 and cursor_row < len(self.sessions):
            session = self.sessions[cursor_row]
            
            self.logger.info(f"SSHplex: Connecting to tmux session '{session.name}'")
            
            # Close the modal and attach to session
            self.dismiss()
            
            # Auto-attach to the session by replacing current process
            import os
            os.execlp("tmux", "tmux", "attach-session", "-t", session.name)

    def action_kill_session(self) -> None:
        """Kill the selected tmux session."""
        if not self.table or not self.sessions:
            return

        cursor_row = self.table.cursor_row
        if cursor_row >= 0 and cursor_row < len(self.sessions):
            session = self.sessions[cursor_row]
            
            try:
                # Find and kill the session
                if self.tmux_server:
                    tmux_session = self.tmux_server.find_where({"session_name": session.name})
                    if tmux_session:
                        tmux_session.kill_session()
                        self.logger.info(f"SSHplex: Killed tmux session '{session.name}'")
                        
                        # Refresh the session list
                        self.load_sessions()
                    else:
                        self.logger.error(f"SSHplex: Session '{session.name}' not found for killing")
                        
            except Exception as e:
                self.logger.error(f"SSHplex: Failed to kill session '{session.name}': {e}")

    def action_refresh_sessions(self) -> None:
        """Refresh the session list."""
        self.logger.info("SSHplex: Refreshing tmux sessions")
        self.load_sessions()

    def action_close_manager(self) -> None:
        """Close the session manager."""
        self.dismiss()
