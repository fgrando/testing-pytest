import re
import paths
from catalog import read_text


def test_header_has_guard():
    """foo_config.h uses an include guard (or #pragma once)."""
    text = read_text(paths.FOO_HEADER)
    assert "#pragma once" in text or re.search(
        r"#ifndef\s+\w+_H", text
    ), "no include guard found in foo_config.h"
