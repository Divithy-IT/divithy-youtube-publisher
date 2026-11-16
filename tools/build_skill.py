"""Build the marketplace ZIP from an explicit allowlist; include no local state."""

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
FILES = ('SKILL.md', 'references/workflow.md', 'LICENSE')


def main():
    source = ROOT / 'skills' / 'divithy-youtube-publisher'
    # Keep the external-app instructions in sync with the tested source release.
    reference = ROOT / 'docs' / 'QUICKSTART_EN.md'
    if (source / 'references' / 'workflow.md').read_bytes() != reference.read_bytes():
        raise SystemExit('Skill workflow differs from docs/QUICKSTART_EN.md; sync it before packaging.')
    output = ROOT / 'dist' / 'divithy-youtube-publisher-skill.zip'
    output.parent.mkdir(exist_ok=True)
    with ZipFile(output, 'w', compression=ZIP_DEFLATED) as archive:
        for name in FILES:
            path = source / name
            if path.is_symlink() or not path.is_file():
                raise SystemExit(f'Expected a regular package file: {name}')
            archive.write(path, name)
    print(output)


if __name__ == '__main__':
    main()
