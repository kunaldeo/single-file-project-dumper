import os
import fnmatch
from typing import List, Dict, Set, Tuple
from pathlib import Path


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
    Also includes common patterns and other ignore files.
    
    Args:
        start_dir: Directory to start searching from
        
    Returns:
        List of gitignore patterns
    """
    # Use the new comprehensive ignore file loader
    return load_ignore_files(start_dir)


def get_default_ignore_patterns() -> List[str]:
    """Get default patterns for directories that should always be ignored."""
    return [
        '.git', '.svn', '.hg', '.bzr',  # Version control
        '.vscode', '.idea', '.sublime-*', '*.swp', '*.swo', '*~',  # IDE/Editor
        'node_modules', 'bower_components',  # JavaScript
        '__pycache__', '*.pyc', '*.pyo', '*.pyd', '.Python',  # Python
        'target', '.gradle', '.m2',  # Java/Maven/Gradle
        '.stack-work', '.cabal-sandbox',  # Haskell
        '.coverage', 'htmlcov', '.pytest_cache', '.tox',  # Testing
        '.DS_Store', 'Thumbs.db', 'desktop.ini',  # OS files
    ]


def load_ignore_files(start_dir: str) -> List[str]:
    """
    Load patterns from various ignore files (.gitignore, .dockerignore, etc.).
    
    Args:
        start_dir: Directory to start searching from
        
    Returns:
        List of ignore patterns
    """
    patterns = get_default_ignore_patterns()
    
    # Find git root directory
    git_root = find_git_dir(start_dir)
    search_dirs = [start_dir]
    if git_root and git_root != start_dir:
        search_dirs.append(git_root)
    
    # Check various ignore files
    ignore_files = ['.gitignore', '.dockerignore', '.npmignore']
    
    for dir_path in search_dirs:
        for ignore_file in ignore_files:
            ignore_path = os.path.join(dir_path, ignore_file)
            if os.path.exists(ignore_path):
                with open(ignore_path, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            patterns.append(line)
    
    return patterns


def is_ignored(path: str, gitignore_patterns: List[str]) -> bool:
    """Check if a path matches any gitignore patterns."""
    path_parts = path.split(os.sep)
    
    # Check if any part of the path matches a pattern
    for pattern in gitignore_patterns:
        # Direct match with any path component
        if any(fnmatch.fnmatch(part, pattern) for part in path_parts):
            return True
        # Full path match
        if fnmatch.fnmatch(path, pattern):
            return True
        # Pattern starting with / (root-relative)
        if pattern.startswith('/') and fnmatch.fnmatch(path, pattern[1:]):
            return True
        # Directory pattern ending with /
        if pattern.endswith('/') and any(fnmatch.fnmatch(f"{part}/", pattern) for part in path_parts):
            return True
            
    return False


def format_file_size(size: int) -> str:
    """Format file size in human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} TB"


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


def wrap_code_block(content: str, file_path: str) -> str:
    """Wrap file content in a markdown code block with appropriate language highlighting."""
    extension = os.path.splitext(file_path)[1].lstrip('.')
    if not extension:
        extension = ''
        
    if content.startswith('\ufeff'):
        content = content[1:]
    
    return f"```{extension}\n{content}\n```"