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
            # Add patterns from .gitignore file to existing patterns
            patterns.extend([line.strip() for line in f if line.strip() and not line.startswith('#')])

    return patterns


def is_ignored(path, gitignore_patterns):
    path_parts = path.split(os.sep)
    for pattern in gitignore_patterns:
        # Check if any part of the path matches the pattern
        if any(fnmatch.fnmatch(part, pattern) for part in path_parts):
            return True
        # Check if the full path matches the pattern
        if fnmatch.fnmatch(path, pattern):
            return True
        # Check if the pattern with a leading '/' matches the path
        if pattern.startswith('/') and fnmatch.fnmatch(path, pattern[1:]):
            return True
        # Check if the pattern with a trailing '/' matches any directory
        if pattern.endswith('/') and any(fnmatch.fnmatch(f"{part}/", pattern) for part in path_parts):
            return True
    return False


def load_state(state_file):
    if os.path.exists(state_file):
        with open(state_file, 'r') as f:
            state = json.load(f)
            # Convert lists to sets for efficient lookup
            state['skipped_dirs'] = set(state.get('skipped_dirs', []))
            state['selected_dirs'] = set(state.get('selected_dirs', []))
            return state
    return {'selected_files': {}, 'skipped_dirs': set(), 'selected_dirs': set()}


def save_state(state_file, state):
    # Convert sets to lists for JSON serialization
    json_state = {
        'root_dir': state['root_dir'],
        'selected_files': state['selected_files'],
        'skipped_dirs': list(state['skipped_dirs']),
        'selected_dirs': list(state['selected_dirs'])
    }
    with open(state_file, 'w') as f:
        json.dump(json_state, f, indent=2)


def clean_missing_files(root_dir, selected_files):
    """Remove missing files from the state and return cleaned selected files dict"""
    cleaned_files = {}
    removed_files = []
    
    for file_path, include in selected_files.items():
        full_path = os.path.join(root_dir, file_path)
        if os.path.exists(full_path):
            cleaned_files[file_path] = include
        else:
            removed_files.append(file_path)
    
    if removed_files:
        print("\nRemoving missing files from state:")
        for file_path in removed_files:
            print(f"- {file_path}")
            
    return cleaned_files


def select_files(root_dir, gitignore_patterns, existing_state, state_file, script_name, output_file):
    selected_files = existing_state.get('selected_files', {})
    skipped_dirs = existing_state.get('skipped_dirs', set())
    selected_dirs = existing_state.get('selected_dirs', set())
    new_files = []

    # Clean up missing files from state
    selected_files = clean_missing_files(root_dir, selected_files)

    # Get the absolute path of root_dir for proper relative path calculation
    abs_root_dir = os.path.abspath(root_dir)

    # Add script-specific files to ignore
    script_ignore_patterns = [
        script_name,
        os.path.basename(state_file),
        os.path.basename(output_file)
    ]
    all_ignore_patterns = gitignore_patterns + script_ignore_patterns

    for root, dirs, files in os.walk(abs_root_dir, topdown=True):
        # Calculate relative path from the root directory
        rel_path = os.path.relpath(root, abs_root_dir)
        if rel_path == '.':
            rel_path = ''

        # First, handle directories
        filtered_dirs = []
        for d in dirs:
            dir_path = os.path.normpath(os.path.join(rel_path, d))
            full_dir_path = os.path.normpath(os.path.join(abs_root_dir, dir_path))
            
            # Skip already ignored directories
            if is_ignored(dir_path, all_ignore_patterns):
                continue
                
            # Skip previously skipped directories
            if dir_path in skipped_dirs:
                continue

            # Include previously selected directories
            if dir_path in selected_dirs:
                filtered_dirs.append(d)
                continue
                
            # Ask about new directories with relative path
            include = input(f"Include directory '{dir_path}'? (y/n): ").lower() == 'y'
            if include:
                filtered_dirs.append(d)
                selected_dirs.add(dir_path)
            else:
                skipped_dirs.add(dir_path)
                    
        # Update dirs in-place to only process chosen directories
        dirs[:] = filtered_dirs

        # Now handle files in included directories
        for file in files:
            file_path = os.path.normpath(os.path.join(rel_path, file))
            
            # Skip ignored files (including script-specific files)
            if (is_ignored(file_path, all_ignore_patterns) or
                file.startswith('.') or
                file == '__init__.py'):
                continue

            full_path = os.path.join(abs_root_dir, file_path)
            if os.path.getsize(full_path) == 0:
                continue

            if file_path not in selected_files:
                new_files.append(file_path)

    if new_files:
        print("\nNew files found:")
        for file_path in new_files:
            # Show relative path when asking about files
            include = input(f"Include '{file_path}'? (y/n): ").lower() == 'y'
            selected_files[file_path] = include

    return selected_files, skipped_dirs, selected_dirs


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
    parser.add_argument("--output-file", help="Output file name", default="project_code.txt")
    parser.add_argument("--state-file", help="Path to state file", default=".file_dumper_state.json")
    args = parser.parse_args()

    root_dir = args.root_dir
    output_file = args.output_file
    state_file = args.state_file

    existing_state = load_state(state_file)
    gitignore_patterns = load_gitignore(root_dir)

    selected_files, skipped_dirs, selected_dirs = select_files(
        root_dir, gitignore_patterns, existing_state, state_file, 
        os.path.basename(__file__), output_file
    )

    new_state = {
        'root_dir': root_dir,
        'selected_files': selected_files,
        'skipped_dirs': skipped_dirs,
        'selected_dirs': selected_dirs
    }
    save_state(state_file, new_state)
    dump_files(root_dir, selected_files, output_file)
    print(f"\nFiles dumped to {output_file}")


if __name__ == "__main__":
    main()
