from dataclasses import dataclass,asdict
from datetime import datetime

@dataclass
class GozerDeploy:
    id: str
    date_built: datetime
    user_tag: str
    pinned: bool