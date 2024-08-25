# File Dumper for LLM Prompts

## Purpose

The File Dumper script is designed to create a single text file containing the contents of multiple selected files from a directory structure. This compiled file is particularly useful for creating prompts for Large Language Models (LLMs) that require context from multiple source files.

## Features

- **Selective File Inclusion**: Users can choose which directories and files to include in the final output.
- **.gitignore Support**: The script respects .gitignore patterns, automatically excluding files that match these patterns.
- **State Preservation**: Selections are saved in a state file, allowing users to reuse or modify previous choices in subsequent runs.
- **Directory-Level Selection**: Users can choose to include or exclude entire directories, streamlining the selection process for large projects.
- **Formatted Output**: The dumped file follows a specific format, prefixing each file's content with its path for easy reference.

## How to Use

1. **Setup**:
   - Ensure you have Python installed on your system.
   - Save the `file_dumper.py` script in a location of your choice.

2. **Running the Script**:
   - Open a terminal or command prompt.
   - Navigate to the directory where you want the output and state files to be created.
   - Run the script using the command: `python path/to/file_dumper.py`

3. **Script Workflow**:
   - You'll be prompted to enter or confirm the root directory of your project.
   - The script will then walk through the directory structure:
     - For each directory, you'll be asked if you want to include files from it.
     - If you choose to include a directory, you'll be prompted for each file within it.
   - You can choose to use existing selections if you've run the script before.

4. **Output**:
   - The script creates a file named `dumped_files.txt` in the current working directory.
   - This file contains the contents of all selected files, each prefixed with its relative path.

5. **State File**:
   - A `.file_dumper_state.json` file is created in the current working directory.
   - This file stores your selections, allowing you to reuse or modify them in future runs.

## Tips for Use

- Run the script from the directory where you want the output file to be created.
- The first run might take longer as you select files, but subsequent runs can be faster if you reuse selections.
- You can always choose to make new selections, even if you have existing ones saved.
- The script respects .gitignore files, which is useful for automatically excluding build artifacts or dependencies.

## Note

This script is designed for text files. Binary files or files with non-UTF-8 encoding may not be processed correctly.
