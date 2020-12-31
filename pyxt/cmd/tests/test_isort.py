import os
from os.path import isabs, join

from testil import eq, tempdir

from .. import isort as mod
from ...tests.util import (
    async_test,
    do_command,
    FakeEditor,
    gentest,
)


def test_isort_command():
    @gentest
    @async_test
    async def test(command, selection=(0, 0), expect=None):
        if expect is None:
            expect = SORTED_IMPORTS
        editor = FakeEditor(__file__, text=UNSORTED_IMPORTS)
        editor.selection = selection
        await do_command(command, editor)
        eq(await editor.get_text(), expect)

    yield test("isort")
    yield test("isort editxt", expect=SORTED_EDITXT_IMPORTS)
    yield test("isort", (1, 106), """
import os
import sys

from editxt import Object, Object2, Object3

""" + UNSORTED_IMPORTS[107:])


def test_default_package():
    with tempdir() as tmp:
        os.mkdir(join(tmp, "dir"))
        os.mkdir(join(tmp, "dir/package"))
        os.mkdir(join(tmp, "dir/other"))
        for path in [
            "dir/package/__init__.py",
            "dir/other/b.txt",
        ]:
            assert not isabs(path), path
            with open(join(tmp, path), "w"):
                pass

        @async_test
        async def test(path, result=""):
            filepath = 'file' if path is None else join(tmp, path)
            editor = FakeEditor(filepath)
            eq(await mod.default_package(editor), result)

        yield test, None
        yield test, "dir/mod.py"
        yield test, "dir/other/mod.py"
        yield test, "dir/package/mod.py", "package"


UNSORTED_IMPORTS = """
from editxt import Object

import os

from editxt import Object3

from editxt import Object2

import sys

from third_party import lib15, lib1, lib2, lib3, lib4, lib5, lib6, lib7, lib8, lib9, lib10, lib11, lib12, lib13, lib14

import sys

from __future__ import absolute_import

from third_party import lib3

print("yo")
"""

SORTED_IMPORTS = """
from __future__ import absolute_import

import os
import sys

from editxt import Object, Object2, Object3
from third_party import (
    lib1,
    lib2,
    lib3,
    lib4,
    lib5,
    lib6,
    lib7,
    lib8,
    lib9,
    lib10,
    lib11,
    lib12,
    lib13,
    lib14,
    lib15,
)

print("yo")
"""

SORTED_EDITXT_IMPORTS = """
from __future__ import absolute_import

import os
import sys

from third_party import (
    lib1,
    lib2,
    lib3,
    lib4,
    lib5,
    lib6,
    lib7,
    lib8,
    lib9,
    lib10,
    lib11,
    lib12,
    lib13,
    lib14,
    lib15,
)

from editxt import Object, Object2, Object3

print("yo")
"""
