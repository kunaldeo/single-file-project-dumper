"""Modern curses-based TUI interface for file selection and project dumping."""

import os
import curses
import re
from typing import Dict, List, Optional, Tuple
from pathlib import Path

from .file_utils import format_file_size, is_source_file
from .token_utils import estimate_tokens
from .features import suggest_related_files


class CursesFileSelector:
    """Curses-based file selector with modern UI features."""
    
    def __init__(self, stdscr, root_dir: str, selected_files: Dict[str, bool]):
        self.stdscr = stdscr
        self.root_dir = root_dir
        self.selected_files = selected_files
        self.filtered_files = list(selected_files.keys())
        self.current_pos = 0
        self.scroll_offset = 0
        self.search_filter = ""
        self.show_selected_only = False
        self.help_visible = False
        
        # Initialize colors
        curses.start_color()
        curses.use_default_colors()
        
        # Define color pairs
        curses.init_pair(1, curses.COLOR_GREEN, -1)    # Selected items
        curses.init_pair(2, curses.COLOR_CYAN, -1)     # Headers
        curses.init_pair(3, curses.COLOR_YELLOW, -1)   # Highlighted item
        curses.init_pair(4, curses.COLOR_RED, -1)      # Errors/warnings
        curses.init_pair(5, curses.COLOR_MAGENTA, -1)  # Info
        curses.init_pair(6, curses.COLOR_BLUE, -1)     # Secondary info
        curses.init_pair(7, curses.COLOR_WHITE, curses.COLOR_BLUE)  # Status bar
        
        self.colors = {
            'selected': curses.color_pair(1) | curses.A_BOLD,
            'header': curses.color_pair(2) | curses.A_BOLD,
            'highlight': curses.color_pair(3) | curses.A_REVERSE,
            'error': curses.color_pair(4) | curses.A_BOLD,
            'info': curses.color_pair(5),
            'secondary': curses.color_pair(6),
            'status': curses.color_pair(7),
            'normal': curses.A_NORMAL
        }
        
        # Get screen dimensions and use full screen
        self.height, self.width = stdscr.getmaxyx()
        self.list_height = self.height - 3  # Reserve minimal space for header and footer only
        
        # Ensure minimum usable size
        if self.height < 15 or self.width < 60:
            raise Exception("Terminal too small - need at least 60x15")
        
        # Filter files initially
        self.filter_files()
    
    def filter_files(self):
        """Filter files based on search criteria and view mode."""
        all_files = list(self.selected_files.keys())
        
        if self.show_selected_only:
            # Show only selected files
            all_files = [f for f in all_files if self.selected_files[f]]
        
        if self.search_filter:
            # Apply search filter
            try:
                pattern = re.compile(self.search_filter, re.IGNORECASE)
                self.filtered_files = [f for f in all_files if pattern.search(f)]
            except re.error:
                # Invalid regex, use simple string matching
                search_lower = self.search_filter.lower()
                self.filtered_files = [f for f in all_files if search_lower in f.lower()]
        else:
            self.filtered_files = all_files
        
        # Sort files
        self.filtered_files.sort()
        
        # Reset position if out of bounds
        if self.current_pos >= len(self.filtered_files):
            self.current_pos = max(0, len(self.filtered_files) - 1)
    
    def draw_header(self):
        """Draw the header with title and stats."""
        self.stdscr.addstr(0, 0, " " * self.width, self.colors['status'])
        
        title = f" Project Dumper - {os.path.basename(self.root_dir)} "
        self.stdscr.addstr(0, 0, title[:self.width], self.colors['status'])
        
        # Add view mode and stats
        view_mode = "SELECTED" if self.show_selected_only else "ALL"
        selected_count = sum(1 for v in self.selected_files.values() if v)
        total_count = len(self.selected_files)
        
        # Show search filter if active
        filter_info = f" | Filter: {self.search_filter}" if self.search_filter else ""
        
        stats = f" [{view_mode}] {selected_count}/{total_count} selected{filter_info} "
        
        # Ensure we don't overflow
        max_stats_len = self.width - len(title) - 1
        if len(stats) > max_stats_len:
            stats = stats[:max_stats_len-3] + "... "
        
        if len(title) + len(stats) < self.width:
            self.stdscr.addstr(0, self.width - len(stats), stats, self.colors['status'])
    
    
    def draw_file_list(self):
        """Draw the file list with selection indicators."""
        start_y = 1  # Start immediately after header
        
        # Calculate scroll offset
        if self.current_pos < self.scroll_offset:
            self.scroll_offset = self.current_pos
        elif self.current_pos >= self.scroll_offset + self.list_height:
            self.scroll_offset = self.current_pos - self.list_height + 1
        
        # Draw files
        for i in range(self.list_height):
            y = start_y + i
            if y >= self.height - 2:  # Leave space for info and footer
                break
                
            file_idx = self.scroll_offset + i
            if file_idx >= len(self.filtered_files):
                # Clear remaining lines
                self.stdscr.addstr(y, 0, " " * self.width)
                continue
            
            file_path = self.filtered_files[file_idx]
            is_selected = self.selected_files[file_path]
            is_current = file_idx == self.current_pos
            
            # Selection indicator
            indicator = "[✓]" if is_selected else "[ ]"
            
            # File path (truncate if necessary)
            display_path = file_path
            max_path_width = self.width - 20  # Leave space for indicator and size
            if len(display_path) > max_path_width:
                display_path = "..." + display_path[-(max_path_width - 3):]
            
            # File size
            try:
                size = os.path.getsize(os.path.join(self.root_dir, file_path))
                size_str = format_file_size(size)
            except:
                size_str = "???"
            
            # Build the line
            line = f"{indicator} {display_path}"
            padding = max(0, self.width - len(line) - len(size_str) - 1)
            line += " " * padding + size_str
            
            # Truncate if still too long
            if len(line) > self.width:
                line = line[:self.width]
            
            # Choose colors
            if is_current:
                color = self.colors['highlight']
            elif is_selected:
                color = self.colors['selected']
            else:
                color = self.colors['normal']
            
            # Draw the line
            self.stdscr.addstr(y, 0, " " * self.width)  # Clear line
            self.stdscr.addstr(y, 0, line, color)
    
    def draw_info_panel(self):
        """Draw the info panel with stats."""
        y = self.height - 2
        
        selected_files = [f for f, v in self.selected_files.items() if v]
        total_size = 0
        
        for file_path in selected_files:
            try:
                size = os.path.getsize(os.path.join(self.root_dir, file_path))
                total_size += size
            except:
                pass
        
        # Estimate tokens (sample from first few files to avoid slowdown)
        sample_content = ""
        for file_path in selected_files[:5]:  # Sample first 5 files
            try:
                full_path = os.path.join(self.root_dir, file_path)
                if os.path.getsize(full_path) < 100000:  # Only read small files
                    with open(full_path, 'r', encoding='utf-8') as f:
                        sample_content += f.read()[:5000]  # Limit content
            except:
                pass
        
        token_estimate = estimate_tokens(sample_content, 'claude') if sample_content else 0
        if len(selected_files) > 5:
            token_estimate = int(token_estimate * len(selected_files) / 5)  # Rough scaling
        
        info_text = f"Selected: {len(selected_files)} files, Size: {format_file_size(total_size)}, Est. tokens: ~{token_estimate:,}"
        
        self.stdscr.addstr(y, 0, " " * self.width, self.colors['status'])
        if len(info_text) <= self.width:
            self.stdscr.addstr(y, 0, info_text, self.colors['status'])
        else:
            self.stdscr.addstr(y, 0, info_text[:self.width], self.colors['status'])
    
    def draw_help(self):
        """Draw help overlay."""
        if not self.help_visible:
            return
        
        help_lines = [
            "HELP - Key Bindings",
            "",
            "SPACE     - Toggle file selection",
            "ENTER     - Save and continue",
            "a         - Select all visible files",
            "n         - Deselect all files",
            "s         - Toggle between all/selected view",
            "c         - Clear search filter",
            "/         - Enter search mode",
            "f         - Filter source files only",
            "q, ESC    - Quit without saving",
            "h, ?      - Toggle this help",
            "",
            "Navigation:",
            "UP/DOWN   - Move cursor",
            "PAGE UP/DOWN - Scroll page",
            "HOME/END  - Go to start/end",
            "",
            "Press any key to close help"
        ]
        
        # Calculate help window size and position
        help_width = max(len(line) for line in help_lines) + 4
        help_height = len(help_lines) + 2
        
        start_x = (self.width - help_width) // 2
        start_y = (self.height - help_height) // 2
        
        # Create a window for help
        try:
            help_win = curses.newwin(help_height, help_width, start_y, start_x)
            help_win.box()
            
            for i, line in enumerate(help_lines):
                if i < help_height - 2:
                    help_win.addstr(i + 1, 2, line[:help_width - 4])
            
            help_win.refresh()
        except curses.error:
            pass  # Ignore errors if terminal is too small
    
    def draw_footer(self):
        """Draw the footer with key hints."""
        y = self.height - 1
        
        footer_text = " SPACE:Toggle  ENTER:Save  a:All  n:None  s:View  /:Search  h:Help  q:Quit "
        
        self.stdscr.addstr(y, 0, " " * self.width, self.colors['status'])
        if len(footer_text) <= self.width:
            self.stdscr.addstr(y, 0, footer_text, self.colors['status'])
        else:
            self.stdscr.addstr(y, 0, footer_text[:self.width], self.colors['status'])
    
    def draw_screen(self):
        """Draw the entire screen."""
        self.stdscr.clear()
        
        self.draw_header()
        self.draw_file_list()
        self.draw_info_panel()
        self.draw_footer()
        self.draw_help()
        
        self.stdscr.refresh()
    
    def handle_search_mode(self):
        """Handle search input mode."""
        # Show search prompt
        y = self.height - 2
        self.stdscr.addstr(y, 0, " " * self.width)
        self.stdscr.addstr(y, 0, "Search (regex): ", self.colors['header'])
        
        # Get current search text
        search_text = self.search_filter
        cursor_pos = len(search_text)
        
        curses.curs_set(1)  # Show cursor
        
        while True:
            # Display current search text
            display_text = search_text
            if len(display_text) > self.width - 20:
                display_text = "..." + display_text[-(self.width - 23):]
            
            self.stdscr.addstr(y, 16, " " * (self.width - 16))
            self.stdscr.addstr(y, 16, display_text)
            self.stdscr.move(y, 16 + len(display_text))
            self.stdscr.refresh()
            
            ch = self.stdscr.getch()
            
            if ch == ord('\n') or ch == ord('\r'):  # Enter
                break
            elif ch == 27:  # Escape
                search_text = self.search_filter  # Restore original
                break
            elif ch == curses.KEY_BACKSPACE or ch == 127 or ch == 8:
                if search_text:
                    search_text = search_text[:-1]
            elif ch == curses.KEY_DC:  # Delete
                pass  # Could implement if cursor movement is added
            elif 32 <= ch <= 126:  # Printable characters
                search_text += chr(ch)
        
        curses.curs_set(0)  # Hide cursor
        
        # Update search filter and re-filter files
        self.search_filter = search_text
        self.filter_files()
    
    def toggle_current_file(self):
        """Toggle selection of current file."""
        if 0 <= self.current_pos < len(self.filtered_files):
            file_path = self.filtered_files[self.current_pos]
            self.selected_files[file_path] = not self.selected_files[file_path]
    
    def select_all_visible(self):
        """Select all visible files."""
        for file_path in self.filtered_files:
            self.selected_files[file_path] = True
    
    def deselect_all(self):
        """Deselect all files."""
        for file_path in self.selected_files:
            self.selected_files[file_path] = False
    
    def select_source_only(self):
        """Select only source code files."""
        for file_path in self.selected_files:
            self.selected_files[file_path] = is_source_file(file_path)
        self.filter_files()
    
    def run(self) -> Tuple[Dict[str, bool], bool]:
        """Run the file selector interface."""
        curses.curs_set(0)  # Hide cursor
        self.stdscr.keypad(True)  # Enable special keys
        self.stdscr.timeout(-1)  # Block indefinitely for input
        
        # Ensure we have files to display
        if not self.filtered_files:
            with open('/tmp/curses_debug.log', 'w') as f:
                f.write(f"No filtered files found. Total files: {len(self.selected_files)}\n")
            return self.selected_files, False
        
        while True:
            self.draw_screen()
            
            ch = self.stdscr.getch()
            
            # Debug log the input
            with open('/tmp/curses_debug.log', 'a') as f:
                f.write(f"Got key: {ch} ({chr(ch) if 32 <= ch <= 126 else 'special'})\n")
            
            # Navigation
            if ch == curses.KEY_UP:
                self.current_pos = max(0, self.current_pos - 1)
            elif ch == curses.KEY_DOWN:
                self.current_pos = min(len(self.filtered_files) - 1, self.current_pos + 1)
            elif ch == curses.KEY_PPAGE:  # Page Up
                self.current_pos = max(0, self.current_pos - self.list_height)
            elif ch == curses.KEY_NPAGE:  # Page Down
                self.current_pos = min(len(self.filtered_files) - 1, self.current_pos + self.list_height)
            elif ch == curses.KEY_HOME:
                self.current_pos = 0
            elif ch == curses.KEY_END:
                self.current_pos = max(0, len(self.filtered_files) - 1)
            
            # Actions
            elif ch == ord(' '):  # Space - toggle selection
                self.toggle_current_file()
                # Move to next file
                self.current_pos = min(len(self.filtered_files) - 1, self.current_pos + 1)
            elif ch == ord('\n') or ch == ord('\r'):  # Enter - save and exit
                return self.selected_files, True
            elif ch == ord('a') or ch == ord('A'):  # Select all
                self.select_all_visible()
            elif ch == ord('n') or ch == ord('N'):  # Select none
                self.deselect_all()
            elif ch == ord('s') or ch == ord('S'):  # Toggle view mode
                self.show_selected_only = not self.show_selected_only
                self.filter_files()
            elif ch == ord('c') or ch == ord('C'):  # Clear filter
                self.search_filter = ""
                self.filter_files()
            elif ch == ord('/'):  # Search mode
                self.handle_search_mode()
            elif ch == ord('f') or ch == ord('F'):  # Filter source files
                self.select_source_only()
            elif ch == ord('h') or ch == ord('H') or ch == ord('?'):  # Help
                self.help_visible = not self.help_visible
            elif ch == ord('q') or ch == ord('Q') or ch == 27:  # Quit
                return self.selected_files, False
            
            # Ensure current position is valid
            if self.filtered_files:
                self.current_pos = max(0, min(self.current_pos, len(self.filtered_files) - 1))
            else:
                self.current_pos = 0


def run_curses_file_selection(root_dir: str, selected_files: Dict[str, bool]) -> Tuple[Dict[str, bool], bool]:
    """Run the curses-based file selection interface."""
    
    # Check if we have any files to show
    if not selected_files:
        print("No files found to display in interactive mode")
        return selected_files, False
    
    def main(stdscr):
        try:
            # Initialize curses properly
            stdscr.nodelay(False)
            stdscr.clear()
            stdscr.refresh()
            
            selector = CursesFileSelector(stdscr, root_dir, selected_files)
            return selector.run()
        except Exception as e:
            # Write error to a file for debugging
            with open('/tmp/curses_error.log', 'w') as f:
                f.write(f"Curses error: {e}\n")
                import traceback
                traceback.print_exc(file=f)
            raise
    
    # Note: We don't check isatty() here because some environments (like Claude Code)
    # may not report as TTY but still support curses
    
    try:
        return curses.wrapper(main)
    except KeyboardInterrupt:
        return selected_files, False
    except Exception as e:
        # Write detailed error info
        print(f"Curses interface failed: {e}")
        print("Falling back to text interface...")
        # Fallback to non-interactive mode if curses fails
        return selected_files, True