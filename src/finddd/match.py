import abc
import fnmatch
import re
import stat
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Callable, Optional, Union


class Matcher(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def match(self, path: Path) -> bool:
        raise NotImplementedError


class NotMatcher(Matcher):
    def __init__(self, matcher: Matcher):
        self.matcher = matcher

    def match(self, path: Path) -> bool:
        return not self.matcher.match(path)


class NopMatcher(Matcher):
    def match(self, path: Path) -> bool:
        return True


class FilenameMatchMode(Enum):
    FMM_EXACT = 0
    FMM_STR = 1
    FMM_GLOB = 2
    FMM_RE = 3


class FilenameMather(Matcher):
    def __init__(
        self,
        pattern: Union[str, re.Pattern[str]],
        *,
        ignore_case: bool = False,
        mode: FilenameMatchMode = FilenameMatchMode.FMM_STR,
    ):
        if (
            ignore_case
            and isinstance(pattern, str)
            and mode != FilenameMatchMode.FMM_RE
        ):
            pattern = pattern.lower()

        if isinstance(pattern, re.Pattern):
            mode = FilenameMatchMode.FMM_RE
        if mode == FilenameMatchMode.FMM_RE and isinstance(pattern, str):
            pattern = re.compile(pattern)
        self.mode = mode
        self.pattern = pattern
        self.ignore_case = ignore_case

    def match(self, path: Path) -> bool:  # type: ignore
        name = path.name
        if self.ignore_case:
            name = name.lower()
        if self.mode == FilenameMatchMode.FMM_EXACT:
            return path.name == self.pattern
        if self.mode == FilenameMatchMode.FMM_STR:
            return self.pattern in path.name  # type: ignore
        if self.mode == FilenameMatchMode.FMM_GLOB:
            return fnmatch.fnmatch(path.name, self.pattern)  # type: ignore
        if self.mode == FilenameMatchMode.FMM_RE:
            return self.pattern.match(path.name)  # type: ignore
        assert isinstance(self.mode, FilenameMatchMode)


class SizeMatcher(Matcher):
    def __init__(
        self,
        *,
        min: Optional[int] = None,
        max: Optional[int] = None,
        within: bool = False,
    ):
        if within:
            assert min is not None
            assert max is not None
            assert min < max

        self.max = max
        self.min = min
        self.within = within

    def match(self, path: Path) -> bool:
        s = path.stat().st_size
        if self.within:
            return self.min < s < self.max  # type: ignore
        if self.min:
            return s > self.min
        if self.max:
            return s < self.max

        return True


class HiddenMatcher(Matcher):
    def __init__(self, hidden: bool = False):
        self.hidden = hidden

    def match(self, path: Path) -> bool:
        if self.hidden:
            return True
        return not path.name.startswith(".")


class IgnoreFileMatcher(Matcher):
    def __init__(self):
        pass

    def match(self, path: Path) -> bool:
        raise NotImplementedError
        return True


class FileType(Enum):
    FT_DIRECTORY = "d"
    FT_FILE = "f"
    FT_SYMLINK = "l"
    FT_EXECUTABLE = "x"
    FT_EMPTY = "e"
    FT_SOCKET = "s"
    FT_PIPE = "p"


class FileTypeMatcher(Matcher):
    def __init__(self, *types: FileType):
        self.types = types

    def match(self, path: Path) -> bool:
        if self.types:
            ps = path.stat()
            mode = ps.st_mode

            def is_excutable():
                raise NotImplementedError
                return False

            def is_empty() -> bool:
                if stat.S_ISDIR(mode):
                    return len(list(path.iterdir())) == 0
                if stat.S_ISREG(mode):
                    return ps.st_size == 0
                return False

            fns: dict[str, Callable[[], bool]] = {
                "d": lambda: stat.S_ISDIR(mode),
                "f": lambda: stat.S_ISREG(mode),
                "l": lambda: stat.S_ISLNK(mode),
                "x": is_excutable,
                "e": is_empty,
                "s": lambda: stat.S_ISSOCK(mode),
                "p": lambda: stat.S_ISFIFO(mode),
            }
            return any(fns.get(i, lambda _: False)() for i in self.types)  # type: ignore
        return True


class SuffixMatcher(Matcher):
    def __init__(self, *suffixes: str):
        self.suffixes = [(i if i.startswith(".") else f".{i}") for i in suffixes if i]

    def match(self, path: Path) -> bool:
        if self.suffixes:
            return path.suffix in self.suffixes
        return True


class DepthMatcher(Matcher):
    def __init__(
        self,
        cur: Path,
        *,
        max: Optional[int] = None,
        min: Optional[int] = None,
        exact: Optional[int] = None,
    ):
        self.cur = cur
        self.max = max
        self.min = min
        self.exact = exact

    def match(self, path: Path) -> bool:
        depth = len(path.parts) - len(self.cur.parts)
        assert depth >= 0
        if self.exact is not None:
            return self.exact == depth
        if self.min is not None:
            return depth > self.min
        if self.max is not None:
            return depth < self.max
        return True


class ChangeTimeMatcher(Matcher):
    def __init__(
        self,
        *,
        older: Optional[datetime] = None,
        newer: Optional[datetime] = None,
        within: bool = False,
    ):
        if within:
            assert newer is None
            assert older is None
            assert older < newer  # type: ignore

        self.newer = newer
        self.older = older
        self.within = within

    def match(self, path: Path) -> bool:
        t = datetime.fromtimestamp(path.stat().st_mtime_ns)
        if self.within:
            return self.older < t < self.newer  # type: ignore
        if self.newer is not None:
            return t > self.newer
        if self.older is not None:
            return t < self.older
        return True


class MaxResultMatcher(Matcher):
    def __init__(self, max: int = 0):
        self._count = 0
        self.max = max

    def match(self, path: Path) -> bool:
        if self.max > 0:
            ok = self._count < self.max
            self._count += 1
            return ok
        return True


class MultiMatcher(Matcher):
    def __init__(self, *matchers: Matcher):
        self.matchers = matchers

    def add(self, *matchers: Matcher):
        self.matchers = (*self.matchers, *matchers)

    def match(self, path: Path) -> bool:
        if self.matchers:
            return all(i.match(path) for i in self.matchers)
        return True
