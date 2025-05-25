import os
import fnmatch
import re
import subprocess
import platform
from typing import Dict, Set, Tuple, List
from .file_utils import format_file_size
from .token_utils import estimate_tokens, show_token_analysis
from .ui_utils import (
    colored, print_header, print_status, format_size_colored,
    prompt_yes_no, Colors
)
from .features import suggest_related_files, generate_dump_summary


def interactive_edit_mode(root_dir: str, selected_files: Dict[str, bool], 
                         skipped_dirs: Set[str], selected_dirs: Set[str],
                         gitignore_patterns: List[str], output_file: str) -> Tuple[Dict[str, bool], bool]:
    """Interactive mode to edit file selections after initial scan."""
    while True:
        print_header("INTERACTIVE EDIT MODE")
        
        # Count selected files
        selected_count = sum(1 for v in selected_files.values() if v)
        total_count = len(selected_files)
        
        # Color the count based on selection status
        if selected_count == 0:
            count_color = Colors.RED
        elif selected_count == total_count:
            count_color = Colors.YELLOW
        else:
            count_color = Colors.GREEN
            
        print(f"\nCurrently selected: {colored(str(selected_count), count_color, bold=True)} / {total_count} files")
        
        print(f"\n{colored('Options:', Colors.CYAN, bold=True)}")
        print(f"  {colored('1', Colors.YELLOW)}. View/edit selected files")
        print(f"  {colored('2', Colors.YELLOW)}. View/edit excluded files")
        print(f"  {colored('3', Colors.YELLOW)}. Select all files matching pattern")
        print(f"  {colored('4', Colors.YELLOW)}. Deselect all files matching pattern")
        print(f"  {colored('5', Colors.YELLOW)}. Preview output")
        print(f"  {colored('6', Colors.GREEN, bold=True)}. Save and dump")
        print(f"  {colored('7', Colors.RED)}. Exit without saving")
        print(f"  {colored('8', Colors.YELLOW)}. Show file size summary")
        print(f"  {colored('9', Colors.YELLOW)}. Show token analysis")
        print(f"  {colored('10', Colors.CYAN)}. Show suggested files")
        print(f"  {colored('11', Colors.CYAN)}. Quick summary")
        
        choice = input(f"\n{colored('→', Colors.GREEN, bold=True)} Enter your choice (1-11): ").strip()
        
        if choice == '1':
            # View/edit selected files
            selected_list = sorted([f for f, v in selected_files.items() if v])
            if not selected_list:
                print("\nNo files currently selected.")
                continue
                
            print("\nSelected files:")
            for i, file in enumerate(selected_list, 1):
                print(f"  {i}. {file}")
            
            file_num = input(f"\n{colored('?', Colors.CYAN, bold=True)} Enter file number to deselect (or 'q' to go back): ").strip()
            if file_num != 'q' and file_num.isdigit():
                idx = int(file_num) - 1
                if 0 <= idx < len(selected_list):
                    selected_files[selected_list[idx]] = False
                    print_status(f"Deselected: {selected_list[idx]}", "success")
                    
        elif choice == '2':
            # View/edit excluded files
            excluded_list = sorted([f for f, v in selected_files.items() if not v])
            if not excluded_list:
                print("\nNo files currently excluded.")
                continue
                
            print("\nExcluded files:")
            for i, file in enumerate(excluded_list, 1):
                print(f"  {i}. {file}")
            
            file_num = input(f"\n{colored('?', Colors.CYAN, bold=True)} Enter file number to select (or 'q' to go back): ").strip()
            if file_num != 'q' and file_num.isdigit():
                idx = int(file_num) - 1
                if 0 <= idx < len(excluded_list):
                    selected_files[excluded_list[idx]] = True
                    print_status(f"Selected: {excluded_list[idx]}", "success")
                    
        elif choice == '3':
            # Select by pattern
            pattern = input("\nEnter pattern to select (e.g., *.py, test_*, **/models/*): ").strip()
            if pattern:
                count = 0
                for file in selected_files:
                    if fnmatch.fnmatch(file, pattern) or re.search(pattern, file):
                        if not selected_files[file]:
                            selected_files[file] = True
                            count += 1
                print_status(f"Selected {count} files matching '{pattern}'", "success")
                
        elif choice == '4':
            # Deselect by pattern
            pattern = input("\nEnter pattern to deselect (e.g., *.pyc, __pycache__/*): ").strip()
            if pattern:
                count = 0
                for file in selected_files:
                    if fnmatch.fnmatch(file, pattern) or re.search(pattern, file):
                        if selected_files[file]:
                            selected_files[file] = False
                            count += 1
                print_status(f"Deselected {count} files matching '{pattern}'", "success")
                
        elif choice == '5':
            # Preview output
            preview_output(root_dir, selected_files, output_file)
            
        elif choice == '6':
            # Save and dump
            return selected_files, True
            
        elif choice == '7':
            # Exit without saving
            if prompt_yes_no("Are you sure you want to exit without saving?", default=False):
                return selected_files, False
                
        elif choice == '8':
            # Show file size summary
            show_file_size_summary(root_dir, selected_files)
        
        elif choice == '9':
            # Token analysis
            show_token_analysis(root_dir, selected_files)
            
        elif choice == '10':
            # Show suggested files
            show_file_suggestions(root_dir, selected_files)
            
        elif choice == '11':
            # Quick summary
            summary = generate_dump_summary(root_dir, selected_files)
            print(f"\n{colored(summary, Colors.CYAN)}")
            
        else:
            print_status("Invalid choice. Please try again.", "warning")


def preview_output(root_dir: str, selected_files: Dict[str, bool], output_file: str) -> None:
    """Preview the output that would be generated."""
    selected_list = sorted([f for f, v in selected_files.items() if v])
    
    print_header("OUTPUT PREVIEW")
    print(f"\n{colored('Output file:', Colors.CYAN)} {output_file}")
    print(f"{colored('Selected files:', Colors.CYAN)} {len(selected_list)}")
    
    # Calculate total size
    total_size = 0
    for file in selected_list:
        try:
            total_size += os.path.getsize(os.path.join(root_dir, file))
        except:
            pass
    
    print(f"{colored('Total size:', Colors.CYAN)} {format_size_colored(total_size)}")
    
    # Estimate tokens for different models
    print(f"\n{colored('Estimated token counts:', Colors.CYAN, bold=True)}")
    total_text = ""
    for file in selected_list:
        try:
            with open(os.path.join(root_dir, file), 'r', encoding='utf-8') as f:
                total_text += f.read() + "\n"
        except:
            pass
    
    for model in ['claude', 'gpt-4', 'gemini']:
        tokens = estimate_tokens(total_text, model)
        print(f"  {model.capitalize():>8}: ~{tokens:,} tokens")
    
    print("\nFirst 10 files:")
    for file in selected_list[:10]:
        print(f"  - {file}")
    
    if len(selected_list) > 10:
        print(f"  ... and {len(selected_list) - 10} more files")


def show_file_size_summary(root_dir: str, selected_files: Dict[str, bool]) -> None:
    """Show summary of file sizes."""
    sizes = []
    for file, selected in selected_files.items():
        try:
            size = os.path.getsize(os.path.join(root_dir, file))
            sizes.append((file, size, selected))
        except:
            pass
    
    # Sort by size descending
    sizes.sort(key=lambda x: x[1], reverse=True)
    
    print_header("FILE SIZE SUMMARY")
    
    print(f"\n{colored('Top 10 largest files:', Colors.CYAN, bold=True)}")
    for file, size, selected in sizes[:10]:
        if selected:
            status = colored("[SELECTED]", Colors.GREEN)
        else:
            status = colored("[EXCLUDED]", Colors.RED)
        print(f"  {format_size_colored(size):>10} {status:>11} {file}")
    
    # Summary stats
    selected_size = sum(size for _, size, selected in sizes if selected)
    total_size = sum(size for _, size, _ in sizes)
    
    print(f"\n{colored('Total size of selected files:', Colors.CYAN)} {format_size_colored(selected_size)}")
    print(f"{colored('Total size of all files:', Colors.CYAN)} {format_size_colored(total_size)}")


def show_file_suggestions(root_dir: str, selected_files: Dict[str, bool]) -> None:
    """Show suggested files that might be worth including."""
    print_header("FILE SUGGESTIONS")
    
    suggestions = suggest_related_files(root_dir, selected_files)
    
    if not suggestions:
        print_status("No additional files to suggest.", "info")
        return
    
    print(f"\n{colored('Found related files you might want to include:', Colors.CYAN, bold=True)}\n")
    
    for i, file in enumerate(suggestions, 1):
        try:
            size = os.path.getsize(os.path.join(root_dir, file))
            size_str = format_size_colored(size)
            print(f"  {colored(str(i), Colors.YELLOW)}. {file} ({size_str})")
        except:
            print(f"  {colored(str(i), Colors.YELLOW)}. {file}")
    
    add_all = prompt_yes_no("\nAdd all suggested files?", default=False)
    if add_all:
        count = 0
        for file in suggestions:
            if file in selected_files and not selected_files[file]:
                selected_files[file] = True
                count += 1
        print_status(f"Added {count} suggested files.", "success")
    else:
        # Ask for individual files
        while True:
            choice = input(f"\n{colored('?', Colors.CYAN, bold=True)} Enter file number to add (or 'q' to finish): ").strip()
            if choice == 'q':
                break
            if choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(suggestions):
                    file = suggestions[idx]
                    if file in selected_files:
                        selected_files[file] = True
                        print_status(f"Added: {file}", "success")


def copy_to_clipboard(text: str) -> bool:
    """Copy text to clipboard. Returns True if successful."""
    try:
        if platform.system() == 'Darwin':  # macOS
            subprocess.run(['pbcopy'], input=text.encode('utf-8'), check=True)
        elif platform.system() == 'Linux':
            # Try xclip first, then xsel
            try:
                subprocess.run(['xclip', '-selection', 'clipboard'], 
                             input=text.encode('utf-8'), check=True)
            except:
                subprocess.run(['xsel', '--clipboard', '--input'], 
                             input=text.encode('utf-8'), check=True)
        elif platform.system() == 'Windows':
            subprocess.run(['clip'], input=text.encode('utf-8'), check=True, shell=True)
        return True
    except:
        return False