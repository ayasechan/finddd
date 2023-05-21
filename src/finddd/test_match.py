from datetime import timedelta
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
    ...


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
    ...


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
    ...


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
