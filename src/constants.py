from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
WORKDIR = BASE_DIR / "src"

TEAM_DIR = BASE_DIR / ".team"
INBOX_DIR = BASE_DIR / "inbox"
TASKS_DIR = BASE_DIR / ".tasks"
SKILLS_DIR = BASE_DIR / "skills"
TRANSCRIPT_DIR = BASE_DIR / ".transcripts"
TOKEN_THRESHOLD = 100000
POLL_INTERVAL = 5
IDLE_TIMEOUT = 60

VALID_MSG_TYPES = {"message", "broadcast", "shutdown_request",
                   "shutdown_response", "plan_approval_response"}