"""UI utilities for colored output and better user experience."""

import os
import sys
from typing import Optional

# ANSI color codes
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    DIM = '\033[2m'

# Check if colors should be disabled
NO_COLOR = os.environ.get('NO_COLOR') or not sys.stdout.isatty()

def colored(text: str, color: str, bold: bool = False) -> str:
    """Apply color to text if colors are enabled."""
    if NO_COLOR:
        return text
    
    prefix = color
    if bold:
        prefix = Colors.BOLD + prefix
    
    return f"{prefix}{text}{Colors.ENDC}"

def print_header(text: str) -> None:
    """Print a formatted header."""
    width = 50
    print("\n" + colored("=" * width, Colors.CYAN, bold=True))
    print(colored(text.center(width), Colors.CYAN, bold=True))
    print(colored("=" * width, Colors.CYAN, bold=True))

def print_status(message: str, status: str = "info") -> None:
    """Print a status message with appropriate color."""
    icons = {
        "info": ("ℹ", Colors.BLUE),
        "success": ("✓", Colors.GREEN),
        "warning": ("⚠", Colors.YELLOW),
        "error": ("✗", Colors.RED),
        "question": ("?", Colors.CYAN)
    }
    
    icon, color = icons.get(status, ("•", Colors.DIM))
    print(f"{colored(icon, color, bold=True)} {message}")

def print_progress(current: int, total: int, label: str = "") -> None:
    """Print a progress indicator."""
    if total == 0:
        return
    
    percentage = (current / total) * 100
    bar_length = 30
    filled = int(bar_length * current / total)
    
    bar = "█" * filled + "░" * (bar_length - filled)
    
    if label:
        label = f" {label}"
    
    print(f"\r{colored(bar, Colors.GREEN)} {percentage:3.0f}%{label}", end="", flush=True)
    
    if current == total:
        print()  # New line when complete

def format_size_colored(size: int) -> str:
    """Format file size with color based on size."""
    from .file_utils import format_file_size
    
    size_str = format_file_size(size)
    
    # Color based on size
    if size < 10 * 1024:  # < 10KB
        return colored(size_str, Colors.GREEN)
    elif size < 100 * 1024:  # < 100KB
        return colored(size_str, Colors.YELLOW)
    elif size < 1024 * 1024:  # < 1MB
        return colored(size_str, Colors.YELLOW, bold=True)
    else:  # >= 1MB
        return colored(size_str, Colors.RED, bold=True)

def prompt_yes_no(question: str, default: Optional[bool] = None) -> bool:
    """Prompt user for yes/no answer with color."""
    if default is True:
        prompt = f"{colored('?', Colors.CYAN, bold=True)} {question} [Y/n]: "
    elif default is False:
        prompt = f"{colored('?', Colors.CYAN, bold=True)} {question} [y/N]: "
    else:
        prompt = f"{colored('?', Colors.CYAN, bold=True)} {question} [y/n]: "
    
    while True:
        answer = input(prompt).strip().lower()
        
        if not answer and default is not None:
            return default
        
        if answer in ['y', 'yes']:
            return True
        elif answer in ['n', 'no']:
            return False
        else:
            print_status("Please answer 'y' or 'n'", "warning")

def clear_line() -> None:
    """Clear the current line."""
    print('\r' + ' ' * 80 + '\r', end='', flush=True)