import os
from pathlib import Path
from typing import Optional, Dict, List


def detect_project_type(root_dir: str) -> Optional[str]:
    """Detect project type based on files present."""
    indicators = {
        'python': ['requirements.txt', 'setup.py', 'pyproject.toml', 'Pipfile'],
        'javascript': ['package.json', 'yarn.lock', 'package-lock.json'],
        'typescript': ['tsconfig.json', 'package.json'],
        'rust': ['Cargo.toml', 'Cargo.lock'],
        'go': ['go.mod', 'go.sum'],
        'java': ['pom.xml', 'build.gradle', 'build.gradle.kts'],
        'cpp': ['CMakeLists.txt', 'Makefile', '*.cpp', '*.h'],
        'ruby': ['Gemfile', 'Gemfile.lock', '*.rb'],
        'php': ['composer.json', 'composer.lock'],
        'swift': ['Package.swift', '*.xcodeproj'],
        'kotlin': ['build.gradle.kts', '*.kt'],
        'scala': ['build.sbt', '*.scala'],
    }
    
    for project_type, files in indicators.items():
        for file_pattern in files:
            if '*' in file_pattern:
                # Handle wildcards
                if list(Path(root_dir).glob(file_pattern)):
                    return project_type
            else:
                if os.path.exists(os.path.join(root_dir, file_pattern)):
                    return project_type
    return None


def get_smart_defaults(project_type: str) -> Dict:
    """Get smart defaults based on project type."""
    defaults = {
        'python': {
            'include': ['*.py', '*.pyx', '*.pxd', '*.pyi'],
            'exclude': ['__pycache__/*', '*.pyc', 'venv/*', '.venv/*', 'build/*', 'dist/*', '*.egg-info/*'],
            'max_file_size': 1000
        },
        'javascript': {
            'include': ['*.js', '*.jsx', '*.mjs', '*.json', '*.md'],
            'exclude': ['node_modules/*', 'dist/*', 'build/*', 'coverage/*', '.next/*'],
            'max_file_size': 500
        },
        'typescript': {
            'include': ['*.ts', '*.tsx', '*.js', '*.jsx', '*.json', '*.md'],
            'exclude': ['node_modules/*', 'dist/*', 'build/*', 'coverage/*', '.next/*', '*.d.ts'],
            'max_file_size': 500
        },
        'rust': {
            'include': ['*.rs', 'Cargo.toml', '*.md'],
            'exclude': ['target/*', 'Cargo.lock'],
            'max_file_size': 1000
        },
        'go': {
            'include': ['*.go', 'go.mod', 'go.sum', '*.md'],
            'exclude': ['vendor/*', 'bin/*'],
            'max_file_size': 1000
        },
        'java': {
            'include': ['*.java', '*.xml', 'pom.xml', '*.gradle', '*.properties', '*.md'],
            'exclude': ['target/*', 'build/*', '.gradle/*', '*.class'],
            'max_file_size': 1000
        },
        'cpp': {
            'include': ['*.cpp', '*.h', '*.hpp', '*.c', '*.cc', 'CMakeLists.txt', 'Makefile', '*.md'],
            'exclude': ['build/*', 'cmake-build-*/*', '*.o', '*.obj', '*.exe'],
            'max_file_size': 1000
        },
        'ruby': {
            'include': ['*.rb', '*.rake', 'Gemfile', 'Rakefile', '*.gemspec', '*.md'],
            'exclude': ['vendor/*', '.bundle/*', 'tmp/*', 'log/*'],
            'max_file_size': 500
        },
        'php': {
            'include': ['*.php', 'composer.json', '*.md'],
            'exclude': ['vendor/*', 'cache/*', 'logs/*'],
            'max_file_size': 500
        }
    }
    return defaults.get(project_type, {})