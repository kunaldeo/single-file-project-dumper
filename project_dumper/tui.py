"""Modern TUI interface using Textual for file selection and project dumping."""

import os
from typing import Dict, Set, List, Optional, Tuple
from pathlib import Path

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.widgets import (
    Header, Footer, Button, Checkbox, Static, Tree, Input, 
    DataTable, ProgressBar, Label, TabbedContent, TabPane,
    ListView, ListItem, Collapsible, Pretty, SelectionList
)
from textual.binding import Binding
from textual.reactive import reactive
from textual.screen import Screen
from textual.message import Message
from textual import events

from .file_utils import format_file_size, is_source_file
from .token_utils import estimate_tokens
from .features import suggest_related_files, generate_dump_summary


class FileSelectionScreen(Screen):
    """Main file selection screen with tree view and controls."""
    
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("enter", "save_and_dump", "Save & Dump"),
        Binding("ctrl+s", "save_and_dump", "Save & Dump"),
        Binding("ctrl+a", "select_all", "Select All"),
        Binding("ctrl+n", "select_none", "Select None"),
        Binding("space", "toggle_selected", "Toggle"),
        Binding("ctrl+p", "select_pattern", "Pattern"),
        Binding("ctrl+o", "select_source_only", "Source Only"),
        Binding("ctrl+e", "select_by_extension", "Extensions"),
        Binding("ctrl+r", "preview", "Preview"),
        Binding("ctrl+f", "filter_files", "Filter"),
        Binding("escape", "clear_filter", "Clear Filter"),
        Binding("tab", "next_tab", "Next Tab"),
        Binding("shift+tab", "prev_tab", "Prev Tab"),
    ]
    
    def __init__(self, root_dir: str, selected_files: Dict[str, bool], **kwargs):
        super().__init__(**kwargs)
        self.root_dir = root_dir
        self.selected_files = selected_files
        self.filtered_files = list(selected_files.keys())
        self.search_filter = ""
        
    def compose(self) -> ComposeResult:
        """Create the layout."""
        yield Header()
        
        with TabbedContent(initial="files"):
            with TabPane("Files", id="files"):
                with Horizontal():
                    # Left panel - file tree
                    with Vertical(classes="left-panel"):
                        yield Static("📁 Project Files", classes="panel-title")
                        with Container(classes="search-container"):
                            yield Input(
                                placeholder="Filter files (regex)...",
                                id="file-filter"
                            )
                        yield self._create_file_list()
                    
                    # Right panel - file info and controls
                    with Vertical(classes="right-panel"):
                        yield Static("📊 Selection Info", classes="panel-title")
                        yield self._create_info_panel()
                        yield Static("🎯 Quick Actions", classes="panel-title")
                        yield self._create_action_panel()
                        
            with TabPane("Preview", id="preview"):
                yield self._create_preview_panel()
                
            with TabPane("Suggestions", id="suggestions"):
                yield self._create_suggestions_panel()
        
        yield Footer()
    
    def _create_file_list(self) -> SelectionList:
        """Create the file selection list."""
        selections = []
        for file_path in sorted(self.filtered_files):
            is_selected = self.selected_files.get(file_path, False)
            try:
                size = os.path.getsize(os.path.join(self.root_dir, file_path))
                size_str = format_file_size(size)
                display_text = f"{file_path} ({size_str})"
            except:
                display_text = file_path
                
            selections.append((display_text, file_path, is_selected))
        
        return SelectionList(*selections, id="file-list")
    
    def _create_info_panel(self) -> Container:
        """Create the information panel."""
        return Container(
            Static("Selected: 0 files", id="selected-count"),
            Static("Total size: 0 B", id="total-size"),
            Static("Est. tokens: ~0", id="token-estimate"),
            classes="info-panel"
        )
    
    def _create_action_panel(self) -> Container:
        """Create the action buttons panel."""
        return Container(
            Button("🎯 Select by Pattern", id="pattern-select", variant="primary"),
            Button("📝 Select Source Only", id="source-only"),
            Button("🗂️ Select by Extension", id="ext-select"),
            Button("🔄 Toggle All", id="toggle-all"),
            Button("🗑️ Clear Selection", id="clear-all"),
            Button("💾 Save & Dump", id="save-dump", variant="success"),
            classes="action-panel"
        )
    
    def _create_preview_panel(self) -> Container:
        """Create the preview panel."""
        return Container(
            Static("📋 Output Preview", classes="panel-title"),
            Pretty("", id="preview-content"),
            classes="preview-panel"
        )
    
    def _create_suggestions_panel(self) -> Container:
        """Create the suggestions panel."""
        return Container(
            Static("💡 Suggested Files", classes="panel-title"),
            Static("Loading suggestions...", id="suggestions-content"),
            Button("Add All Suggestions", id="add-suggestions", variant="primary"),
            classes="suggestions-panel"
        )
    
    def on_mount(self) -> None:
        """Called when the screen is mounted."""
        self.update_info_panel()
        self.load_suggestions()
    
    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle search filter changes."""
        if event.input.id == "file-filter":
            self.search_filter = event.value
            self.filter_files()
    
    def on_selection_list_selection_toggled(self, event: SelectionList.SelectionToggled) -> None:
        """Handle file selection toggle."""
        if event.selection_list.id == "file-list":
            file_path = event.selection.value
            self.selected_files[file_path] = event.selection.selected
            self.update_info_panel()
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "pattern-select":
            self.action_select_pattern()
        elif event.button.id == "source-only":
            self.action_select_source_only()
        elif event.button.id == "ext-select":
            self.action_select_by_extension()
        elif event.button.id == "toggle-all":
            self.action_toggle_all()
        elif event.button.id == "clear-all":
            self.action_clear_all()
        elif event.button.id == "save-dump":
            self.action_save_and_dump()
        elif event.button.id == "add-suggestions":
            self.action_add_suggestions()
    
    def filter_files(self) -> None:
        """Filter files based on search criteria."""
        if not self.search_filter:
            self.filtered_files = list(self.selected_files.keys())
        else:
            import re
            try:
                pattern = re.compile(self.search_filter, re.IGNORECASE)
                self.filtered_files = [
                    f for f in self.selected_files.keys()
                    if pattern.search(f)
                ]
            except re.error:
                # Invalid regex, use simple string matching
                self.filtered_files = [
                    f for f in self.selected_files.keys()
                    if self.search_filter.lower() in f.lower()
                ]
        
        # Refresh the file list
        file_list = self.query_one("#file-list", SelectionList)
        file_list.clear_options()
        
        selections = []
        for file_path in sorted(self.filtered_files):
            is_selected = self.selected_files.get(file_path, False)
            try:
                size = os.path.getsize(os.path.join(self.root_dir, file_path))
                size_str = format_file_size(size)
                display_text = f"{file_path} ({size_str})"
            except:
                display_text = file_path
                
            selections.append((display_text, file_path, is_selected))
        
        file_list.add_options(selections)
    
    def update_info_panel(self) -> None:
        """Update the information panel with current stats."""
        selected_count = sum(1 for v in self.selected_files.values() if v)
        total_size = 0
        total_content = ""
        
        for file_path, is_selected in self.selected_files.items():
            if is_selected:
                try:
                    full_path = os.path.join(self.root_dir, file_path)
                    size = os.path.getsize(full_path)
                    total_size += size
                    
                    # Read content for token estimation (limit to avoid memory issues)
                    if size < 1024 * 1024:  # Only read files < 1MB
                        try:
                            with open(full_path, 'r', encoding='utf-8') as f:
                                total_content += f.read()[:10000]  # Limit content length
                        except:
                            pass
                except:
                    pass
        
        # Estimate tokens
        token_count = estimate_tokens(total_content, 'claude') if total_content else 0
        
        self.query_one("#selected-count", Static).update(f"Selected: {selected_count} files")
        self.query_one("#total-size", Static).update(f"Total size: {format_file_size(total_size)}")
        self.query_one("#token-estimate", Static).update(f"Est. tokens: ~{token_count:,}")
    
    def load_suggestions(self) -> None:
        """Load file suggestions."""
        try:
            suggestions = suggest_related_files(self.root_dir, self.selected_files)
            if suggestions:
                content = "\n".join([f"• {f}" for f in suggestions[:20]])  # Show first 20
                if len(suggestions) > 20:
                    content += f"\n... and {len(suggestions) - 20} more"
            else:
                content = "No additional suggestions found."
            
            self.query_one("#suggestions-content", Static).update(content)
        except Exception as e:
            self.query_one("#suggestions-content", Static).update(f"Error loading suggestions: {e}")
    
    def update_preview_panel(self) -> None:
        """Update the preview panel with current selection summary."""
        try:
            selected_files = [f for f, v in self.selected_files.items() if v]
            total_size = 0
            
            for file_path in selected_files:
                try:
                    full_path = os.path.join(self.root_dir, file_path)
                    total_size += os.path.getsize(full_path)
                except:
                    pass
            
            # Create preview content
            preview_data = {
                "selected_files": len(selected_files),
                "total_size": format_file_size(total_size),
                "files": selected_files[:15]  # Show first 15 files
            }
            
            if len(selected_files) > 15:
                preview_data["more_files"] = len(selected_files) - 15
            
            self.query_one("#preview-content", Pretty).update(preview_data)
        except Exception as e:
            self.query_one("#preview-content", Pretty).update({"error": str(e)})
    
    def action_select_pattern(self) -> None:
        """Show pattern selection dialog."""
        self.app.push_screen(PatternSelectScreen(self.selected_files), self.handle_pattern_result)
    
    def action_select_source_only(self) -> None:
        """Select only source code files."""
        count = 0
        for file_path in self.selected_files:
            if is_source_file(file_path):
                if not self.selected_files[file_path]:
                    count += 1
                self.selected_files[file_path] = True
            else:
                self.selected_files[file_path] = False
        self.filter_files()
        self.update_info_panel()
        self.notify(f"Selected {count} source files", severity="information")
    
    def action_select_by_extension(self) -> None:
        """Show extension selection dialog."""
        extensions = set()
        for file_path in self.selected_files:
            ext = os.path.splitext(file_path)[1]
            if ext:
                extensions.add(ext)
        
        self.app.push_screen(ExtensionSelectScreen(sorted(extensions), self.selected_files), 
                           self.handle_extension_result)
    
    def action_toggle_all(self) -> None:
        """Toggle selection of all visible files."""
        visible_files = self.filtered_files
        # Check if all visible are selected
        all_selected = all(self.selected_files.get(f, False) for f in visible_files)
        
        # Toggle: if all selected, deselect all; otherwise select all
        new_state = not all_selected
        for file_path in visible_files:
            self.selected_files[file_path] = new_state
        
        self.filter_files()
        self.update_info_panel()
    
    def action_clear_all(self) -> None:
        """Clear all selections."""
        for file_path in self.selected_files:
            self.selected_files[file_path] = False
        self.filter_files()
        self.update_info_panel()
    
    def action_save_and_dump(self) -> None:
        """Save selections and proceed with dump."""
        self.app.exit((self.selected_files, True))
    
    def action_add_suggestions(self) -> None:
        """Add all suggested files."""
        try:
            suggestions = suggest_related_files(self.root_dir, self.selected_files)
            for file_path in suggestions:
                if file_path in self.selected_files:
                    self.selected_files[file_path] = True
            self.filter_files()
            self.update_info_panel()
        except Exception:
            pass
    
    def action_quit(self) -> None:
        """Quit without saving."""
        self.app.exit((self.selected_files, False))
    
    def action_select_all(self) -> None:
        """Select all visible files."""
        count = 0
        for file_path in self.filtered_files:
            if not self.selected_files[file_path]:
                count += 1
            self.selected_files[file_path] = True
        self.filter_files()
        self.update_info_panel()
        self.notify(f"Selected {count} files", severity="information")
    
    def action_select_none(self) -> None:
        """Deselect all files."""
        count = sum(1 for v in self.selected_files.values() if v)
        for file_path in self.selected_files:
            self.selected_files[file_path] = False
        self.filter_files()
        self.update_info_panel()
        self.notify(f"Deselected {count} files", severity="information")
    
    def action_toggle_selected(self) -> None:
        """Toggle selection of currently focused file."""
        file_list = self.query_one("#file-list", SelectionList)
        if file_list.highlighted is not None:
            option = file_list.get_option_at_index(file_list.highlighted)
            if option:
                file_path = option.value
                self.selected_files[file_path] = not self.selected_files[file_path]
                self.filter_files()
                self.update_info_panel()
    
    def action_clear_filter(self) -> None:
        """Clear the search filter."""
        filter_input = self.query_one("#file-filter", Input)
        filter_input.value = ""
        self.search_filter = ""
        self.filter_files()
    
    def action_next_tab(self) -> None:
        """Switch to next tab."""
        tabs = self.query_one(TabbedContent)
        tabs.next_tab()
    
    def action_prev_tab(self) -> None:
        """Switch to previous tab."""
        tabs = self.query_one(TabbedContent)
        tabs.previous_tab()
    
    def action_preview(self) -> None:
        """Switch to preview tab and update content."""
        tabs = self.query_one(TabbedContent)
        tabs.active = "preview"
        self.update_preview_panel()
    
    def action_filter_files(self) -> None:
        """Focus the filter input."""
        filter_input = self.query_one("#file-filter", Input)
        filter_input.focus()
    
    def handle_pattern_result(self, result: Optional[str]) -> None:
        """Handle pattern selection result."""
        if result:
            import fnmatch
            for file_path in self.selected_files:
                if fnmatch.fnmatch(file_path, result):
                    self.selected_files[file_path] = True
            self.filter_files()
            self.update_info_panel()
    
    def handle_extension_result(self, result: Optional[List[str]]) -> None:
        """Handle extension selection result."""
        if result:
            for file_path in self.selected_files:
                ext = os.path.splitext(file_path)[1]
                self.selected_files[file_path] = ext in result
            self.filter_files()
            self.update_info_panel()


class PatternSelectScreen(Screen):
    """Screen for pattern-based file selection."""
    
    def __init__(self, selected_files: Dict[str, bool], **kwargs):
        super().__init__(**kwargs)
        self.selected_files = selected_files
    
    def compose(self) -> ComposeResult:
        with Container(classes="pattern-dialog"):
            yield Static("Select files by pattern", classes="dialog-title")
            yield Input(placeholder="e.g., *.py, test_*, **/models/*", id="pattern-input")
            with Horizontal(classes="dialog-buttons"):
                yield Button("Apply", id="apply", variant="primary")
                yield Button("Cancel", id="cancel")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "apply":
            pattern = self.query_one("#pattern-input", Input).value
            self.dismiss(pattern if pattern else None)
        elif event.button.id == "cancel":
            self.dismiss(None)


class ExtensionSelectScreen(Screen):
    """Screen for extension-based file selection."""
    
    def __init__(self, extensions: List[str], selected_files: Dict[str, bool], **kwargs):
        super().__init__(**kwargs)
        self.extensions = extensions
        self.selected_files = selected_files
    
    def compose(self) -> ComposeResult:
        with Container(classes="extension-dialog"):
            yield Static("Select file extensions", classes="dialog-title")
            
            options = [(ext, ext, False) for ext in self.extensions]
            yield SelectionList(*options, id="ext-list")
            
            with Horizontal(classes="dialog-buttons"):
                yield Button("Apply", id="apply", variant="primary")
                yield Button("Cancel", id="cancel")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "apply":
            ext_list = self.query_one("#ext-list", SelectionList)
            selected_exts = [option.value for option in ext_list.selected]
            self.dismiss(selected_exts if selected_exts else None)
        elif event.button.id == "cancel":
            self.dismiss(None)


class ProjectDumperTUI(App):
    """Main TUI application for project dumping."""
    
    CSS = """
    Screen {
        background: $surface;
    }
    
    .left-panel {
        width: 65%;
        border: round $primary;
        padding: 1;
        margin: 1;
    }
    
    .right-panel {
        width: 35%;
        border: round $accent;
        padding: 1;
        margin: 1;
    }
    
    .panel-title {
        color: $primary;
        text-style: bold;
        margin-bottom: 1;
        text-align: center;
        background: $primary 10%;
        padding: 0 1;
        border-radius: 1;
    }
    
    .search-container {
        height: 3;
        margin-bottom: 1;
    }
    
    .search-container Input {
        border: round $accent;
    }
    
    .info-panel {
        height: 10;
        border: round $success;
        padding: 1;
        margin-bottom: 1;
        background: $success 5%;
    }
    
    .info-panel Static {
        margin-bottom: 1;
        color: $text;
        text-style: bold;
    }
    
    .action-panel {
        height: auto;
        border: round $warning;
        padding: 1;
        background: $warning 5%;
    }
    
    .action-panel Button {
        width: 100%;
        margin-bottom: 1;
        border: round;
    }
    
    .preview-panel {
        height: 100%;
        border: round $accent;
        padding: 1;
        background: $accent 5%;
    }
    
    .suggestions-panel {
        height: 100%;
        border: round $warning;
        padding: 1;
        background: $warning 5%;
    }
    
    .pattern-dialog, .extension-dialog {
        width: 60;
        height: 15;
        border: round $primary;
        background: $surface;
        padding: 2;
        margin: 2;
    }
    
    .dialog-title {
        text-align: center;
        text-style: bold;
        margin-bottom: 2;
        color: $primary;
    }
    
    .dialog-buttons {
        height: 3;
        margin-top: 2;
    }
    
    .dialog-buttons Button {
        width: 50%;
        margin: 0 1;
        border: round;
    }
    
    SelectionList {
        height: 100%;
        border: round $accent;
        scrollbar-background: $primary 30%;
        scrollbar-color: $primary;
    }
    
    SelectionList:focus {
        border: round $primary;
    }
    
    TabbedContent {
        height: 100%;
    }
    
    TabPane {
        padding: 1;
        height: 100%;
    }
    
    Header {
        background: $primary;
        color: $text;
        text-style: bold;
    }
    
    Footer {
        background: $accent;
        color: $text;
    }
    """
    
    def __init__(self, root_dir: str, selected_files: Dict[str, bool], **kwargs):
        super().__init__(**kwargs)
        self.root_dir = root_dir
        self.selected_files = selected_files
    
    def on_mount(self) -> None:
        """Called when the app is mounted."""
        self.title = f"Project Dumper - {os.path.basename(self.root_dir)}"
        self.sub_title = self.root_dir
        self.push_screen(FileSelectionScreen(self.root_dir, self.selected_files))


def run_tui_file_selection(root_dir: str, selected_files: Dict[str, bool]) -> Tuple[Dict[str, bool], bool]:
    """Run the TUI file selection interface."""
    app = ProjectDumperTUI(root_dir, selected_files)
    result = app.run()
    
    if result is None:
        return selected_files, False
    
    return result