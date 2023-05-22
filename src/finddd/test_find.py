

from finddd.find import *
from subprocess import run

def test_finder():
    fder = Finder()
    # fder.hidden = True
    def cb(i: Path):
        print(i)
        # cp = run('bash -c "sleep 30s"', shell=True)
        # print(cp.returncode)

    fder.find('py', Path('.'), cb)
