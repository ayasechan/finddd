import os
import re
from concurrent.futures import ThreadPoolExecutor
from multiprocessing import cpu_count
from pathlib import Path
from typing import Callable, Union

from finddd.match import *

DEFAULT_EXECUTOR_NUM = cpu_count()


class Finder:
    exclude: list[str]

    def __init__(self) -> None:
        self.threads = DEFAULT_EXECUTOR_NUM
        self.exclude = []
        self.glob = False
        self.hidden = False
        self.no_ignore = True
        self.ignore_case = False
        self.follow = False

    def find(
        self,
        pattern: Union[str, re.Pattern[str]],
        path: Path,
        cb: Callable[[Path], None],
        *,
        size_min: Optional[int] = None,
        size_max: Optional[int] = None,
        size_within: bool = False,
        time_newer: Optional[datetime] = None,
        time_older: Optional[datetime] = None,
        time_within: bool = False,
        filetypes: list[Union[FileType, str]] = [],
        depth_exact: Optional[int] = None,
        depth_min: Optional[int] = None,
        depth_max: Optional[int] = None,
        depth_within: bool = False,
        suffixes: list[str] = [],
        exclude: list[str] = [],
        max_result: int = 0,
        threads: Optional[int] = None,
    ) -> None:
        cmm = MultiMatcher()
        nmm = MultiMatcher()

        dmm = MultiMatcher()
        fmm = MultiMatcher()

        nmm.add(HiddenMatcher(self.hidden))
        nmm.add(
            *(
                NotMatcher(
                    FilenameMather(
                        i, mode=FilenameMatchMode.FMM_GLOB, ignore_case=self.ignore_case
                    )
                )
                for i in [*self.exclude, *exclude]
            )
        )
        nmm.add(IgnoreFileMatcher(enable=self.no_ignore))

        cmm.add(nmm)
        cmm.add(FileTypeMatcher(*filetypes))  # type: ignore
        cmm.add(
            DepthMatcher(
                path,
                exact=depth_exact,
                min=depth_min,
                max=depth_max,
                within=depth_within,
            )
        )
        cmm.add(
            ChangeTimeMatcher(older=time_older, newer=time_newer, within=time_within)
        )
        cmm.add(FilenameMather(pattern, ignore_case=self.ignore_case))

        fmm.add(SizeMatcher(min=size_min, max=size_max, within=size_within))
        fmm.add(SuffixMatcher(*suffixes))

        # add MaxResultMatcher last
        mrm = MaxResultMatcher(max_result)
        fmm.add(cmm, mrm)
        dmm.add(cmm, mrm)

        def g(cwd: str, l: list[str], m: Matcher):
            l2 = (Path(cwd) / i for i in l)
            return (i for i in l2 if m.match(i))

        files: list[Path] = []
        for cwd, ds, nonds in os.walk(path, followlinks=self.follow):
            files = [*files, *g(cwd, ds, dmm), *g(cwd, nonds, fmm)]
            ds[:] = [i.name for i in g(cwd, ds, nmm)]

        with ThreadPoolExecutor(threads if threads else self.threads) as pool:
            list(pool.map(cb, files))


_finder = Finder()
find = _finder.find
