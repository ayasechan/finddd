from finddd.find import *
from finddd.match import FT_DIRECTORY, FT_FILE


def test_find():

    files = find(r".", filetypes=[FT_DIRECTORY, FT_FILE],)
    print(files)
