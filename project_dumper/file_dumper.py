import os
import argparse
import fnmatch
from typing import Set, Dict, List, Tuple, Optional

# Import from our new modules
from .file_utils import (
    load_gitignore, is_ignored, generate_source_tree, 
    wrap_code_block, format_file_size, is_source_file
)
from .token_utils import estimate_tokens, check_token_limits
from .project_utils import detect_project_type, get_smart_defaults
from .config import load_config, save_config_template, load_state, save_state
from .interactive import interactive_edit_mode, copy_to_clipboard
from .state_editor import create_state_editor
from .template import load_template, render_template
from .ui_utils import print_status, prompt_yes_no, colored, Colors, print_progress
from .features import create_dump_manifest, export_to_formats
from .preferences import load_preferences, save_preferences, add_recent_project


def auto_select_files(root_dir: str, gitignore_patterns: List[str], 
                     script_name: str, output_file: str, 
                     include_patterns: Optional[List[str]] = None,
                     max_file_size_kb: int = 1000,
                     state_file: Optional[str] = None) -> Dict[str, bool]:
    """Automatically select files based on patterns without prompting."""
    selected_files = {}
    ignore_files = [script_name, os.path.basename(output_file)]
    if state_file:
        ignore_files.append(os.path.basename(state_file))
    
    for root, dirs, files in os.walk(root_dir, topdown=True):
        rel_path = os.path.relpath(root, root_dir)
        if rel_path == '.':
            rel_path = ''
            
        # Filter directories based on gitignore
        dirs[:] = [d for d in dirs if not is_ignored(
            os.path.normpath(os.path.join(rel_path, d)), gitignore_patterns)]
        
        # Process files
        for file in files:
            file_path = os.path.normpath(os.path.join(rel_path, file))
            full_file_path = os.path.join(root_dir, file_path)
            
            try:
                file_size = os.path.getsize(full_file_path)
            except:
                continue
                
            # Skip files based on criteria
            if (is_ignored(file_path, gitignore_patterns) or
                file in ignore_files or
                file.startswith('.') or
                file_size == 0 or
                file_size > max_file_size_kb * 1024 or
                not is_source_file(file_path)):
                continue
                
            # Check include patterns if specified
            if include_patterns:
                if any(fnmatch.fnmatch(file_path, pattern) for pattern in include_patterns):
                    selected_files[file_path] = True
            else:
                # Include by default if no patterns specified
                selected_files[file_path] = True
                
    return selected_files


def select_files(root_dir: str, gitignore_patterns: List[str], 
                existing_state: Dict, state_file: str, 
                script_name: str, output_file: str, 
                include_patterns: Optional[List[str]] = None,
                max_file_size_kb: int = 1000) -> Tuple[Dict[str, bool], Set[str], Set[str]]:
    """Interactive file selection process."""
    selected_files = existing_state.get('selected_files', {})
    skipped_dirs = existing_state.get('skipped_dirs', set())
    selected_dirs = existing_state.get('selected_dirs', set())
    
    # Clean up missing files from state
    selected_files = {k: v for k, v in selected_files.items() 
                     if os.path.exists(os.path.join(root_dir, k))}
    
    # Files to ignore
    ignore_files = [script_name, os.path.basename(state_file), os.path.basename(output_file)]
    
    # Count total files for progress
    total_files = sum(1 for _, _, files in os.walk(root_dir) for _ in files)
    processed_files = 0
    
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
                
            include = prompt_yes_no(f"Include directory '{colored(dir_path, Colors.CYAN)}'?")
            if include:
                filtered_dirs.append(d)
                selected_dirs.add(dir_path)
                print_status(f"Added directory: {dir_path}", "success")
            else:
                skipped_dirs.add(dir_path)
                print_status(f"Skipped directory: {dir_path}", "info")
                
        dirs[:] = filtered_dirs
        
        # Process files in included directories
        for file in files:
            file_path = os.path.normpath(os.path.join(rel_path, file))
            full_file_path = os.path.join(root_dir, file_path)
            file_size = os.path.getsize(full_file_path)
            
            if (is_ignored(file_path, gitignore_patterns) or
                file in ignore_files or
                file.startswith('.') or
                file_size == 0 or
                file_size > max_file_size_kb * 1024 or
                not is_source_file(file_path)):
                continue
                
            # Check include patterns if specified
            if include_patterns:
                if not any(fnmatch.fnmatch(file_path, pattern) for pattern in include_patterns):
                    continue
                
            if file_path not in selected_files:
                size_str = format_file_size(file_size)
                include = prompt_yes_no(f"Include '{colored(file_path, Colors.CYAN)}' ({size_str})?")
                selected_files[file_path] = include
                if include:
                    print_status(f"Selected: {file_path}", "success")
                else:
                    print_status(f"Excluded: {file_path}", "info")
                
            # Update progress
            processed_files += 1
                
    return selected_files, skipped_dirs, selected_dirs


def dump_files(root_dir: str, selected_files: Dict[str, bool], output_file: str, 
               template_path: Optional[str] = None) -> None:
    """Write selected files to output with formatting."""
    
    if template_path:
        # Use template-based output
        dump_files_with_template(root_dir, selected_files, output_file, template_path)
    else:
        # Use default markdown format
        dump_files_markdown(root_dir, selected_files, output_file)


def dump_files_markdown(root_dir: str, selected_files: Dict[str, bool], output_file: str) -> None:
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


def dump_files_with_template(root_dir: str, selected_files: Dict[str, bool], 
                            output_file: str, template_path: str) -> None:
    """Write selected files using a template."""
    template = load_template(template_path)
    
    # Prepare context for template
    files_data = []
    for file_path, include in selected_files.items():
        if include:
            full_path = os.path.join(root_dir, file_path)
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    files_data.append({
                        'path': file_path,
                        'code': wrap_code_block(content, file_path)
                    })
            except UnicodeDecodeError:
                files_data.append({
                    'path': file_path,
                    'code': None
                })
    
    context = {
        'absolute_code_path': os.path.abspath(root_dir),
        'source_tree': generate_source_tree(root_dir, selected_files, True),
        'files': files_data
    }
    
    # Render and write
    output = render_template(template, context)
    with open(output_file, 'w', encoding='utf-8') as out:
        out.write(output)


def main():
    parser = argparse.ArgumentParser(
        description="File Dumper Script - Automatically generates a code dump of your project. "
                    "Runs in automatic mode by default, use --interactive for manual file selection."
    )
    parser.add_argument("root_dir", nargs='?', help="Root directory to start file dumping",
                       default=os.getcwd())
    parser.add_argument("--output-file", "-o", help="Output file name")
    parser.add_argument("--state-file", help="Path to state file")
    parser.add_argument("--edit", "-e", action="store_true", 
                       help="Jump directly to edit mode with existing state")
    parser.add_argument("--interactive", "-i", action="store_true",
                       help="Interactive mode for file management and export options")
    parser.add_argument("--include", help="Include files matching pattern", action="append")
    parser.add_argument("--exclude", help="Exclude files matching pattern", action="append")
    parser.add_argument("--max-file-size", "-m", type=int, help="Maximum file size in KB")
    parser.add_argument("--copy", "-c", action="store_true", help="Copy output to clipboard")
    parser.add_argument("--init", action="store_true", 
                       help="Initialize a .claude-dump config file")
    parser.add_argument("--template", "-t", help="Path to Handlebars template file")
    parser.add_argument("--manifest", action="store_true", 
                       help="Create a manifest file with dump metadata")
    parser.add_argument("--format", "-f", choices=["markdown", "json", "html"],
                       help="Export to additional formats")
    parser.add_argument("--reset", "-r", action="store_true",
                       help="Clear saved file selections and start fresh")
    parser.add_argument("--state-editor", "-s", action="store_true",
                       help="Use tree-based state editor for file selection")
    
    args = parser.parse_args()

    root_dir = args.root_dir
    
    # Handle --init flag
    if args.init:
        save_config_template(root_dir)
        return
    
    # Load config file
    config = load_config(root_dir)
    
    # Command line args override config file
    output_file = args.output_file or config.get('output_file', 'project_code.txt')
    state_file = args.state_file or config.get('state_file', '.file_dumper_state.json')
    max_file_size = args.max_file_size or config.get('max_file_size_kb', 1000)
    should_copy = args.copy or config.get('auto_copy', False)
    include_patterns = args.include or config.get('include', [])
    exclude_patterns = args.exclude or config.get('exclude', [])
    template_path = args.template or config.get('template')
    
    # Handle --reset flag
    if args.reset and os.path.exists(state_file):
        os.remove(state_file)
        print_status("Cleared saved file selections", "success")
    
    # Check if this is first run
    prefs = load_preferences()
    is_first_run = root_dir not in prefs.get('recent_projects', [])
    
    # Determine mode
    run_interactive = args.interactive
    
    # Add to recent projects
    add_recent_project(root_dir)
    
    # Load gitignore patterns
    gitignore_patterns = load_gitignore(root_dir)
    if exclude_patterns:
        gitignore_patterns.extend(exclude_patterns)
    
    # Apply smart defaults based on project type
    detected_type = detect_project_type(root_dir)
    if detected_type and not config.get('project_type'):
        smart = get_smart_defaults(detected_type)
        if not args.include:
            include_patterns = smart.get('include', [])
        if not args.exclude:
            gitignore_patterns.extend(smart.get('exclude', []))
        if not args.max_file_size:
            max_file_size = smart.get('max_file_size', 1000)
    
    if args.state_editor or args.edit:
        # State editor mode (including edit mode)
        mode_name = "edit mode" if args.edit else "state editor"
        print_status(f"Starting {mode_name} in {colored(root_dir, Colors.CYAN, bold=True)}", "info")
        
        # Always load existing state if available for both modes
        existing_state = load_state(state_file)
        existing_selections = {}
        if existing_state.get('selected_files') and existing_state.get('root_dir') == root_dir:
            # Filter to only include files that are actually selected (value is True)
            existing_selections = {k: v for k, v in existing_state['selected_files'].items() if v}
            if existing_selections:
                print_status(f"Loaded {colored(str(len(existing_selections)), Colors.GREEN)} previously selected files", "info")
        
        selected_file_paths = create_state_editor(root_dir, gitignore_patterns, state_file, existing_selections)
        
        # Check if user cancelled (ESC or Ctrl+C)
        if not selected_file_paths:
            print_status("Cancelled - no files selected", "warning")
            return
        
        # Convert set of paths to dict format expected by the rest of the system
        # Only include files that are source files and not ignored
        selected_files = {}
        for root, dirs, files in os.walk(root_dir):
            rel_path = os.path.relpath(root, root_dir)
            if rel_path == '.':
                rel_path = ''
                
            # Filter directories based on gitignore
            dirs[:] = [d for d in dirs if not is_ignored(
                os.path.normpath(os.path.join(rel_path, d)), gitignore_patterns)]
            
            for file in files:
                file_path = os.path.normpath(os.path.join(rel_path, file))
                
                # Skip if ignored or not a source file
                if is_ignored(file_path, gitignore_patterns) or not is_source_file(file_path):
                    continue
                    
                # Only add to selected_files if it's a valid source file
                selected_files[file_path] = file_path in selected_file_paths
        
        # Set should_save to True since we want to dump the selected files
        should_save = True
        skipped_dirs = set()
        selected_dirs = set()
        
    elif run_interactive:
        # Interactive mode - use state editor for file selection, then edit mode
        print_status(f"Starting interactive mode in {colored(root_dir, Colors.CYAN, bold=True)}", "info")
        
        # Always load existing state if available for both modes
        existing_state = load_state(state_file)
        existing_selections = {}
        if existing_state.get('selected_files') and existing_state.get('root_dir') == root_dir:
            # Filter to only include files that are actually selected (value is True)
            existing_selections = {k: v for k, v in existing_state['selected_files'].items() if v}
            if existing_selections:
                print_status(f"Loaded {colored(str(len(existing_selections)), Colors.GREEN)} previously selected files", "info")
        
        # First use state editor to select files
        selected_file_paths = create_state_editor(root_dir, gitignore_patterns, state_file, existing_selections)
        
        # Check if user cancelled (ESC or Ctrl+C)
        if not selected_file_paths:
            print_status("Cancelled - no files selected", "warning")
            return
        
        # Convert to expected format
        # Only include files that are source files and not ignored
        selected_files = {}
        for root, dirs, files in os.walk(root_dir):
            rel_path = os.path.relpath(root, root_dir)
            if rel_path == '.':
                rel_path = ''
                
            # Filter directories based on gitignore
            dirs[:] = [d for d in dirs if not is_ignored(
                os.path.normpath(os.path.join(rel_path, d)), gitignore_patterns)]
            
            for file in files:
                file_path = os.path.normpath(os.path.join(rel_path, file))
                
                # Skip if ignored or not a source file
                if is_ignored(file_path, gitignore_patterns) or not is_source_file(file_path):
                    continue
                    
                # Only add to selected_files if it's a valid source file
                selected_files[file_path] = file_path in selected_file_paths
        
        skipped_dirs = set()
        selected_dirs = set()
        
        # Enter interactive edit mode for advanced options
        selected_files, should_save = interactive_edit_mode(
            root_dir, selected_files, skipped_dirs, selected_dirs, 
            gitignore_patterns, output_file
        )
        
    else:
        # Non-interactive mode - use saved state if available, otherwise auto select
        print_status(f"Generating dump for {colored(root_dir, Colors.CYAN, bold=True)}", "info")
        
        # Check for existing state from previous interactive session
        existing_state = load_state(state_file)
        
        if existing_state.get('selected_files') and existing_state.get('root_dir') == root_dir:
            # Use saved state from previous interactive session
            print_status("Using file selection from previous interactive session", "info")
            selected_files = existing_state['selected_files']
            skipped_dirs = existing_state.get('skipped_dirs', set())
            selected_dirs = existing_state.get('selected_dirs', set())
            
            # Clean up missing files from state
            selected_files = {k: v for k, v in selected_files.items() 
                             if v and os.path.exists(os.path.join(root_dir, k))}
            
            if not selected_files:
                print_status("No valid files found in saved state", "warning")
                print_status("Run with --state-editor or --interactive flag to select files", "info")
                return
                
            print_status(f"Using {colored(str(len(selected_files)), Colors.GREEN)} previously selected files", "info")
        else:
            # No saved state - auto select files
            if is_first_run:
                print_status("First time dumping this project. Use --state-editor or --interactive for manual file selection", "info")
            
            if detected_type:
                print_status(f"Using {colored(detected_type, Colors.GREEN, bold=True)} defaults", "info")
            
            # Auto-select files
            selected_files = auto_select_files(
                root_dir, gitignore_patterns, os.path.basename(__file__), 
                output_file, include_patterns, max_file_size, state_file
            )
            
            if not selected_files:
                print_status("No files found matching criteria", "warning")
                print_status("Try running with --state-editor or --interactive flag to manually select files", "info")
                return
                
            print_status(f"Found {colored(str(len(selected_files)), Colors.GREEN)} files to dump", "info")
            skipped_dirs = set()
            selected_dirs = set()
        
        should_save = True
    
    if should_save:
        new_state = {
            'root_dir': root_dir,
            'selected_files': selected_files,
            'skipped_dirs': skipped_dirs,
            'selected_dirs': selected_dirs
        }
        
        save_state(state_file, new_state)
        dump_files(root_dir, selected_files, output_file, template_path)
        print_status(f"Files dumped to {output_file}", "success")
        
        # Create manifest if requested
        if args.manifest:
            manifest_file = create_dump_manifest(root_dir, selected_files, output_file, config)
            print_status(f"Created manifest: {manifest_file}", "success")
        
        # Export to additional formats
        if args.format:
            exported = export_to_formats(output_file, args.format)
            if exported:
                print_status(f"Exported to: {exported}", "success")
        
        # Copy to clipboard if requested
        if should_copy:
            try:
                with open(output_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                if copy_to_clipboard(content):
                    print_status("Output copied to clipboard!", "success")
                else:
                    print_status("Failed to copy to clipboard.", "error")
            except Exception as e:
                print_status(f"Error copying to clipboard: {e}", "error")
        
        # Check token limits from config
        if config.get('token_limit_warnings'):
            check_token_limits(output_file, config['token_limit_warnings'])
    else:
        print_status("Exiting without saving.", "warning")


if __name__ == "__main__":
    main()