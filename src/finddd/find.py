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
        mm = MultiMatcher()
        mm.add(HiddenMatcher(self.hidden))
        # mm.add(IgnoreFileMatcher())
        mm.add(SizeMatcher())
        mm.add(FileTypeMatcher())
        mm.add(SuffixMatcher())
        mm.add(DepthMatcher(path))
        mm.add(ChangeTimeMatcher())
        mm.add(FilenameMather(pattern, ignore_case=self.ignore_case))
        mm.add(
            *(
                NotMatcher(
                    FilenameMather(
                        i, mode=FilenameMatchMode.FMM_GLOB, ignore_case=self.ignore_case
                    )
                )
                for i in self.exclude
            )
        )
        mm.add(MaxResultMatcher())

        files: tuple[Path, ...] = ()
        for cwd, ds, fs in os.walk(path, followlinks=self.follow):

            def g(l: list[str]):
                l2 = (Path(cwd) / i for i in l)
                return (i for i in l2 if mm.match(i))

            files = (*files, *g(ds), *g(fs))

        with ThreadPoolExecutor(self.threads) as pool:
            pool.map(cb, files)
