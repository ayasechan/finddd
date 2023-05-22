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
                for i in self.exclude
            )
        )
        # nmm.add(IgnoreFileMatcher())
        cmm.add(nmm)
        cmm.add(FileTypeMatcher())
        cmm.add(DepthMatcher(path))
        cmm.add(ChangeTimeMatcher())
        cmm.add(FilenameMather(pattern, ignore_case=self.ignore_case))

        fmm.add(SizeMatcher())
        fmm.add(SuffixMatcher())

        # add MaxResultMatcher last
        mrm = MaxResultMatcher()
        fmm.add(cmm, mrm)
        dmm.add(cmm, mrm)

        files: tuple[Path, ...] = ()
        for cwd, ds, nonds in os.walk(path, followlinks=self.follow):

            def g(l: list[str], m: Matcher):
                l2 = (Path(cwd) / i for i in l)
                return (i for i in l2 if m.match(i))

            files = (*files, *g(ds, dmm), *g(nonds, fmm))
            ds[:] = [i.name for i in g(ds, nmm)]

        with ThreadPoolExecutor(self.threads) as pool:
            list(pool.map(cb, files))
