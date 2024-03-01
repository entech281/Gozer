from gozer_lib import GozerApp,GozerDeploy
from datetime import datetime

def test_gozer_save():
    d = {}
    g = GozerApp(d)
    DT=datetime.now()
    ID='133423'
    TAG='foo'

    f = GozerDeploy(id=ID, date_built=DT, user_tag=TAG, pinned=False)
    g.save(f)
    assert {
        'builds': {
            ID : {
                    'id': ID,
                    'date_built': DT,
                    'user_tag': TAG,
                    'pinned': False
            }
        }
    } == g.data

