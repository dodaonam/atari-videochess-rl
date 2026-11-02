"""Inventory tracked bytes and compressed members without reading private stores.

This pattern scan cannot establish third-party rights or prove absence of all secrets.
The sole permitted binary leaf is inside the exact owner-dispositioned M1 archive.
"""
from __future__ import annotations

import argparse
from collections import Counter
import gzip
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import zipfile

ARCHIVE = '.agents/evidence/BLK-001-diagnostic-20261015-r2.zip'
ARCHIVE_SHA256 = '91b0d03907b1b6764f18991880596f9c09b90986ad982b05f106bed948f96a32'
PATTERNS = {
    'private_key': rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',
    'github_token': rb'\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})\b',
    'aws_key': rb'\bAKIA[A-Z0-9]{16}\b',
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path,
                        help='Write inventory JSON outside the repository.')
    args = parser.parse_args()
    root = Path(subprocess.check_output(['git', 'rev-parse', '--show-toplevel'], text=True).strip())
    if args.output.resolve().is_relative_to(root.resolve()):
        parser.error('output must be outside the repository to avoid source mutation')
    paths = subprocess.check_output(['git', 'ls-files', '-z'], cwd=root).decode().split('\0')[:-1]
    findings = []
    opaque = []
    members = Counter()
    historical_paths = Counter()
    inventory = []

    def inspect(name: str, payload: bytes) -> None:
        for kind, pattern in PATTERNS.items():
            if re.search(pattern, payload):
                findings.append({'path': name, 'kind': kind})
        historical_paths['concrete_home_path_occurrences'] += len(
            re.findall(rb'/(?:home|Users)/[A-Za-z0-9_-]+/', payload))
        if payload.startswith(b'\x1f\x8b'):
            members['gzip'] += 1
            inspect(name + '::gzip', gzip.decompress(payload))
        elif payload.startswith(b'PK\x03\x04'):
            with zipfile.ZipFile(io.BytesIO(payload)) as archive:
                for item in archive.infolist():
                    if not item.is_dir():
                        members['zip_entries'] += 1
                        inspect(name + '::' + item.filename, archive.read(item))
        else:
            try:
                payload.decode('utf8')
            except UnicodeDecodeError:
                opaque.append({'path': name, 'bytes': len(payload),
                               'signature': payload[:8].hex()})

    for relative in paths:
        payload = (root / relative).read_bytes()
        inspect(relative, payload)
        inventory.append({'path': relative, 'bytes': len(payload),
                          'sha256': hashlib.sha256(payload).hexdigest()})
    archive_unchanged = hashlib.sha256((root / ARCHIVE).read_bytes()).hexdigest() == ARCHIVE_SHA256
    unexpected_opaque = [entry for entry in opaque if not entry['path'].startswith(ARCHIVE + '::')]
    result = {
        'schema_version': 1,
        'source_head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip(),
        'scope': 'tracked worktree bytes, recursive gzip/ZIP members; exact inventory hashes',
        'files': len(paths),
        'recursive_members': dict(members),
        'high_confidence_credential_matches': findings,
        'opaque_leaf_payloads': opaque,
        'unexpected_opaque_payloads': unexpected_opaque,
        'authorized_historical_archive_unchanged': archive_unchanged,
        'historical_path_counts': dict(historical_paths),
        'inventory': inventory,
        'limitations': [
            'Pattern scanning is not proof of absence of all secrets or of third-party rights.',
            'Historical concrete paths remain in accepted immutable evidence.',
            'Only the exact existing BLK-001 archive has a scoped owner disposition.',
            'Private artifact stores and past versions of Git blobs are outside this content scan.',
        ],
    }
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    summary = {key: value for key, value in result.items()
               if key not in ('inventory', 'opaque_leaf_payloads')}
    summary['opaque_leaf_count'] = len(opaque)
    print(json.dumps(summary, indent=2))
    return int(bool(findings or unexpected_opaque or not archive_unchanged))


if __name__ == '__main__':
    raise SystemExit(main())
