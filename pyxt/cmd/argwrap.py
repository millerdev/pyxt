import logging
import re
from itertools import tee

from ..command import command

log = logging.getLogger(__name__)


async def default_scope(editor):
    a, b = await editor.selection() or (0, 0)
    return "all" if a == b else "selection"


@command()
async def argwrap(editor, args):
    """Wrap/unwrap arguments of a function or other comma-delimited structure

    Wrap if the selection spans a single line, unwrap if it spans
    multiple lines.
    """
    full_text = await editor.get_text()
    selections = await editor.selections()
    texts = []
    ranges = []
    for sel in reversed(selections):
        text, rng = toggle_wrap(
            full_text,
            sel,
            await editor.eol,
            await editor.insert_spaces,
            await editor.tab_size,
            trailing_comma=True,
        )
        texts.append(text)
        ranges.append(rng)
    await editor.set_texts(texts, ranges)


def toggle_wrap(text, sel, eol, insert_spaces, tab_size, trailing_comma):
    rng = sorted(sel)
    if should_wrap(text, rng, eol):
        parts, rng = split_line(text, rng[0], eol)
        if not parts:
            i0, i1 = sorted(sel)
            return text[i0:i1], sel
        return wrap(parts, eol, insert_spaces, tab_size, trailing_comma), rng
    return unwrap(split_lines(text, rng, eol)), sel


def should_wrap(text, rng, eol):
    i0, i1 = rng
    assert i0 <= i1, rng
    region = text[i0:i1]
    if region.endswith(eol):
        region = region[:-len(eol)]
    return eol not in region


def wrap(parts, eol, insert_spaces, tab_size, trailing_comma):
    line1 = parts[0]
    indent1 = line1[:len(line1) - len(line1.lstrip())]
    indent2 = (" " * tab_size) if insert_spaces else "\t"
    end1 = eol + indent1 + indent2
    end2 = eol + indent1
    comma = "," if trailing_comma and not parts[-2].endswith(",") else ""
    return end1.join(parts[:-1]) + comma + end2 + parts[-1]


def unwrap(lines, arg_delim=","):
    def iter_parts(lines):
        delim_len = len(arg_delim)
        end_delims = tuple(DELIMS.values())
        lines, nextlines = tee(lines)
        next(nextlines, None)
        for not_first, (line, nextline) in enumerate(zip(lines, nextlines)):
            part = line.strip() if not_first else line.rstrip()
            part2 = nextline.lstrip()
            if part.endswith(arg_delim):
                if part2.startswith(end_delims):
                    part = part[:-delim_len]
                    yield part
                else:
                    yield part
                    yield " "
            else:
                yield part
        yield nextline.lstrip()
    return "".join(iter_parts(lines))


def split_line(text, index, eol="\n", start_delim=None):
    text, rng = _get_line(text, index, eol)
    parts = list(_iter_split(text, index, start_delim))
    return parts, rng


def _iter_split(text, cursor_index, start_delim):
    start_delims = start_delim or ''.join(DELIMS)
    start_delims_regex = re.compile(f"[{re.escape(start_delims)}]")
    for delim_iter, match_index in [
        (start_delims_regex.finditer(text, 0, cursor_index), -1),
        (start_delims_regex.finditer(text, cursor_index), 0),
    ]:
        matches = list(delim_iter)
        if matches:
            start_index = index = matches[match_index].start()
            start_delim = matches[match_index].group()
            break
    else:
        return  # start delimiter not found

    end_delim = DELIMS[start_delim]
    if end_delim not in text[start_index:]:
        return
    if len(end_delim) > 1:
        raise NotImplementedError(repr(end_delim))

    end_delims = set(DELIMS.values())
    assert len(DELIMS) == len(end_delims), DELIMS
    parens = ''.join(re.escape(c) for c in set(DELIMS) | end_delims)
    delims = re.compile(fr"(?:[,{parens}]|\\*['\"])")

    level = 0
    in_string = ''
    for match in delims.finditer(text, index):
        delim = match.group()
        if in_string:
            if delim.endswith(in_string) and len(delim) % 2 != 0:
                in_string = ''
            continue
        if delim.endswith(('"', "'")):
            in_string = delim[-1]
            continue
        if delim in DELIMS:
            level += 1
            if index == start_index:
                index = match.end()
                yield text[:index]
            continue
        elif not level:
            if delim == end_delim and cursor_index < match.end():
                # abort if cursor is before unbalanced end delimiter
                break
            continue  # ignore delimiters up to start delim
        if level > 1:
            if delim in end_delims:
                level -= 1
            continue
        if delim == ",":
            end = match.end()
            yield text[index:end].lstrip()
            index = end
            continue
        assert delim == end_delim, f"unknown delimiter: {delim!r}"
        yield text[index:match.start()].lstrip()
        yield text[match.start():]
        break


def split_lines(text, rng, eol):
    i0, i1 = rng
    region = text[i0:i1]
    if eol not in region:
        return [region]
    parts = region.split(eol)
    if not parts[-1]:
        parts[-2:] = [eol.join(parts[-2:])]
    return parts


def _get_line(text, index, eol):
    start = text.rfind(eol, 0, index)
    if start < 0:
        start = 0
    else:
        start += len(eol)
    end = text.find(eol, index)
    if end < 0:
        end = len(text)
    return text[start:end], (start, end)


DELIMS = {"(": ")", "[": "]", "{": "}"}
