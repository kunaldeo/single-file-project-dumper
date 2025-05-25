import os
import json
from typing import Dict
from .project_utils import detect_project_type, get_smart_defaults


def load_config(root_dir: str) -> Dict:
    """Load .claude-dump config file if it exists."""
    config_file = os.path.join(root_dir, '.claude-dump')
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
                return config
        except Exception as e:
            print(f"Warning: Error loading .claude-dump config: {e}")
    return {}


def save_config_template(root_dir: str) -> None:
    """Save a template .claude-dump config file."""
    project_type = detect_project_type(root_dir)
    smart_defaults = get_smart_defaults(project_type) if project_type else {}
    
    template = {
        "output_file": "project_code.txt",
        "state_file": ".file_dumper_state.json",
        "include": smart_defaults.get('include', ["*"]),
        "exclude": smart_defaults.get('exclude', []),
        "max_file_size_kb": smart_defaults.get('max_file_size', 1000),
        "auto_copy": True,
        "project_type": project_type,
        "template": None,
        "token_limit_warnings": {
            "claude": 150000,
            "gpt-4": 100000,
            "gemini": 800000
        }
    }
    
    config_file = os.path.join(root_dir, '.claude-dump')
    with open(config_file, 'w') as f:
        json.dump(template, f, indent=2)
    
    print(f"\nCreated .claude-dump config file with smart defaults for {project_type or 'generic'} project.")
    print("Edit this file to customize your dump settings.")


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