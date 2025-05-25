import os
import json
import fnmatch
import argparse
from pathlib import Path
from typing import Set, Dict, List, Tuple
# Import statements moved to top of file
try:
    from pybars import Compiler
except ImportError:
    print("pybars3 is required for template support. Install it with:")
    print("pip install pybars3")
    sys.exit(1)


def find_git_dir(start_path: str) -> str:
    """
    Search up the directory tree for a .git directory.
    Returns the path containing .git, or None if not found.
    """
    current = os.path.abspath(start_path)
    while current != os.path.dirname(current):  # Stop at root directory
        if os.path.exists(os.path.join(current, '.git')):
            return current
        current = os.path.dirname(current)
    return None

def load_gitignore(start_dir: str) -> List[str]:
    """
    Load gitignore patterns, searching up the directory tree for .gitignore files.
    Also includes common Python patterns if no .gitignore file is found.
    
    Args:
        start_dir: Directory to start searching from
        
    Returns:
        List of gitignore patterns
    """
    patterns = [
        '__pycache__', '*.pyc', '*.pyo', '*.pyd', '.Python', 'build', 'develop-eggs', 
        'dist', 'downloads', 'eggs', '.eggs', 'lib', 'lib64', 'parts', 'sdist', 'var',
        '*.egg-info', '.installed.cfg', '*.egg', '*.manifest', '*.spec', 'pip-log.txt',
        'pip-delete-this-directory.txt', '.venv', 'venv', 'ENV', 'env', '.env'
    ]
    
    # First try to find the git root directory
    git_root = find_git_dir(start_dir)
    if git_root:
        # Load the repository's .gitignore if it exists
        repo_gitignore = os.path.join(git_root, '.gitignore')
        if os.path.exists(repo_gitignore):
            with open(repo_gitignore, 'r') as f:
                patterns.extend([line.strip() for line in f if line.strip() and not line.startswith('#')])
        
        # Also check for .gitignore in the current directory if it's different from git root
        if start_dir != git_root:
            local_gitignore = os.path.join(start_dir, '.gitignore')
            if os.path.exists(local_gitignore):
                with open(local_gitignore, 'r') as f:
                    patterns.extend([line.strip() for line in f if line.strip() and not line.startswith('#')])
    else:
        # If no git repository found, just check the current directory
        local_gitignore = os.path.join(start_dir, '.gitignore')
        if os.path.exists(local_gitignore):
            with open(local_gitignore, 'r') as f:
                patterns.extend([line.strip() for line in f if line.strip() and not line.startswith('#')])
                
    return patterns


def is_ignored(path: str, gitignore_patterns: List[str]) -> bool:
    """Check if a path matches any gitignore patterns."""
    path_parts = path.split(os.sep)
    
    for pattern in gitignore_patterns:
        if any(fnmatch.fnmatch(part, pattern) for part in path_parts):
            return True
        if fnmatch.fnmatch(path, pattern):
            return True
        if pattern.startswith('/') and fnmatch.fnmatch(path, pattern[1:]):
            return True
        if pattern.endswith('/') and any(fnmatch.fnmatch(f"{part}/", pattern) for part in path_parts):
            return True
            
    return False


def load_state(state_file: str) -> Dict:
    """Load previous file selection state from JSON file."""
    if os.path.exists(state_file):
        with open(state_file, 'r') as f:
            state = json.load(f)
            state['skipped_dirs'] = set(state.get('skipped_dirs', []))
            state['selected_dirs'] = set(state.get('selected_dirs', []))
            return state
    return {'selected_files': {}, 'skipped_dirs': set(), 'selected_dirs': set()}


def save_state(state_file: str, state: Dict) -> None:
    """Save current selection state to JSON file."""
    json_state = {
        'root_dir': state['root_dir'],
        'selected_files': state['selected_files'],
        'skipped_dirs': list(state['skipped_dirs']),
        'selected_dirs': list(state['selected_dirs'])
    }
    with open(state_file, 'w') as f:
        json.dump(json_state, f, indent=2)


def wrap_code_block(content: str, file_path: str) -> str:
    """Wrap file content in a markdown code block with appropriate language highlighting."""
    extension = os.path.splitext(file_path)[1].lstrip('.')
    if not extension:
        extension = ''
        
    if content.startswith('\ufeff'):
        content = content[1:]
    
    # Don't escape the content - let handlebars handle it
    return f"```{extension}\n{content}\n```"



def generate_source_tree(root_dir: str, selected_files: Dict[str, bool], selected_only: bool = False) -> str:
    """
    Generate a source tree representation of the project.
    
    Args:
        root_dir: Root directory of the project
        selected_files: Dictionary of file paths and their selection status
        selected_only: If True, show only selected files and their directories
        
    Returns:
        String representation of the source tree
    """
    tree = []
    
    def is_hidden(path: str) -> bool:
        """Check if a path is hidden (starts with '.')"""
        return any(part.startswith('.') for part in path.split(os.sep))
    
    def get_all_files() -> List[str]:
        """Get all non-hidden files in the directory"""
        all_files = []
        for root, _, files in os.walk(root_dir):
            rel_root = os.path.relpath(root, root_dir)
            if rel_root == '.':
                rel_root = ''
            
            # Skip hidden directories
            if is_hidden(rel_root):
                continue
                
            for file in files:
                if not is_hidden(file):
                    file_path = os.path.join(rel_root, file)
                    if file_path in selected_files:  # Only include files that were considered
                        all_files.append(file_path)
        return sorted(all_files)

    def get_selected_files() -> List[str]:
        """Get only selected files"""
        return sorted([f for f, included in selected_files.items() if included])
    
    # Decide which files to show based on mode
    files_to_show = get_selected_files() if selected_only else get_all_files()
    if not files_to_show:
        return ""

    # Track all directories needed
    directories = set()
    for file_path in files_to_show:
        parts = file_path.split(os.sep)
        for i in range(len(parts)):
            dir_path = os.sep.join(parts[:i])
            if dir_path:  # Skip empty path
                directories.add(dir_path)

    # Combine directories and files
    all_paths = sorted(list(directories) + files_to_show)
    
    # Build the tree with proper indentation
    last_level = []
    for path in all_paths:
        current_level = path.split(os.sep)
        
        # Determine common prefix length
        common_len = 0
        for last, curr in zip(last_level, current_level):
            if last != curr:
                break
            common_len += 1
        
        # Add new items with proper indentation
        for i, item in enumerate(current_level[common_len:], common_len):
            prefix = "    " * i
            # Use different symbols based on type and status
            if path in files_to_show:  # It's a file
                if path in selected_files and selected_files[path]:
                    marker = "└── "  # Selected file
                else:
                    marker = "├── "  # Unselected file
            else:  # It's a directory
                marker = "├── "
            tree.append(f"{prefix}{marker}{item}")
        
        last_level = current_level
    
    return "\n".join(tree)


def load_template(template_path: str) -> str:
    """Load a Handlebars template file."""
    if not template_path:
        # Default template with proper variable names
        return """Project Path: {{absolute_code_path}}

Source Tree:
```
{{source_tree}}
```

{{#each files}}
{{#if code}}
`{{path}}`:
{{{code}}}

{{/if}}
{{/each}}"""
    
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"Error loading template {template_path}: {e}")
        print("Using default template instead")
        return load_template(None)  # Fall back to default template


def dump_files(root_dir: str, selected_files: Dict[str, bool], output_file: str) -> None:
    """Write selected files to output with markdown formatting."""
    output = []
    
    # Add project path
    output.append(f"Project Path: {os.path.abspath(root_dir)}\n")
    
    # Add source tree
    output.append("Source Tree:")
    output.append("```")
    output.append(generate_source_tree(root_dir, selected_files, True))
    output.append("```\n")
    
    # Add each selected file
    for file_path, include in selected_files.items():
        if include:
            full_path = os.path.join(root_dir, file_path)
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    extension = os.path.splitext(file_path)[1].lstrip('.')
                    
                    output.append(f"`{file_path}`:")
                    output.append(f"```{extension}")
                    output.append(content)
                    output.append("```\n")
            except UnicodeDecodeError:
                output.append(f"`{file_path}`: Unable to read file (possibly binary)\n")
    
    # Write to file
    with open(output_file, 'w', encoding='utf-8') as out:
        out.write('\n'.join(output))



def select_files(root_dir: str, gitignore_patterns: List[str], 
                existing_state: Dict, state_file: str, 
                script_name: str, output_file: str) -> Tuple[Dict[str, bool], Set[str], Set[str]]:
    """Interactive file selection process."""
    selected_files = existing_state.get('selected_files', {})
    skipped_dirs = existing_state.get('skipped_dirs', set())
    selected_dirs = existing_state.get('selected_dirs', set())
    
    # Clean up missing files from state
    selected_files = {k: v for k, v in selected_files.items() 
                     if os.path.exists(os.path.join(root_dir, k))}
    
    # Files to ignore
    ignore_files = [script_name, os.path.basename(state_file), os.path.basename(output_file)]
    
    # Walk directory using relative paths
    for root, dirs, files in os.walk(root_dir, topdown=True):
        rel_path = os.path.relpath(root, root_dir)
        if rel_path == '.':
            rel_path = ''
            
        # Filter directories
        filtered_dirs = []
        for d in dirs:
            dir_path = os.path.normpath(os.path.join(rel_path, d))
            
            if is_ignored(dir_path, gitignore_patterns):
                continue
                
            if dir_path in skipped_dirs:
                continue
            if dir_path in selected_dirs:
                filtered_dirs.append(d)
                continue
                
            include = input(f"Include directory '{dir_path}'? (y/n): ").lower() == 'y'
            if include:
                filtered_dirs.append(d)
                selected_dirs.add(dir_path)
            else:
                skipped_dirs.add(dir_path)
                
        dirs[:] = filtered_dirs
        
        # Process files in included directories
        for file in files:
            file_path = os.path.normpath(os.path.join(rel_path, file))
            
            if (is_ignored(file_path, gitignore_patterns) or
                file in ignore_files or
                file.startswith('.') or
                os.path.getsize(os.path.join(root_dir, file_path)) == 0):
                continue
                
            if file_path not in selected_files:
                include = input(f"Include '{file_path}'? (y/n): ").lower() == 'y'
                selected_files[file_path] = include
                
    return selected_files, skipped_dirs, selected_dirs


def main():
    parser = argparse.ArgumentParser(description="File Dumper Script")
    parser.add_argument("root_dir", nargs='?', help="Root directory to start file dumping",
                       default=os.getcwd())
    parser.add_argument("--output-file", help="Output file name",
                       default="project_code.txt")
    parser.add_argument("--state-file", help="Path to state file",
                       default=".file_dumper_state.json")
    
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