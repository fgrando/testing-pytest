from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO_A = ROOT / "repos" / "software"
REPO_B = ROOT / "repos" / "configtool"

FOO_HEADER = REPO_A / "include" / "foo_config.h"
BAR_XML = REPO_B / "config" / "bar.xml"
SHARED_PROTO = REPO_A / "shared" / "protocol.h"
SHARED_PROTO_DUP = REPO_B / "shared" / "protocol.h"
LICENSE_A = REPO_A / "LICENSE"
LICENSE_B = REPO_B / "LICENSE"
