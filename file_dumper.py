import os
import json
import fnmatch
from pathlib import Path

def load_gitignore(root_dir):
    gitignore_path = os.path.join(root_dir, '.gitignore')
    if not os.path.exists(gitignore_path):
        return []
    
    with open(gitignore_path, 'r') as f:
        return [line.strip() for line in f if line.strip() and not line.startswith('#')]

def is_ignored(file_path, gitignore_patterns):
    for pattern in gitignore_patterns:
        if fnmatch.fnmatch(file_path, pattern):
            return True
    return False

def load_state(state_file):
    if os.path.exists(state_file):
        with open(state_file, 'r') as f:
            return json.load(f)
    return {}

def save_state(state_file, state):
    with open(state_file, 'w') as f:
        json.dump(state, f, indent=2)

def select_files(root_dir, gitignore_patterns, existing_state):
    selected_files = {}
    for root, dirs, files in os.walk(root_dir, topdown=True):
        rel_path = os.path.relpath(root, root_dir)
        if rel_path == '.':
            rel_path = ''
        
        print(f"\nCurrent directory: {rel_path}")
        use_existing = input("Use existing selections for this directory? (y/n): ").lower() == 'y'
        
        if not use_existing:
            include_dir = input(f"Include files from {rel_path or 'root directory'}? (y/n): ").lower() == 'y'
            if not include_dir:
                dirs[:] = []  # Clear the list of subdirectories to prevent further recursion
                continue
        
        for file in files:
            file_path = os.path.join(rel_path, file)
            if is_ignored(file_path, gitignore_patterns):
                continue
            
            if use_existing and file_path in existing_state.get('selected_files', {}):
                selected_files[file_path] = existing_state['selected_files'][file_path]
            else:
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

    if 'root_dir' in existing_state:
        use_existing_dir = input(f"Use existing root directory ({existing_state['root_dir']})? (y/n): ").lower() == 'y'
        if use_existing_dir:
            root_dir = existing_state['root_dir']
        else:
            root_dir = input("Enter the root directory: ")
    else:
        root_dir = input("Enter the root directory: ")

    output_file = os.path.join(current_dir, 'dumped_files.txt')
    
    gitignore_patterns = load_gitignore(root_dir)
    
    if 'selected_files' in existing_state:
        use_existing = input("Existing file selections found. Use them? (y/n): ").lower() == 'y'
        if use_existing:
            selected_files = existing_state['selected_files']
        else:
            selected_files = select_files(root_dir, gitignore_patterns, existing_state)
    else:
        selected_files = select_files(root_dir, gitignore_patterns, {})
    
    new_state = {
        'root_dir': root_dir,
        'selected_files': selected_files
    }
    save_state(state_file, new_state)
    dump_files(root_dir, selected_files, output_file)
    print(f"Files dumped to {output_file}")

if __name__ == "__main__":
    main()
