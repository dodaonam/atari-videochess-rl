# M3 source terms and provenance check

- **Checked at:** 2026-10-20 14:53:45 UTC
- **Selected package:** Lichess Elite Database — May 2022
- **Owner decision:** bounded internal academic research and local retention only, recorded in [M3-source-decision-20261020.md](M3-source-decision-20261020.md)

## Publisher page

- URL: https://database.nikonoel.fr/
- Direct archive URL: https://database.nikonoel.fr/lichess_elite_2022-05.zip
- HTTP response: 200; `Content-Type: text/html; charset=UTF-8`
- Response body observed: 60,137 bytes; SHA-256 `b0bc850f67e5064e3ca9369b5ff0e91cdb0030a8af5f928e9aefa35a219ec88a`
- The page describes standard Lichess games, excludes bullet, states the post-December-2021 2500+ vs. 2300+ selection, and lists May 2022 as 355,535 games / 93 MB. These figures are publisher reports, not local archive measurements.
- The checked page provides no stated license or checksum for the filtered May 2022 package. This check makes no inference that it is CC0.
- Its page says Lichess game URLs were retained in `LichessURL` from June 2020. M3 records retain an opaque reference hash and source ordinal, not raw player names or game URLs.

## Upstream Lichess terms page

- URL: https://database.lichess.org/
- HTTP response: 200; `Content-Type: text/html`; `Content-Length: 473710`; `Last-Modified: Mon, 05 Oct 2026 09:22:13 GMT`; `ETag: \"6ac36c45-73a6e\"`
- Response body observed: 473,710 bytes; SHA-256 `2b1db536724631cd0a21e24bff3693b26037676e4f91489072f584be51e24b0d`
- The page states that Lichess database exports are CC0 and may be modified and redistributed. This statement is limited to official Lichess exports. It does not establish the rights or license of the separately curated Elite package.

## Use boundary and interpretation

The owner authorized bounded private/internal academic use of the exact Elite package despite the publisher's unstated package license. Keep the original archive and bulk derived records in ignored local artifact storage. Do not upload or publicly redistribute either. This project authorization is not a legal determination or a grant of third-party rights. If an explicit restriction inconsistent with this processing is found, stop the affected operation. The source manifest records this evidence path and its SHA-256 before any dataset build.

The raw HTML bodies were measured and hashed during this check but were not copied into the repository. The links and recorded response hashes identify the observed page versions for review; the publisher page has no stable terms revision identifier.
