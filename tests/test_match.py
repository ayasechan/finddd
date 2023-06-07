import re
import stat
from datetime import datetime, timedelta
from pathlib import Path

from finddd.match import *


def test_NopMather():
    nm = NopMatcher()
    assert nm.match(Path("foo"))
    assert nm.match(Path("bar"))


def test_NotMather():
    nm = NotMatcher(NopMatcher())
    assert not nm.match(Path("foo"))
    assert not nm.match(Path("bar"))


def test_HiddenMatcher():
    hm = HiddenMatcher(False)
    assert not hm.match(Path(".foo"))
    assert hm.match(Path("foo"))

    hm = HiddenMatcher(True)
    assert hm.match(Path(".foo"))
    assert hm.match(Path("foo"))


def test_FilenameMather():
    fm = FilenameMather("foo", mode=FMM_RE)
    assert fm.match(Path("123foo123"))
    assert not fm.match(Path("123Foo123"))

    fm = FilenameMather(re.compile("foo"))
    assert fm.mode == FMM_RE

    fm = FilenameMather("foo", mode=FMM_EXACT)
    assert fm.match(Path("foo"))
    assert not fm.match(Path("foobar"))

    fm = FilenameMather("foo", mode=FMM_STR)
    assert fm.match(Path("123foo123"))
    assert not fm.match(Path("123Foo123"))

    fm = FilenameMather("foo*", mode=FMM_GLOB)
    assert fm.match(Path("foo123"))
    assert not fm.match(Path("Foo123"))
    assert not fm.match(Path("123foo"))

    fm = FilenameMather("foo", mode=FMM_RE, ignore_case=True)
    assert fm.match(Path("123foo123"))
    assert fm.match(Path("123Foo123"))

    fm = FilenameMather("foo", mode=FMM_EXACT, ignore_case=True)
    assert fm.match(Path("foo"))
    assert fm.match(Path("Foo"))

    fm = FilenameMather("foo", mode=FMM_STR, ignore_case=True)
    assert fm.match(Path("123foo123"))
    assert fm.match(Path("123Foo123"))


def test_SizeMatcher():
    class fakePath:
        def __init__(self, size: int):
            self.st_size = size

        def stat(self):
            return self

    sm = SizeMatcher(min=1024)
    assert not sm.match(fakePath(1000))  # type: ignore
    assert sm.match(fakePath(1025))  # type: ignore
    sm = SizeMatcher(max=1024)
    assert sm.match(fakePath(1000))  # type: ignore
    assert not sm.match(fakePath(1025))  # type: ignore
    sm = SizeMatcher(min=256, max=1024, within=True)
    assert not sm.match(fakePath(100))  # type: ignore
    assert sm.match(fakePath(1000))  # type: ignore
    assert not sm.match(fakePath(1025))  # type: ignore


def test_IgnoreFileMatcher():
    ...


def test_FileTypeMatcher():
    class fakePath:
        def __init__(self, mode: int, size: int = 0):
            self.st_mode = mode
            self.st_size = size

        def stat(self):
            return self

        def iterdir(self):
            if self.st_size > 0:
                yield "foo"

    ftm = FileTypeMatcher(FT_FILE)
    assert ftm.match(fakePath(stat.S_IFREG))  # type: ignore
    assert not ftm.match(fakePath(stat.S_IFDIR))  # type: ignore

    ftm = FileTypeMatcher(FT_DIRECTORY)
    assert not ftm.match(fakePath(stat.S_IFREG))  # type: ignore
    assert ftm.match(fakePath(stat.S_IFDIR))  # type: ignore

    ftm = FileTypeMatcher(FT_FILE, FT_DIRECTORY)
    assert ftm.match(fakePath(stat.S_IFREG))  # type: ignore
    assert ftm.match(fakePath(stat.S_IFDIR))  # type: ignore

    ftm = FileTypeMatcher(FT_SOCKET)
    assert ftm.match(fakePath(stat.S_IFSOCK))  # type: ignore
    assert not ftm.match(fakePath(stat.S_IFDIR))  # type: ignore

    ftm = FileTypeMatcher(FT_SYMLINK)
    assert ftm.match(fakePath(stat.S_IFLNK))  # type: ignore
    assert not ftm.match(fakePath(stat.S_IFDIR))  # type: ignore

    ftm = FileTypeMatcher(FT_PIPE)
    assert ftm.match(fakePath(stat.S_IFIFO))  # type: ignore
    assert not ftm.match(fakePath(stat.S_IFDIR))  # type: ignore

    ftm = FileTypeMatcher(FT_EXECUTABLE)
    assert ftm.match(fakePath(stat.S_IFREG | stat.S_IXUSR))  # type: ignore
    assert not ftm.match(fakePath(stat.S_IFREG))  # type: ignore

    ftm = FileTypeMatcher(FT_EMPTY)
    assert ftm.match(fakePath(stat.S_IFREG, 0))  # type: ignore
    assert not ftm.match(fakePath(stat.S_IFREG, 1))  # type: ignore
    assert ftm.match(fakePath(stat.S_IFDIR))  # type: ignore
    assert not ftm.match(fakePath(stat.S_IFDIR, 1))  # type: ignore
    assert not ftm.match(fakePath(stat.S_IFIFO))  # type: ignore


def test_SuffixMatcher():
    sm = SuffixMatcher(
        "py",
        "go",
    )
    assert sm.match(Path("foo.py"))
    assert sm.match(Path("foo.go"))

    assert not sm.match(Path("foo.cs"))
    assert not sm.match(Path("foo.cpp"))


def test_DepthMatcher():
    dm = DepthMatcher(Path("."), exact=2)
    assert not dm.match(Path("1"))
    assert dm.match(Path("1/2"))
    assert not dm.match(Path("1/2/3"))

    dm = DepthMatcher(Path("."), min=2)
    assert not dm.match(Path("1"))
    assert dm.match(Path("1/2"))
    assert dm.match(Path("1/2/3"))

    dm = DepthMatcher(Path("."), max=2)
    assert dm.match(Path("1"))
    assert dm.match(Path("1/2"))
    assert not dm.match(Path("1/2/3"))

    dm = DepthMatcher(Path("."), min=2, max=3, within=True)
    assert not dm.match(Path("1"))
    assert dm.match(Path("1/2"))
    assert dm.match(Path("1/2/3"))
    assert not dm.match(Path("1/2/3/4"))


def test_ChangeTimeMatcher():
    class fakePath:
        def __init__(self, t: datetime) -> None:
            self.st_mtime = t.timestamp()

        def stat(self):
            return self

    today = datetime.today()
    one_day = timedelta(days=1)
    one_min = timedelta(minutes=1)
    cm = ChangeTimeMatcher(newer=(today - one_day))
    assert cm.match(fakePath(today))  # type: ignore
    assert not cm.match(fakePath(today - 2 * one_day))  # type: ignore
    cm = ChangeTimeMatcher(older=(today - one_day))
    assert not cm.match(fakePath(today))  # type: ignore
    assert cm.match(fakePath(today - 2 * one_day))  # type: ignore
    cm = ChangeTimeMatcher(older=(today - one_day), newer=today, within=True)
    assert cm.match(fakePath(today - one_min))  # type: ignore
    assert not cm.match(fakePath(today - 2 * one_day))  # type: ignore


def test_MaxResultMatcher():
    mm = MaxResultMatcher()
    assert mm.match(Path("foo"))
    mm = MaxResultMatcher(2)
    assert mm.match(Path("1"))
    assert mm.match(Path("2"))
    assert not mm.match(Path("3"))


def test_MultiMatcher():
    mm = MultiMatcher(NopMatcher(), NopMatcher())
    assert mm.match(Path("foo"))
    mm = MultiMatcher(NopMatcher(), NotMatcher(NopMatcher()))
    assert not mm.match(Path("foo"))
