import os
import re
from collections import Counter
from contextlib import contextmanager
from os.path import isabs, join

from nose.plugins.skip import SkipTest
from testil import eq

from .. import ag as mod
from ...tests.util import do_command, gentest, TestConfig, test_app, tempdir


def test_ag():
    if not mod.is_ag_installed():
        raise SkipTest("ag not installed")
    @gentest
    def test(command, message="", selection="", state="window project(/) editor(/dir/b.txt)*"):
        cfg = {"command.ag.options": "--workers=1"}
        with test_app(state, cfg) as app, setup_files(test_app(app).tmp) as tmp:
            editor = app.windows[0].current_editor
            if selection:
                editor.document.text_storage[:] = selection
                editor.text_view = TestConfig(selectedRange=lambda:(0, len(selection)))
            output = do_command(command, editor)
            if output is not None:
                output = output.replace("xt://open/%s/" % tmp, "xt://open/")
                if "Traceback (most recent call last):" in output:
                    print(output)
                    assert "Traceback (most recent call last):" not in message
            assert_same_items(
                output.split("<br />"),
                markup(message).split("<br />"),
            )
            eq(test_app(app).state, state)

    yield test("ag ([bB]|size:\\ 10)",
        "[dir/B file](xt://open/dir/B%20file)\n"
        "[1](xt://open/dir/B%20file?goto=1):name: dir/[B](xt://open/dir/B%20file?goto=1.10.1) file\n"
        "[2](xt://open/dir/B%20file?goto=2):[size: 10](xt://open/dir/B%20file?goto=2.0.8)\n"
        "\n"
        "[dir/b.txt](xt://open/dir/b.txt)\n"
        "[1](xt://open/dir/b.txt?goto=1):name: dir/[b](xt://open/dir/b.txt?goto=1.10.1).txt\n")
    yield test("ag dir/[bB] ..",
        "[dir/B file](xt://open/dir/../dir/B%20file)\n"
        "[1](xt://open/dir/../dir/B%20file?goto=1):name: [dir/B](xt://open/dir/../dir/B%20file?goto=1.6.5) file\n"
        "\n"
        "[dir/b.txt](xt://open/dir/../dir/b.txt)\n"
        "[1](xt://open/dir/../dir/b.txt?goto=1):name: [dir/b](xt://open/dir/../dir/b.txt?goto=1.6.5).txt\n")
    yield test("ag dir/[bB] .. --after=1",
        "[dir/B file](xt://open/dir/../dir/B%20file)\n"
        "[1](xt://open/dir/../dir/B%20file?goto=1):name: [dir/B](xt://open/dir/../dir/B%20file?goto=1.6.5) file\n"
        "[2](xt://open/dir/../dir/B%20file?goto=2):size: 10\n\n"
        "\n"
        "[dir/b.txt](xt://open/dir/../dir/b.txt)\n"
        "[1](xt://open/dir/../dir/b.txt?goto=1):name: [dir/b](xt://open/dir/../dir/b.txt?goto=1.6.5).txt\n"
        "[2](xt://open/dir/../dir/b.txt?goto=2):size: 9\n\n")
    yield test("ag dir/b .. -i",
        "[dir/B file](xt://open/dir/../dir/B%20file)\n"
        "[1](xt://open/dir/../dir/B%20file?goto=1):name: [dir/B](xt://open/dir/../dir/B%20file?goto=1.6.5) file\n"
        "\n"
        "[dir/b.txt](xt://open/dir/../dir/b.txt)\n"
        "[1](xt://open/dir/../dir/b.txt?goto=1):name: [dir/b](xt://open/dir/../dir/b.txt?goto=1.6.5).txt\n")
    yield test("ag  ..",
        "[dir/B file](xt://open/dir/../dir/B%20file)\n"
        "[1](xt://open/dir/../dir/B%20file?goto=1):name: [dir/B ](xt://open/dir/../dir/B%20file?goto=1.6.6)file\n",
        selection="dir/B ")
    yield test("ag xyz", "no match for pattern: xyz")
    yield test("ag txt",
        "[dir/a.txt](xt://open/dir/a.txt)\n"
        "[1](xt://open/dir/a.txt?goto=1):name: dir/a.[txt](xt://open/dir/a.txt?goto=1.12.3)\n"
        "\n"
        "[dir/b.txt](xt://open/dir/b.txt)\n"
        "[1](xt://open/dir/b.txt?goto=1):name: dir/b.[txt](xt://open/dir/b.txt?goto=1.12.3)\n"
        "\n"
        "[e.txt](xt://open/e.txt)\n"
        "[1](xt://open/e.txt?goto=1):name: e.[txt](xt://open/e.txt?goto=1.8.3)\n")
    yield test("ag txt .",
        "[a.txt](xt://open/dir/./a.txt)\n"
        "[1](xt://open/dir/./a.txt?goto=1):name: dir/a.[txt](xt://open/dir/./a.txt?goto=1.12.3)\n"
        "\n"
        "[b.txt](xt://open/dir/./b.txt)\n"
        "[1](xt://open/dir/./b.txt?goto=1):name: dir/b.[txt](xt://open/dir/./b.txt?goto=1.12.3)\n")
    yield test("ag txt ..",
        "[dir/a.txt](xt://open/dir/../dir/a.txt)\n"
        "[1](xt://open/dir/../dir/a.txt?goto=1):name: dir/a.[txt](xt://open/dir/../dir/a.txt?goto=1.12.3)\n"
        "\n"
        "[dir/b.txt](xt://open/dir/../dir/b.txt)\n"
        "[1](xt://open/dir/../dir/b.txt?goto=1):name: dir/b.[txt](xt://open/dir/../dir/b.txt?goto=1.12.3)\n"
        "\n"
        "[e.txt](xt://open/dir/../e.txt)\n"
        "[1](xt://open/dir/../e.txt?goto=1):name: e.[txt](xt://open/dir/../e.txt?goto=1.8.3)\n")
    yield test("ag txt ...",
        "[dir/a.txt](xt://open/dir/a.txt)\n"
        "[1](xt://open/dir/a.txt?goto=1):name: dir/a.[txt](xt://open/dir/a.txt?goto=1.12.3)\n"
        "\n"
        "[dir/b.txt](xt://open/dir/b.txt)\n"
        "[1](xt://open/dir/b.txt?goto=1):name: dir/b.[txt](xt://open/dir/b.txt?goto=1.12.3)\n"
        "\n"
        "[e.txt](xt://open/e.txt)\n"
        "[1](xt://open/e.txt?goto=1):name: e.[txt](xt://open/e.txt?goto=1.8.3)\n")
    yield test("ag txt",
        "[a.txt](xt://open/dir/a.txt)\n"
        "[1](xt://open/dir/a.txt?goto=1):name: dir/a.[txt](xt://open/dir/a.txt?goto=1.12.3)\n"
        "\n"
        "[b.txt](xt://open/dir/b.txt)\n"
        "[1](xt://open/dir/b.txt?goto=1):name: dir/b.[txt](xt://open/dir/b.txt?goto=1.12.3)\n",
        state="window project editor(/dir/b.txt)*")
    yield test("ag xyz", "please specify a search path", state="window project editor*")


def test_exec_shell():
    if not mod.is_ag_installed():
        raise SkipTest("ag not installed")
    with setup_files() as tmp:
        result = mod.exec_shell(["ag", "dir/[bB]", "--workers=1"], cwd=tmp)

        assert_same_items(result.split("\n"), [
            'dir/B file:1:name: dir/B file',
            'dir/b.txt:1:name: dir/b.txt',
            '',
        ])
        eq(result.err, None)
        eq(result.returncode, 0)


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
            yield tmp
    else:
        do_setup(tmp)
        yield tmp


def markup(text, link=re.compile(r"\[([^\]]+)\]\(([^\)]+)\)")):
    return link.subn(r"<a href='\2'>\1</a>", text)[0].replace("\n", "<br />")
