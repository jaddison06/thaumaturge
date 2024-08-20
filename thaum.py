#!/usr/bin/python3.9

import os
import os.path as path
from shutil import copy
from typing import Callable, Any
from datetime import datetime
from yaml import safe_load
import platform
from generate import generate

target_config: Any

def config_dir() -> str: return target_config['repo_url'].split('/')[-1]

OUTPUT_DIR = {
    'server': 'bin',
    'frontend': 'lib/src'
}

def run_stage(fn: Callable[[], None], msg: str):
    print(f'{msg}... ', end = '', flush = True)
    start = datetime.now()
    fn()
    end = datetime.now()
    duration = end - start
    print(f'Done ({duration.seconds}.{duration.microseconds:06}s)')

def download_config():
    os.system(f'git clone --quiet {target_config["repo_url"]}')

def configure():
    generate(target_config['target'], target_config['output_dir'], config_dir())
    add_ignore_listing(f'{target_config["output_dir"]}/generated.dart')

def add_ignore_listing(file: str):
    if not path.exists('.gitignore'):
        open('.gitignore', 'w').close()
    
    with open('.gitignore', 'rt') as fh:
        lines = fh.readlines()

    if file not in lines:
        with open('.gitignore', 'at') as fh:
            fh.write(f'{file}\n')

def configure_exts():
    with open(f'{config_dir()}/generate.yaml', 'rt') as fh:
        contents = safe_load(fh)

    for ext in list(contents['extensions'].values()):
        copy(f'{config_dir()}/ext/{ext}.dart', f'{target_config["output_dir"]}/{ext}.dart')
        ignore_file = f'{target_config["output_dir"]}/{ext}.dart'
        add_ignore_listing(ignore_file)

def cleanup():
    if platform.system() == 'Windows':
        os.system(f'rmdir /s /q {config_dir()}')
    elif platform.system() == 'Linux':
        os.system(f'rm -rf {config_dir()}')
    else:
        raise ValueError('Unsupported platform!')

def main():
    global config
    print('Thaumaturge v1.1')
    global target_config
    with open('thaum.yaml', 'rt') as fh:
        target_config = safe_load(fh)
    run_stage(download_config, 'Downloading configuration')
    print('---\nLast commit:')
    os.system(f'git -C {config_dir()} log -1 --pretty=format:%B')
    print('---')
    try:
        run_stage(configure, 'Configuring')
        if target_config['target'] != 'thaum':
            run_stage(configure_exts, 'Configuring extensions')
    finally:
        run_stage(cleanup, 'Cleaning up')

if __name__ == '__main__': main()