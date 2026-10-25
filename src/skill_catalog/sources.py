"""Bounded, read-only inspection of explicitly registered skill roots."""
import hashlib
import json
import os
from pathlib import Path
import stat

import yaml

MAX_FILE = 1024 * 1024
MAX_PACKAGE = 16 * MAX_FILE
MAX_FILES = 1000
IGNORE = {'.git', '.venv', 'node_modules', '__pycache__'}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def contained(root, relative):
    root = Path(root)
    relative = Path(relative)
    if relative.is_absolute() or '..' in relative.parts:
        raise ValueError('Expected a relative path inside the registered source')
    path = root / relative
    if root.is_symlink() or any(p.is_symlink() for p in [path, *path.parents] if p == root or root in p.parents):
        raise ValueError('Symlink sources are not followed; register the resolved directory explicitly')
    path.resolve().relative_to(root.resolve())
    return path


def stamp(path):
    info = path.stat()
    return (info.st_dev, info.st_ino, info.st_mode, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def raw_file(path):
    before = stamp(path)
    if not stat.S_ISREG(before[2]) or before[3] > MAX_FILE:
        raise ValueError('Expected a regular file no larger than 1 MiB: ' + str(path))
    with path.open('rb') as stream:
        raw = stream.read(MAX_FILE + 1)
    if len(raw) > MAX_FILE or stamp(path) != before:
        raise ValueError('Source changed or exceeded its read limit')
    return raw


def inventory(root):
    root = Path(root)
    if not root.is_dir() or root.is_symlink():
        raise ValueError('Source directory is missing or a symlink: ' + str(root))
    found = []
    def fail(error):
        raise error
    for directory, dirs, files in os.walk(root, onerror=fail, followlinks=False):
        dirs[:] = sorted(d for d in dirs if d not in IGNORE)
        for name in dirs + files:
            if (Path(directory) / name).is_symlink():
                raise ValueError('Symlink in source: ' + str(Path(directory) / name))
        for name in sorted(files):
            found.append((Path(directory) / name).relative_to(root).as_posix())
            if len(found) > MAX_FILES:
                raise ValueError('Source inventory exceeds 1000 files; register a smaller root')
    return sorted(found)


def inspect(root, location):
    skill = contained(root, location)
    if skill.name != 'SKILL.md':
        raise ValueError('Skill location must name SKILL.md')
    package = skill.parent
    names = inventory(package)
    hashes, total, stamps = {}, 0, {}
    raw = None
    for name in names:
        path = contained(package, name)
        stamps[name] = stamp(path)
        value = raw_file(path)
        total += len(value)
        if total > MAX_PACKAGE:
            raise ValueError('Skill package exceeds 16 MiB')
        hashes[name] = digest(value)
        if name == 'SKILL.md':
            raw = value
    if raw is None or inventory(package) != names or any(stamp(contained(package,n))!=value for n,value in stamps.items()):
        raise ValueError('Skill changed during inspection')
    if len(raw) > 128 * 1024:
        raise ValueError('SKILL.md exceeds the 128 KiB instruction response limit')
    text = raw.decode('utf-8')
    lines = text.splitlines()
    meta = {}
    if lines and lines[0].strip() == '---':
        end = next((i for i in range(1, len(lines)) if lines[i].strip() == '---'), None)
        if end is None:
            raise ValueError('Unterminated skill YAML')
        meta = yaml.safe_load('\n'.join(lines[1:end])) or {}
        if not isinstance(meta, dict):
            raise ValueError('Skill YAML must be a mapping')
    for field in ('name', 'description'):
        if field in meta and not isinstance(meta[field], str):
            raise ValueError('Skill ' + field + ' must be text')
    return {'location': location, 'name': meta.get('name') or package.name,
            'description': meta.get('description', ''), 'instruction': text,
            'instruction_revision': hashes['SKILL.md'], 'files': hashes,
            'package_revision': digest(json.dumps(hashes, sort_keys=True).encode())}


class Sources:
    def __init__(self, core):
        self.core = core

    def list(self):
        return self.core.documents.scan(directory='sources', collection='sources')['documents']

    def get(self, id):
        for doc in self.list():
            if doc['metadata']['id'] == id:
                return doc['metadata']
        raise ValueError('Unknown source: ' + id)

    def save(self, id, root, shell, origin, expected_revision=None):
        import re
        if not re.fullmatch(r'[a-z][a-z0-9_-]*', id):
            raise ValueError('Invalid source id')
        path = Path(root).expanduser()
        if not path.is_absolute() or not path.is_dir():
            raise ValueError('Source root must be an existing absolute directory')
        root = str(path.resolve())
        old = next((d for d in self.list() if d['metadata']['id'] == id), None)
        if old and old['metadata']['root'] != root:
            raise ValueError('Source roots are immutable; register a new source for a different root')
        # Overlapping roots make installation identity ambiguous.
        for doc in self.list():
            other = Path(doc['metadata']['root'])
            if doc['metadata']['id'] != id and (path.resolve() == other or path.resolve() in other.parents or other in path.resolve().parents):
                raise ValueError('Source roots must not overlap')
        self.core.documents.write(directory='sources', collection='sources', path=id+'.md',
            metadata={'id':id,'type':'skill_source','root':root,'shell':shell,'origin':origin},
            text='# '+id+'\n\nRead-only skill source.\n',expected_revision=expected_revision)
        return next(d for d in self.list() if d['metadata']['id'] == id)

    def discover(self, source_id):
        source = self.get(source_id)
        found = inventory(source['root'])
        records=[]
        for location in found:
            if Path(location).name == 'SKILL.md':
                data=inspect(source['root'], location)
                data.pop('instruction')
                records.append({**data, 'source_id':source_id,'shell':source['shell'],'origin':source['origin']})
        if inventory(source['root']) != found:
            raise ValueError('Source inventory changed; retry')
        return {'records':records,'complete':True,'source_id':source_id}

    def inspect(self, source_id, location):
        return inspect(self.get(source_id)['root'], location)

    def file_read(self, source_id, location, file, expected_revision):
        source = self.get(source_id)
        snapshot = inspect(source['root'], location)
        if snapshot['package_revision'] != expected_revision:
            raise ValueError('Skill package changed; inspect it again')
        if file not in snapshot['files']:
            raise ValueError('File is not in the inspected skill package')
        path = contained(contained(source['root'], location).parent, file)
        raw = raw_file(path)
        if digest(raw) != snapshot['files'][file]:
            raise ValueError('File changed during inspection')
        if len(raw) > 256 * 1024:
            raise ValueError('Text response exceeds 256 KiB')
        return {'file':file,'content':raw.decode('utf-8'),'revision':digest(raw)}
