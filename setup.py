#!/usr/bin/env python3
"""
Setup script for WSL-Tmux-Nvim-Setup CLI

Creates a standalone installable package for the wsm CLI tool.
"""

from setuptools import setup, find_packages
from pathlib import Path
import sys
import json

# Read version from version.json
try:
    with open('version.json', 'r') as f:
        version_data = json.load(f)
        version = version_data['version']
except (FileNotFoundError, KeyError, json.JSONDecodeError):
    version = '1.0.0'

# Read long description from README
readme_path = Path(__file__).parent / 'README.md'
long_description = ""
if readme_path.exists():
    with open(readme_path, 'r', encoding='utf-8') as f:
        long_description = f.read()

# Read requirements
with open('requirements.txt', 'r') as f:
    requirements = [
        line.strip() 
        for line in f 
        if line.strip() and not line.startswith('#') and not line.startswith('pathlib2')
    ]

# Filter out pathlib2 for Python 3.4+
if sys.version_info >= (3, 4):
    requirements = [req for req in requirements if not req.startswith('pathlib2')]

setup(
    name='wsl-tmux-nvim-setup',
    version=version,
    
    # Package information
    description='WSL-Tmux-Nvim-Setup Manager - CLI tool for WSL development environment',
    long_description=long_description,
    long_description_content_type='text/markdown',
    
    # Author and project info
    author='Albert Dall\'Ara',
    author_email='noreply@example.com',
    url='https://github.com/albertodall/wsl-tmux-nvim-setup',
    project_urls={
        'Bug Tracker': 'https://github.com/albertodall/wsl-tmux-nvim-setup/issues',
        'Documentation': 'https://github.com/albertodall/wsl-tmux-nvim-setup/wiki',
        'Source Code': 'https://github.com/albertodall/wsl-tmux-nvim-setup',
    },
    
    # Package configuration
    packages=find_packages(exclude=['tests', 'tests.*']),
    package_data={
        'cli': ['*.yml', '*.yaml', '*.json'],
        'cli.commands': ['*.yml', '*.yaml', '*.json'],
        'cli.utils': ['*.yml', '*.yaml', '*.json'],
    },
    include_package_data=True,
    
    # Dependencies
    python_requires='>=3.7',
    install_requires=requirements,
    
    # Optional dependencies
    extras_require={
        'dev': [
            'pytest>=6.0',
            'pytest-cov>=2.0',
            'black>=22.0',
            'flake8>=4.0',
            'mypy>=0.900',
        ],
        'build': [
            'pyinstaller>=4.0',
            'wheel>=0.36',
            'twine>=3.0',
        ],
    },
    
    # Entry points - main CLI command
    entry_points={
        'console_scripts': [
            'wsm=cli.wsm:main',
            'wsl-setup-manager=cli.wsm:main',
        ],
    },
    
    # Classification
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: MIT License',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Topic :: Software Development :: Build Tools',
        'Topic :: System :: Installation/Setup',
        'Topic :: System :: Systems Administration',
        'Topic :: Terminals',
        'Topic :: Utilities',
    ],
    
    # Keywords for search
    keywords=[
        'wsl', 'tmux', 'neovim', 'development', 'setup', 'cli', 'linux',
        'terminal', 'environment', 'configuration', 'installer'
    ],
    
    # License
    license='MIT',
    
    # Zip safety
    zip_safe=False,
)