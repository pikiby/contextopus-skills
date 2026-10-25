#!/usr/bin/env python3
"""Build only the skill catalog module; never install or alter user skills."""
import argparse
import hashlib
from pathlib import Path
import shutil
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def build(output):
    output=Path(output).resolve()
    if output.exists(): raise ValueError('Output already exists')
    output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent) as temporary:
        stage=Path(temporary)/'skill_catalog'
        package=stage/'package'
        package.mkdir(parents=True)
        shutil.copy2(ROOT/'module/module.json',stage/'module.json')
        shutil.copy2(ROOT/'module/package/worker.py',package/'worker.py')
        for name in ('procedures','skills'):
            shutil.copytree(ROOT/'module/package'/name,package/name)
        shutil.copytree(ROOT/'module/migrations',package/'migrations')
        (package/'skill_catalog').mkdir()
        for name in ('__init__.py','catalog.py','sources.py','service.py'):
            shutil.copy2(ROOT/'src/skill_catalog'/name,package/'skill_catalog'/name)
        shutil.copy2(ROOT/'README.md',stage/'README.md')
        for name in ('LICENSE','NOTICE'):
            shutil.copy2(ROOT/name,stage/name)
        stage.rename(output)
    return output


def build_zip(output):
    output=Path(output).resolve()
    if output.exists() or Path(str(output)+'.sha256').exists(): raise ValueError('Output already exists')
    output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory() as temporary:
        module=build(Path(temporary)/'skill_catalog')
        with zipfile.ZipFile(output,'x',compression=zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(module.rglob('*')):
                if path.is_file(): archive.write(path,path.relative_to(module.parent))
    with Path(str(output)+'.sha256').open('x') as stream:
        stream.write(hashlib.sha256(output.read_bytes()).hexdigest()+'  '+output.name+'\n')
    return output


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--zip',action='store_true')
    parser.add_argument('output')
    args=parser.parse_args()
    print((build_zip if args.zip else build)(args.output))
