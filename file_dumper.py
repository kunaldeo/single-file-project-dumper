import os
import json
import fnmatch
import argparse
from pathlib import Path


def load_gitignore(root_dir):
    gitignore_path = os.path.join(root_dir, '.gitignore')
    patterns = [
        '__pycache__', '*.pyc', '*.pyo', '*.pyd', '.Python', 'build', 'develop-eggs', 'dist',
        'downloads', 'eggs', '.eggs', 'lib', 'lib64', 'parts', 'sdist', 'var', '*.egg-info',
        '.installed.cfg', '*.egg', '*.manifest', '*.spec', 'pip-log.txt',
        'pip-delete-this-directory.txt', '.venv', 'venv', 'ENV', 'env', '.env'
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


def select_files(root_dir, gitignore_patterns, existing_state, state_file, script_name):
    selected_files = existing_state.get('selected_files', {})
    skipped_dirs = existing_state.get('skipped_dirs', set())
    new_files = []

    for root, dirs, files in os.walk(root_dir, topdown=True):
        rel_path = os.path.relpath(root, root_dir)
        if rel_path == '.':
            rel_path = ''

        # First, handle directories
        filtered_dirs = []
        for d in dirs:
            dir_path = os.path.join(rel_path, d)
            
            # Skip already ignored directories
            if is_ignored(dir_path, gitignore_patterns):
                continue
                
            # Skip previously skipped directories
            if dir_path in skipped_dirs:
                continue
                
            # Ask about new directories
            if dir_path not in skipped_dirs:
                include = input(f"Include directory '{dir_path}'? (y/n): ").lower() == 'y'
                if include:
                    filtered_dirs.append(d)
                else:
                    skipped_dirs.add(dir_path)
                    
        # Update dirs in-place to only process chosen directories
        dirs[:] = filtered_dirs

        # Now handle files in included directories
        for file in files:
            file_path = os.path.join(rel_path, file)
            if (is_ignored(file_path, gitignore_patterns) or
                file.startswith('.') or
                file == '__init__.py' or
                file == os.path.basename(state_file) or
                file == script_name):
                continue

            full_path = os.path.join(root_dir, file_path)
            if os.path.getsize(full_path) == 0:
                continue

            if file_path not in selected_files:
                new_files.append(file_path)

    if new_files:
        print("\nNew files found:")
        for file_path in new_files:
            include = input(f"Include {file_path}? (y/n): ").lower() == 'y'
            selected_files[file_path] = include

    return selected_files, skipped_dirs


def dump_files(root_dir, selected_files, output_file):
    with open(output_file, 'w') as out:
        for file_path, include in selected_files.items():
            if include:
                full_path = os.path.join(root_dir, file_path)
                out.write(f"{file_path}:\n")
                try:
                    with open(full_path, 'r') as f:
                        out.write(f.read())
                except UnicodeDecodeError:
                    out.write(f"Unable to read file: {file_path} (possibly binary)\n")
                out.write("\n\n")


def main():
    parser = argparse.ArgumentParser(description="File Dumper Script")
    parser.add_argument("--root-dir", help="Root directory to start file dumping", default=os.getcwd())
    parser.add_argument("--output-file", help="Output file name", default="dumped_files.txt")
    parser.add_argument("--state-file", help="Path to state file", default=".file_dumper_state.json")
    args = parser.parse_args()

    root_dir = args.root_dir
    output_file = args.output_file
    state_file = args.state_file

    existing_state = load_state(state_file)
    gitignore_patterns = load_gitignore(root_dir)

    selected_files, skipped_dirs = select_files(root_dir, gitignore_patterns, existing_state, state_file, os.path.basename(__file__))

    new_state = {
        'root_dir': root_dir,
        'selected_files': selected_files,
        'skipped_dirs': list(skipped_dirs)  # Convert set to list for JSON serialization
    }
    save_state(state_file, new_state)
    dump_files(root_dir, selected_files, output_file)
    print(f"\nFiles dumped to {output_file}")


if __name__ == "__main__":
    main()
