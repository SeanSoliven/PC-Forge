"""Reject bytes before PHP opening tags and closing tags in PHP-only files."""
from pathlib import Path

root = Path(__file__).resolve().parents[1]
files = sorted(root.rglob('*.php'))
for path in files:
    if '.git' in path.parts:
        continue
    contents = path.read_bytes()
    assert contents.startswith(b'<?php'), f'{path}: BOM/whitespace/output before PHP'
    assert b'\xef\xbb\xbf' not in contents, f'{path}: UTF-8 BOM found'
    if path.relative_to(root).as_posix() in {'bootstrap.php', 'logout.php', 'config/db.php', 'config/orders.php'}:
        assert b'?>' not in contents, f'{path}: closing tag in PHP-only file'
    print('PASS:', path.relative_to(root), 'has no BOM or leading output')
