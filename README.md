# File Dumper for LLM Prompts

## Purpose
The File Dumper script is designed to create a single text file containing the contents of multiple selected files from a directory structure. This compiled file is particularly useful for creating prompts for Large Language Models (LLMs) that require context from multiple source files.

## Installation
```bash
pipx install project-dumper
```

## Features
- **Selective File Inclusion**: Users can choose which directories and files to include in the final output.
- **.gitignore Support**: The script respects .gitignore patterns, automatically excluding files that match these patterns.
- **State Preservation**: Selections are saved in a state file, allowing users to reuse or modify previous choices in subsequent runs.
- **Directory-Level Selection**: Users can choose to include or exclude entire directories, streamlining the selection process for large projects.
- **Formatted Output**: The dumped file follows a specific format optimized for LLM prompts, with a clear project structure and formatted code blocks.

## Usage
```bash
# Run in current directory
project-dumper

# Run in specific directory
project-dumper /path/to/project
```

### Options
```bash
# Specify output file (default: project_code.txt)
project-dumper --output-file output.txt

# Specify state file (default: .file_dumper_state.json)
project-dumper --state-file .my-state.json
```

## Output Format
The script generates a markdown file with:
- Project path
- Directory structure tree
- Selected file contents with proper code formatting

## Notes
- Designed for text files - binary files will be skipped
- UTF-8 encoding is assumed for all text files
- Selections are saved between runs
- Respects .gitignore patterns by default