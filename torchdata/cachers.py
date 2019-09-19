r"""**This module contains interface needed for cachers and basic memory and disk implementations.**


To cache on disk all samples using Python's `pickle` in folder `cache`
(assuming you have already created `torchdata.Dataset` instance named `dataset`)::

    dataset.cache(torchdata.cachers.Pickle("./cache"))

Users are encouraged to write their custom `cachers` if the ones provided below
are too slow or not good enough for their purposes (see `Cacher` abstract interface below).

"""

import abc
import pathlib
import pickle
import shutil
import typing

from ._base import Base


class Cacher(Base):
    r"""**Interface defining interface to be compatible with** `torchdata.Dataset.cache` **method.**

    If you want to implement your own `caching` functionality, inherit from
    this class and implement methods described below.
    """

    @abc.abstractmethod
    def __contains__(self, index: int) -> bool:
        r"""**Return true if sample under** `index` **is cached.**

        If `False` returned, cacher's `__setitem__` will be called, hence if you are not
        going to cache sample under this `index`, you should describe this operation
        at that method.
        This is simply a boolean indicator whether sample is cached.

        If `True` cacher's `__getitem__` will be called and it's users responsibility
        to return correct value in such case.

        Parameters
        ----------
        index : int
                Index of sample
        """

    # Save if doesn't contain
    @abc.abstractmethod
    def __setitem__(self, index: int, data: typing.Any) -> None:
        r"""**Saves sample under index in cache or do nothing.**

        This function should save sample under `index` to be later
        retrieved by `__getitem__`.
        If you don't want to save specific `index`, you can implement this functionality
        in `cacher` or create separate `modifier` solely for this purpose
        (second approach is highly recommended).

        Parameters
        ----------
        index : int
                Index of sample
        data : Any
                Data generated by dataset.
        """

    # Save if doesn't contain
    @abc.abstractmethod
    def __getitem__(self, index) -> typing.Any:
        r"""**Retrieve sample from cache.**

        **This function MUST return valid data sample and it's users responsibility
        if custom cacher is implemented**.

        Return from this function datasample which lies under it's respective
        `index`.

        Parameters
        ----------
        index : int
                Index of sample
        """


class Pickle(Cacher):
    r"""**Save and load data from disk using** `pickle` **module.**

    Data will be saved as `.pkl` in specified path. If path does not exist,
    it will be created.

    **This object can be used as a** `context manager` ** and it will delete files at the end of block::**

        with torchdata.cachers.Pickle(pathlib.Path("./disk")) as pickler:
            dataset = dataset.map(lambda x: x+1).cache(pickler)
            ... # Do something with dataset
        ... # Files on disk will be removed

    You can also issue `clean()` method manually for the same effect
    (though it's discouraged as you might crash `__setitem__` method).

    **Important:**

    This `cacher` can act between consecutive runs, just don't use `clean()` method
    or don't delete the folder manually. If so, **please ensure correct sampling**
    (same seed and sampling order) for reproducible behaviour between runs.

    Attributes
    ----------
    path: pathlib.Path
            Path to the folder where samples will be saved and loaded from.
    extension: str
            Extension to use for saved pickle files. Default: `.pkl`

    """

    def __init__(self, path: pathlib.Path, extension: str = ".pkl"):
        self.path: pathlib.Path = path
        self.path.mkdir(parents=True, exist_ok=True)
        self.extension: str = extension

    def __contains__(self, index: int) -> bool:
        return pathlib.Path(
            (self.path / str(index)).with_suffix(self.extension)
        ).is_file()

    def __setitem__(self, index: int, data: int):
        with open((self.path / str(index)).with_suffix(self.extension), "wb") as file:
            pickle.dump(data, file)

    def __getitem__(self, index: int):
        with open((self.path / str(index)).with_suffix(self.extension), "rb") as file:
            return pickle.load(file)

    def clean(self) -> None:
        """**Remove (non-recursively) files residing in** `self.path`.

        Behaves just like `shutil.rmtree`, but won't act if directory does not exist.
        """

        if self.path.is_dir():
            shutil.rmtree(self.path)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.clean()


class Memory(Cacher):
    r"""**Save and load data in Python dictionary**.

    This `cacher` is used by default inside `torchdata.Dataset`.

    """

    def __init__(self):
        self.cache = {}

    def __contains__(self, index: int) -> bool:
        return index in self.cache

    def __setitem__(self, index: int, data: int):
        self.cache[index] = data

    def __getitem__(self, index: int):
        return self.cache[index]