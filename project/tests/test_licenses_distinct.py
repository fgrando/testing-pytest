import paths
from catalog import files_differ


def test_licenses_are_distinct():
    """Each repo's LICENSE is its own — not a copy-paste of the other."""
    assert files_differ(
        paths.LICENSE_A, paths.LICENSE_B
    ), "LICENSE files are identical; one was likely copied by mistake"
