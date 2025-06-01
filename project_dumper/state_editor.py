import os
import sys
from pathlib import Path
from typing import Dict, Set, List, Optional, Tuple
from rich.console import Console
from rich.tree import Tree
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich.live import Live
from rich.markup import escape
from .file_utils import is_source_file, is_ignored


class TreeItem:
    def __init__(self, path: str, name: str, is_dir: bool, parent: Optional['TreeItem'] = None):
        self.path = path
        self.name = name
        self.is_dir = is_dir
        self.parent = parent
        self.children: List['TreeItem'] = []
        self.expanded = False
        self.selected = False
        self.is_current = False
        
    def add_child(self, child: 'TreeItem'):
        child.parent = self
        self.children.append(child)
        
    def toggle_expansion(self):
        if self.is_dir:
            self.expanded = not self.expanded
            
    def toggle_selection(self):
        self.selected = not self.selected
        if self.is_dir:
            if self.selected:
                self._select_all_children()
            else:
                self._deselect_all_children()
            
    def _select_all_children(self):
        for child in self.children:
            child.selected = True
            if child.is_dir:
                child._select_all_children()
                
    def _deselect_all_children(self):
        for child in self.children:
            child.selected = False
            if child.is_dir:
                child._deselect_all_children()


class StateFileEditor:
    def __init__(self, root_dir: str):
        self.root_dir = Path(root_dir).resolve()
        self.console = Console()
        self.tree_root = None
        self.flat_items: List[TreeItem] = []
        self.current_index = 0
        self.selected_files: Set[str] = set()
        self.running = True
        
    def build_tree(self, gitignore_patterns: Optional[List[str]] = None, state_file: Optional[str] = None) -> TreeItem:
        root_item = TreeItem(".", self.root_dir.name, True)
        root_item.expanded = True
        
        # Add state file to ignore patterns
        ignore_patterns = (gitignore_patterns or []).copy()
        if state_file:
            ignore_patterns.append(os.path.basename(state_file))
            
        self._build_tree_recursive(root_item, self.root_dir, ignore_patterns)
        self.tree_root = root_item
        self._update_flat_items()
        return root_item
        
    def _build_tree_recursive(self, parent_item: TreeItem, directory: Path, gitignore_patterns: List[str]):
        try:
            items = sorted(directory.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
            for item in items:
                relative_path = str(item.relative_to(self.root_dir))
                if is_ignored(relative_path, gitignore_patterns):
                    continue
                
                # Only include directories and source files
                if not item.is_dir() and not is_source_file(str(item)):
                    continue
                    
                relative_path = item.relative_to(self.root_dir)
                tree_item = TreeItem(str(relative_path), item.name, item.is_dir(), parent_item)
                parent_item.add_child(tree_item)
                
                if item.is_dir():
                    self._build_tree_recursive(tree_item, item, gitignore_patterns)
        except PermissionError:
            pass
        
    def _update_flat_items(self):
        self.flat_items = []
        self._flatten_items(self.tree_root)
        
        # Update current item highlighting
        for i, item in enumerate(self.flat_items):
            item.is_current = (i == self.current_index)
        
    def _flatten_items(self, item: TreeItem):
        self.flat_items.append(item)
        if item.expanded and item.is_dir:
            for child in item.children:
                self._flatten_items(child)
    
    def _create_tree_display(self) -> Tree:
        tree = Tree(f"[bold sky_blue3]{escape(self.tree_root.name)}", guide_style="steel_blue")
        self._add_tree_items(tree, self.tree_root, 0)
        return tree
        
    def _add_tree_items(self, tree_widget: Tree, item: TreeItem, level: int):
        for child in item.children:
            # Determine style based on state (dark terminal friendly)
            if child.is_current:
                style = "black on deep_sky_blue1"
            elif child.selected:
                style = "white on sea_green3"
            else:
                style = "bright_white" # Default text color, good for dark backgrounds
                
            # Create display text
            if child.is_dir:
                icon = "📁"
                expand_icon = "▼ " if child.expanded else "▶ "
            else:
                icon = "📄"
                expand_icon = "  "
                
            text = f"{expand_icon}{icon} {escape(child.name)}"
            if child.selected:
                text += " ✓"
                
            branch = tree_widget.add(text, style=style)
            
            if child.expanded and child.is_dir:
                self._add_tree_items(branch, child, level + 1)
                
    def _create_status_panel(self) -> Panel:
        selected_count = len(self.selected_files)
        total_files = sum(1 for item in self.flat_items if not item.is_dir)
        
        status_text = Text()
        status_text.append("Selected: ", style="bold light_steel_blue")
        status_text.append(f"{selected_count}", style="bold spring_green2")
        status_text.append(f" / {total_files} files\n\n", style="grey85") # Slightly softer than bright_white for less emphasis
        
        status_text.append("Controls:\n", style="bold dodger_blue1")
        status_text.append("  ↑/k    ", style="gold3")
        status_text.append("Move up\n", style="grey85")
        status_text.append("  ↓/j    ", style="gold3")
        status_text.append("Move down\n", style="grey85")
        status_text.append("  Space  ", style="gold3")
        status_text.append("Select/deselect\n", style="grey85")
        status_text.append("  Enter  ", style="gold3")
        status_text.append("Expand/collapse\n", style="grey85")
        status_text.append("  q      ", style="bold spring_green2")
        status_text.append("Save & generate dump\n", style="grey85")
        status_text.append("  Ctrl+C ", style="bold orange_red1")
        status_text.append("Cancel (exit without saving)", style="grey85")
        
        return Panel(status_text, title="File State Editor", border_style="royal_blue1")
        
    def _handle_input(self) -> str:
        import termios, tty
        
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setcbreak(fd)
            key = sys.stdin.read(1)
            
            # Handle escape sequences (arrow keys)
            if key == '\x1b':
                next_char = sys.stdin.read(1)
                if next_char == '[':
                    arrow = sys.stdin.read(1)
                    if arrow == 'A':
                        return 'up'
                    elif arrow == 'B':
                        return 'down'
            
            return key
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
            
    def _move_cursor(self, direction: int):
        new_index = self.current_index + direction
        if 0 <= new_index < len(self.flat_items):
            self.current_index = new_index
            self._update_flat_items()
            
    def _toggle_selection(self):
        if self.flat_items and self.current_index < len(self.flat_items):
            current_item = self.flat_items[self.current_index]
            current_item.toggle_selection()
            self._update_selected_files()
            
    def _toggle_expansion(self):
        if self.flat_items and self.current_index < len(self.flat_items):
            current_item = self.flat_items[self.current_index]
            if current_item.is_dir:
                current_item.toggle_expansion()
                self._update_flat_items()
                
    def _update_selected_files(self):
        self.selected_files.clear()
        self._collect_selected_files(self.tree_root)
        
    def _collect_selected_files(self, item: TreeItem):
        if item.selected and not item.is_dir:
            self.selected_files.add(item.path)
        for child in item.children:
            self._collect_selected_files(child)
            
    def _apply_existing_selections(self, existing_selections: Dict[str, bool]):
        """Apply existing selections from state file to the tree."""
        self._apply_selections_recursive(self.tree_root, existing_selections)
        # Update directory selections based on their children
        self._update_directory_selections(self.tree_root)
        self._update_selected_files()
        
    def _apply_selections_recursive(self, item: TreeItem, existing_selections: Dict[str, bool]):
        """Recursively apply selections to tree items."""
        # Check if this file is in existing selections
        if item.path in existing_selections and existing_selections[item.path]:
            item.selected = True
            
        # Process children
        for child in item.children:
            self._apply_selections_recursive(child, existing_selections)
            
    def _update_directory_selections(self, item: TreeItem) -> bool:
        """Update directory selection based on children. Returns True if all children are selected."""
        if not item.is_dir:
            return item.selected
            
        # Check all children first
        all_selected = True
        has_children = False
        
        for child in item.children:
            has_children = True
            if not self._update_directory_selections(child):
                all_selected = False
                
        # If directory has children and all are selected, mark directory as selected
        if has_children and all_selected:
            item.selected = True
            
        return item.selected
            
    def _create_display(self) -> Table:
        tree = self._create_tree_display()
        status = self._create_status_panel()
        
        table = Table.grid(padding=1)
        table.add_column(ratio=1)
        table.add_column(ratio=1)
        table.add_row(tree, status)
        
        return table
        
    def run(self, gitignore_patterns: Optional[List[str]] = None, state_file: Optional[str] = None,
            existing_selections: Optional[Dict[str, bool]] = None) -> Set[str]:
        self.build_tree(gitignore_patterns, state_file)
        
        # Apply existing selections if provided
        if existing_selections:
            self._apply_existing_selections(existing_selections)
        
        save_and_exit = False
        
        with Live(self._create_display(), console=self.console, refresh_per_second=10) as live:
            while self.running:
                try:
                    key = self._handle_input()
                    
                    if key == 'q':
                        # Save and exit
                        save_and_exit = True
                        break
                    elif key == 'up' or key == 'k':
                        self._move_cursor(-1)
                    elif key == 'down' or key == 'j':
                        self._move_cursor(1)
                    elif key == ' ':
                        self._toggle_selection()
                    elif key == '\r' or key == '\n':
                        self._toggle_expansion()
                    
                    live.update(self._create_display())
                    
                except KeyboardInterrupt:
                    # Treat Ctrl+C as exit without saving
                    save_and_exit = False
                    break
                    
        # Return empty set if user chose to exit without saving
        return self.selected_files if save_and_exit else set()


def create_state_editor(root_dir: str, gitignore_patterns: Optional[List[str]] = None, 
                       state_file: Optional[str] = None, existing_selections: Optional[Dict[str, bool]] = None) -> Set[str]:
    editor = StateFileEditor(root_dir)
    return editor.run(gitignore_patterns, state_file, existing_selections)


if __name__ == "__main__":
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    selected = create_state_editor(root)
    print(f"\nSelected {len(selected)} files:")
    for file in sorted(selected):
        print(f"  {file}")