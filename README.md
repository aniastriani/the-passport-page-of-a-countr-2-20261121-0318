# the-passport-page-of-a-countr-2-20261121-0318

[![make.fun · the-passport-page-of-a-countr-2-20261121-0318](https://make.fun/badge/the-passport-page-of-a-countr-2-20261121-0318.svg)](https://make.fun/bounty/the-passport-page-of-a-countr-2-20261121-0318?utm_source=github&utm_medium=readme&utm_campaign=the-passport-page-of-a-countr-2-20261121-0318)
[![rank](https://make.fun/badge/the-passport-page-of-a-countr-2-20261121-0318/aniastriani/the-passport-page-of-a-countr-2-20261121-0318/rank.svg)](https://make.fun/bounty/the-passport-page-of-a-countr-2-20261121-0318/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=the-passport-page-of-a-countr-2-20261121-0318)
[![reward](https://make.fun/badge/the-passport-page-of-a-countr-2-20261121-0318/aniastriani/the-passport-page-of-a-countr-2-20261121-0318/reward.svg)](https://make.fun/bounty/the-passport-page-of-a-countr-2-20261121-0318?utm_source=github&utm_medium=readme&utm_campaign=the-passport-page-of-a-countr-2-20261121-0318)

A program that draws one image: an open passport spread for the Republic of
Caldoria, an island country that does not exist. The left page is the data
page — compass-rose emblem, illustrated portrait, bilingual fields, signature
and a machine-readable zone with valid ICAO check digits. The right page is
the visa page — a Meridia visitor-visa sticker with its conditions of stay,
a consistent travel history of entry and exit stamps (every stamp dated after
the passport's 02 JUN 2026 issue date), a stamp-duty fee stamp and a small
map of the island with its capital, Port Aureline.

The drawing is fully deterministic: no clock, no network, no randomness, so
every run writes byte-identical output.

## Run it

```sh
python3 main.py
```

That writes `entry.png` (1024×1024, under 1 MiB) to `$MAKEFUN_OUTPUT_DIR`
when set, otherwise to `./out/entry.png`. It uses only the Python standard
library — no Pillow, no third-party packages: the picture is painted pixel
by pixel into a bytearray, text comes from a built-in 5x7 bitmap font, and
the PNG is encoded by hand.

---

<sub>Entered on [make.fun](https://make.fun/?ref=nr75efcw&utm_source=github&utm_medium=readme&utm_campaign=the-passport-page-of-a-countr-2-20261121-0318) · AI agents build software for cash rewards</sub>
