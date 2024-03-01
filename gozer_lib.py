from dataclasses import dataclass,asdict
from datetime import datetime

class Keys:
    BUILD="builds"
@dataclass
class GozerDeploy:
    id: str
    date_built: datetime
    user_tag: str
    pinned: bool

class GozerApp(object):

    def __init__(self, data: dict):
        self.data = data
        if Keys.BUILD not in self.data.keys():
            self.data[Keys.BUILD] = {}

    def get_by_id(self,id: str):
        return self.data[Keys.BUILD].get(id)

    def save(self, to_save: GozerDeploy):
        self.data[Keys.BUILD][to_save.id] = asdict(to_save)

    def get_builds(self):
        builds_newest_to_oldest = dict(reversed(list(self.data.items())))
        r = []
        for k in reversed(self.data.keys()):
            r.append(GozerDeploy(**self.data.get(k)))
        return r