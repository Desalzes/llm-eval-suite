import re
from pathlib import Path

CSS = Path(__file__).resolve().parents[1] / "styles.css"


def _read():
    return CSS.read_text(encoding="utf-8")


def _mobile_block(css):
    """Return the body of the first @media block with max-width <= 600px, else ''."""
    m = re.search(r"@media[^{]*max-width:\s*(\d+)px[^{]*\{", css)
    if not m or int(m.group(1)) > 600:
        return ""
    depth, i = 1, m.end()
    while i < len(css) and depth:
        depth += {"{": 1, "}": -1}.get(css[i], 0)
        i += 1
    return css[m.end():i - 1]


def test_has_mobile_breakpoint():
    assert _mobile_block(_read()), "expected an @media (max-width: <=600px) block"


def test_nav_stacks_on_mobile():
    block = _mobile_block(_read())
    assert re.search(r"\.nav\b[^}]*flex-direction:\s*column", block, re.S), \
        ".nav must use flex-direction: column inside the mobile breakpoint"


def test_touch_target_min_height():
    heights = [int(x) for x in re.findall(r"\.btn[^}]*min-height:\s*(\d+)px", _read(), re.S)]
    assert heights and max(heights) >= 44, ".nav .btn must have min-height >= 44px"
