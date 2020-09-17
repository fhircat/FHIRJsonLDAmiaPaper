from dataclasses import dataclass
from typing import ClassVar, List, Union, Dict, Optional, Callable, Generator, Any, Iterator


class SummaryElement:
    def __init__(self, title: str, print_progress: bool=False) -> None:
        self.title = title
        self.print_progress = print_progress
        self.owner: Optional["Heading"] = None

    @property
    def children(self) -> Iterator["SummaryElement"]:
        return [getattr(self, e) for e in dir(self) if e.startswith('n') and isinstance(getattr(self, e), SummaryElement)]


class Heading(SummaryElement):

    @property
    def count(self) -> int:
        return sum(e.count for e in self.children)

    def summary(self, indent: str= "") -> List[str]:
        rval = [f"{indent}{str(self)}"]
        for e in self.children:
            rval += e.summary(indent+"  ")
        return rval

    def __setattr__(self, key: str, value: Any):
        if key != 'owner' and isinstance(value, SummaryElement):
            value.owner = self
        super().__setattr__(key, value)

    def __str__(self):
        return f"Number of {self.title}: {self.count}"


class Counter(SummaryElement):
    def __init__(self, title: str, print_progress: bool=False) -> None:
        self.count = 0
        super().__init__(title, print_progress)

    def summary(self, indent: str) -> List[str]:
        return [f"{indent}{str(self)}"]

    def inc(self, filename: str):
        self.count += 1
        if self.print_progress:
            print(f"{filename}: {self.title} (total: {self.count})")

    def __str__(self):
        return f"Number of {self.title}: {self.count}"


