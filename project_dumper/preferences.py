"""User preferences management for the project dumper."""

import os
import json
from typing import Dict, Any, Optional
from pathlib import Path


def get_preferences_file() -> str:
    """Get the path to the user preferences file."""
    config_dir = Path.home() / '.config' / 'project-dumper'
    config_dir.mkdir(parents=True, exist_ok=True)
    return str(config_dir / 'preferences.json')


def load_preferences() -> Dict[str, Any]:
    """Load user preferences."""
    prefs_file = get_preferences_file()
    
    if os.path.exists(prefs_file):
        try:
            with open(prefs_file, 'r') as f:
                return json.load(f)
        except:
            pass
    
    # Default preferences
    return {
        'default_output_file': 'project_code.txt',
        'auto_copy': False,
        'create_manifest': False,
        'color_output': True,
        'recent_projects': [],
        'favorite_templates': [],
        'quick_patterns': {
            'python': ['*.py', '!__pycache__', '!*.pyc'],
            'javascript': ['*.js', '*.jsx', '!node_modules'],
            'typescript': ['*.ts', '*.tsx', '!node_modules', '!*.d.ts']
        }
    }


def save_preferences(prefs: Dict[str, Any]) -> None:
    """Save user preferences."""
    prefs_file = get_preferences_file()
    
    with open(prefs_file, 'w') as f:
        json.dump(prefs, f, indent=2)


def add_recent_project(project_path: str) -> None:
    """Add a project to recent projects list."""
    prefs = load_preferences()
    
    # Remove if already exists
    if project_path in prefs['recent_projects']:
        prefs['recent_projects'].remove(project_path)
    
    # Add to front
    prefs['recent_projects'].insert(0, project_path)
    
    # Keep only last 10
    prefs['recent_projects'] = prefs['recent_projects'][:10]
    
    save_preferences(prefs)


def get_quick_pattern(pattern_name: str) -> Optional[list]:
    """Get a quick pattern by name."""
    prefs = load_preferences()
    return prefs['quick_patterns'].get(pattern_name)


def save_quick_pattern(name: str, patterns: list) -> None:
    """Save a quick pattern."""
    prefs = load_preferences()
    prefs['quick_patterns'][name] = patterns
    save_preferences(prefs)