import os
import re
from collections import Counter
from contextlib import contextmanager
from dataclasses import dataclass
from os.path import isabs, join
from pathlib import Path

from nose.plugins.skip import SkipTest
from testil import eq, Regex, tempdir

from .. import ag as mod
from ...tests.util import (
    async_test,
    do_command,
    get_completions,
    FakeEditor,
    gentest,
)


def test_ag():
    if not mod.is_ag_installed():
        raise SkipTest("ag not installed")

    with setup_files() as tmp:
        @gentest
        @async_test
        async def test(command, items, opts=None, **editor_props):
            editor = FakeEditor(join(tmp, "dir/file"), tmp)
            for name, val in editor_props.items():
                setattr(editor, name, val)
            result = await do_command(command, editor)
            actual_items = [
                f"{x.get('filepath', '')[len(tmp):]:<26} "
                f"{x.get('detail', ''):<15} {x['label']}"
                f"{(' ' + x['description']) if 'description' in x else ''}"
                for x in result["items"]
            ]
            assert_same_items(actual_items, items)
            discard = {"items", "type"}
            actual_opts = {k: v for k, v in result.items() if k not in discard}
            if opts is None:
                opts = {"filter_results": True, "value": None}
            eq(actual_opts, opts)

        yield test("ag ([bB]|size:\\ 10)", [
            "/dir/B file:0:10:1                         1: name: dir/B file",
            "/dir/B file:1:0:8          dir/B file      2: size: 10",
            "/dir/b.txt:0:10:1          dir/b.txt       1: name: dir/b.txt",
        ])
        yield test("ag dir/[bB] ..", [
            "/dir/../dir/B file:0:6:5   dir/B file      1: name: dir/B file",
            "/dir/../dir/b.txt:0:6:5    dir/b.txt       1: name: dir/b.txt",
        ])
        yield test("ag dir/[bB] .. --after=1", [
            "/dir/../dir/B file:0:6:5                   1: name: dir/B file",
            "/dir/../dir/B file:1       dir/B file      2: size: 10",
            "/dir/../dir/b.txt:0:6:5                    1: name: dir/b.txt",
            "/dir/../dir/b.txt:1        dir/b.txt       2: size: 9",
        ])
        yield test("ag dir/b .. -i", [
            "/dir/../dir/B file:0:6:5   dir/B file      1: name: dir/B file",
            "/dir/../dir/b.txt:0:6:5    dir/b.txt       1: name: dir/b.txt",
        ])

        yield test("ag  ..", [
            "/dir/../dir/B file:0:6:6   dir/B file      1: name: dir/B file",
        ], selection="dir/B ")

        yield test("ag txt", [
            "/dir/a.txt:0:12:3          dir/a.txt       1: name: dir/a.txt",
            "/dir/b.txt:0:12:3          dir/b.txt       1: name: dir/b.txt",
            "/e.txt:0:8:3               e.txt           1: name: e.txt",
        ])
        yield test("ag txt .", [
            "/dir/./a.txt:0:12:3        a.txt           1: name: dir/a.txt",
            "/dir/./b.txt:0:12:3        b.txt           1: name: dir/b.txt",
        ])
        yield test("ag txt ..", [
            "/dir/../dir/a.txt:0:12:3   dir/a.txt       1: name: dir/a.txt",
            "/dir/../dir/b.txt:0:12:3   dir/b.txt       1: name: dir/b.txt",
            "/dir/../e.txt:0:8:3        e.txt           1: name: e.txt",
        ])
        yield test("ag txt ...", [
            "/dir/a.txt:0:12:3          dir/a.txt       1: name: dir/a.txt",
            "/dir/b.txt:0:12:3          dir/b.txt       1: name: dir/b.txt",
            "/e.txt:0:8:3               e.txt           1: name: e.txt",
        ])
        yield test("ag txt", [
            "/dir/a.txt:0:12:3          a.txt           1: name: dir/a.txt",
            "/dir/b.txt:0:12:3          b.txt           1: name: dir/b.txt",
        ], project_path=None)

        yield test("ag xyz", [
            "                                            no match"
        ], opts={"value": "ag xyz"})
        yield test("ag ", [
            "                                            pattern is required"
        ], opts={"value": "ag "})
        yield test("ag xxxx", [
            "                                            path is required"
        ], file_path=None, project_path=None, opts={"value": "ag xxxx"})


@async_test
async def test_ag_error():
    with tempdir() as tmp:
        command = "ag x xxxx"
        editor = FakeEditor(join(tmp, "file"))
        result = await do_command(command, editor)
        item, = result["items"]
        eq(item["description"], Regex("No such file or directory:"))
        eq(result["value"], command)
        assert "filter_results" not in result, result


@async_test
async def test_ag_help():
    with tempdir() as tmp:
        command = "ag x . --help"
        editor = FakeEditor(join(tmp, "file"))
        result = await do_command(command, editor)
        assert len(result["items"]) > 1, result
        result.pop("items")
        eq(result["value"], None)


def test_ag_completions():
    with tempdir() as tmp:
        (Path(tmp) / "dir").mkdir()

        @gentest
        @async_test
        async def test(cmd, description, label="", project_path=None, items=()):
            editor = FakeEditor(join(tmp, "dir/file"), project_path or tmp)
            editor.selection = "b "
            result = await get_completions(cmd, editor)
            items = list(items)
            if description is not None:
                items.insert(0, {
                    "label": label or cmd,
                    "description": description,
                    "offset": 0,
                })
            eq(result["items"], items)
            eq(result["value"], cmd)

        yield test("ag ", "/b\\ / /dir options ...", project_path="/dir")
        yield test("ag 'x ", "/dir options ...", "ag 'x '", project_path="/dir")
        yield test("ag x dir/", "options ...")
        yield test("ag x dir/ ", "options ...")
        yield test("ag x dir/  ", None)
        yield test("ag x ../", "options ...", items=[
            {"label": "dir/", "is_completion": True, "offset": 8},
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
def setup_files():
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

    with tempdir() as tmp:
        do_setup(tmp)
        yield tmp


@dataclass
class Pattern:
    cmdstr: str

    def __eq__(self, other):
        pattern = re.compile("ag " + re.escape(other) + "( .*)?$")
        return pattern.match(self.cmdstr.replace("\\ ", " "))
