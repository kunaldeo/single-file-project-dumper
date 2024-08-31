import os
import json
import fnmatch
from pathlib import Path


def load_gitignore(root_dir):
    gitignore_path = os.path.join(root_dir, '.gitignore')
    patterns = [
        '__pycache__',
        '*.pyc',
        '*.pyo',
        '*.pyd',
        '.Python',
        'build',
        'develop-eggs',
        'dist',
        'downloads',
        'eggs',
        '.eggs',
        'lib',
        'lib64',
        'parts',
        'sdist',
        'var',
        '*.egg-info',
        '.installed.cfg',
        '*.egg',
        '*.manifest',
        '*.spec',
        'pip-log.txt',
        'pip-delete-this-directory.txt',
        '.venv',
        'venv',
        'ENV',
        'env',
        '.env'
    ]

    if os.path.exists(gitignore_path):
        with open(gitignore_path, 'r') as f:
            patterns.extend([line.strip() for line in f if line.strip() and not line.startswith('#')])

    return patterns


def is_ignored(path, gitignore_patterns):
    path_parts = path.split(os.sep)
    return any(
        any(fnmatch.fnmatch(part, pattern) for part in path_parts)
        or fnmatch.fnmatch(path, pattern)
        for pattern in gitignore_patterns
    )


def load_state(state_file):
    if os.path.exists(state_file):
        with open(state_file, 'r') as f:
            return json.load(f)
    return {}


def save_state(state_file, state):
    with open(state_file, 'w') as f:
        json.dump(state, f, indent=2)


def select_files(root_dir, gitignore_patterns, existing_state):
    selected_files = existing_state.get('selected_files', {})
    for root, dirs, files in os.walk(root_dir, topdown=True):
        rel_path = os.path.relpath(root, root_dir)
        if rel_path == '.':
            rel_path = ''

        if is_ignored(rel_path, gitignore_patterns) or rel_path in existing_state.get('omitted_dirs', []):
            dirs[:] = []
            continue

        if rel_path not in existing_state.get('processed_dirs', []):
            print(f"\nCurrent directory: {rel_path}")
            include_dir = input(f"Include files from {rel_path or 'root directory'}? (y/n): ").lower() == 'y'
            if not include_dir:
                existing_state.setdefault('omitted_dirs', []).append(rel_path)
                dirs[:] = []
                continue
            existing_state.setdefault('processed_dirs', []).append(rel_path)

        for file in files:
            file_path = os.path.join(rel_path, file)
            if is_ignored(file_path, gitignore_patterns) or file == '__init__.py':
                continue

            full_path = os.path.join(root_dir, file_path)
            if os.path.getsize(full_path) == 0:
                continue

            if file_path not in selected_files:
                include = input(f"Include {file_path}? (y/n): ").lower() == 'y'
                selected_files[file_path] = include

    return selected_files


def dump_files(root_dir, selected_files, output_file):
    with open(output_file, 'w') as out:
        for file_path, include in selected_files.items():
            if include:
                full_path = os.path.join(root_dir, file_path)
                out.write(f"{file_path}:\n")
                with open(full_path, 'r') as f:
                    out.write(f.read())
                out.write("\n\n")


def main():
    current_dir = os.getcwd()
    state_file = os.path.join(current_dir, '.file_dumper_state.json')
    existing_state = load_state(state_file)

    root_dir = existing_state.get('root_dir') or input("Enter the root directory: ")
    output_file = os.path.join(current_dir, 'dumped_files.txt')

    gitignore_patterns = load_gitignore(root_dir)

    selected_files = select_files(root_dir, gitignore_patterns, existing_state)

    new_state = {
        'root_dir': root_dir,
        'selected_files': selected_files,
        'processed_dirs': existing_state.get('processed_dirs', []),
        'omitted_dirs': existing_state.get('omitted_dirs', [])
    }
    save_state(state_file, new_state)
    dump_files(root_dir, selected_files, output_file)
    print(f"Files dumped to {output_file}")


if __name__ == "__main__":
    main()
