"""Download Noto Sans JP into assets/fonts/.

Why a separate script: the font is licensed under SIL OFL-1.1 and large
enough that we keep it out of the repo to stay slim and avoid bundling
binary assets with their own license. Run this once after cloning, or
let the daily-publish workflow cache it.

The fallback PIL bitmap font in cli.py covers Step 1 smoke-tests, so
this script is optional until Step 3 (PIL text overlay).
"""

from __future__ import annotations

import sys
import urllib.request
from pathlib import Path

# notofonts/noto-cjk dropped the per-region OTF subset (NotoSansJP-Regular)
# from main; the full CJK-JP regular OTF is the stable, region-targeted
# replacement. Larger (~16MB) but covers all required JP glyphs and the
# OFL-1.1 license stays unchanged.
NOTO_SANS_JP_URL = (
    "https://github.com/notofonts/noto-cjk/raw/main/Sans/OTF/Japanese/NotoSansCJKjp-Regular.otf"
)
DEST = Path(__file__).resolve().parent.parent / "assets" / "fonts" / "NotoSansJP-Regular.otf"


def main() -> int:
    DEST.parent.mkdir(parents=True, exist_ok=True)
    if DEST.exists():
        print(f"already present: {DEST}")
        return 0
    print(f"downloading {NOTO_SANS_JP_URL}")
    urllib.request.urlretrieve(NOTO_SANS_JP_URL, DEST)
    print(f"saved: {DEST} ({DEST.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
