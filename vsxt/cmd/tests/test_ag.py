import os
from collections import Counter
from contextlib import contextmanager
from os.path import isabs, join

from nose.plugins.skip import SkipTest
from testil import tempdir

from .. import ag as mod
from ...tests.util import async_test, do_command, FakeEditor, gentest


def test_ag():
    if not mod.is_ag_installed():
        raise SkipTest("ag not installed")

    @gentest
    @async_test
    async def test(command, items="", selection=""):
        with tempdir() as tmp, setup_files(tmp) as editor:
            result = await do_command(command, editor)
            actual_items = [
                f"{x['filepath'][len(tmp):]:<19} {x['detail']:<14} {x['label']}"
                for x in result["items"]
            ]
            assert_same_items(actual_items, items)

    yield test("ag ([bB]|size:\\ 10)", [
        "/dir/B file:0:10:1  dir/B file:1   name: dir/B file",
        "/dir/B file:1:0:8   dir/B file:2   size: 10",
        "/dir/b.txt:0:10:1   dir/b.txt:1    name: dir/b.txt",
    ])


def assert_same_items(lines1, lines2):
    """Assert items in the first sequence are the same as items in the second

    In this context, "same" means has the same number of occurrences of
    each item in each sequence. The order in which items occur in the
    sequences is not important. Items must be hashable.
    """
    def diff(first, second, second_name="second", occurrence_diff=True):
        for key, count in first.items():
            if key not in second:
                yield "{!r} not in {}".format(key, second_name)
            elif second[key] != count and occurrence_diff:
                yield "{!r} occurrences: {} != {}".format(key, count, second[key])

    counts1 = Counter(lines1)
    counts2 = Counter(lines2)
    if counts1 != counts2:
        result = ["items not equal"]
        result.extend(diff(counts1, counts2))
        result.extend(diff(counts2, counts1, "first", occurrence_diff=False))
        raise AssertionError("\n".join(result))


@contextmanager
def setup_files(tmp=None):
    def do_setup(tmp):
        os.mkdir(join(tmp, "dir"))
        for path in [
            "dir/a.txt",
            "dir/b.txt",
            "dir/B file",
            "e.txt",
        ]:
            assert not isabs(path), path
            with open(join(tmp, path), "w") as fh:
                fh.write("name: {}\nsize: {}".format(path, len(path)))
        assert " " not in tmp, tmp

    if tmp is None:
        with tempdir() as tmp:
            do_setup(tmp)
            yield FakeEditor(None, tmp)
    else:
        do_setup(tmp)
        yield FakeEditor(join(tmp, "dir/file"), tmp)