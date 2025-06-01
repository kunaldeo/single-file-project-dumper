# Project Dumper for LLM Prompts

A powerful tool for creating comprehensive, LLM-optimized documentation from your codebase. Intelligently bundles multiple source files into a single output with token counting, smart project detection, and interactive selection.

## Features

### 🚀 Core Features
- **Interactive File Selection**: Navigate and select files/directories with a rich colored UI
- **Smart Project Detection**: Automatically detects project type (Python, JavaScript, TypeScript, Rust, Go, Java, C++, Ruby, PHP, Swift, Kotlin, Scala) and applies intelligent defaults
- **Token Analysis**: Real-time token counting for Claude, GPT-4, and Gemini models with cost estimates
- **Multiple Ignore Files**: Respects .gitignore, .dockerignore, .npmignore, and custom patterns
- **State Preservation**: Remembers selections between runs with project-specific configurations

### 🎯 Advanced Features
- **Configuration System**: Project-specific `.claude-dump` files and global preferences
- **Template Support**: Customizable output formats using Handlebars templates
- **Export Formats**: Output to Markdown (default), JSON, or HTML
- **Manifest Generation**: Track dump metadata for incremental updates
- **Pattern-Based Selection**: Bulk select/deselect files using glob patterns
- **Related File Suggestions**: Intelligently suggests related files based on imports
- **Preview Mode**: Review output before saving with token usage breakdown

## Installation

Clone the repository and install using pipx:

```bash
git clone https://github.com/kunaldeo/single-file-project-dumper
cd single-file-project-dumper
pipx install . --force
```

## Usage

### Basic Usage
```bash
# Run in current directory
project-dumper

# Run in specific directory
project-dumper /path/to/project
```

### Configuration
```bash
# Initialize project configuration with smart defaults
project-dumper --init

# This creates a .claude-dump file with project-specific settings
```

### Command-Line Options

#### Quick Reference (Short Options)
```bash
project-dumper -s              # Open state editor (visual file selector)
project-dumper -e              # Edit mode (load previous selections)
project-dumper -i              # Interactive mode (state editor + advanced options)
project-dumper -o dump.txt     # Set output file
project-dumper -f json         # Set format (markdown/json/html)
project-dumper -c              # Copy output to clipboard
project-dumper -r              # Reset saved selections
```

#### Complete Options List

**File Selection Modes**
```bash
-s, --state-editor     # Visual tree-based file selector with keyboard navigation
-e, --edit            # Open state editor with previously saved selections
-i, --interactive     # Combine visual selection with advanced management options
```

**Output Options**
```bash
-o, --output-file FILE     # Specify output filename (default: project_code.txt)
-f, --format FORMAT        # Export format: markdown, json, or html
-t, --template FILE        # Use custom Handlebars template for output
-c, --copy                 # Copy output to clipboard after generation
```

**Configuration Options**
```bash
--init                     # Initialize .claude-dump config with smart defaults
--state-file FILE          # Custom state file location (default: .file_dumper_state.json)
--manifest                 # Generate manifest file with dump metadata
-r, --reset               # Clear all saved file selections and start fresh
```

**Filtering Options**
```bash
--include PATTERN          # Include files matching pattern (can use multiple times)
--exclude PATTERN          # Exclude files matching pattern (can use multiple times)
-m, --max-file-size KB    # Maximum file size in kilobytes (default: 1000)
```

#### Common Usage Examples
```bash
# Quick visual file selection
project-dumper -s

# Edit previous selection and copy to clipboard
project-dumper -e -c

# Generate JSON output with custom filename
project-dumper -f json -o api-docs.json

# Reset and start fresh selection
project-dumper -r -s

# Include only Python files under 500KB
project-dumper --include "*.py" -m 500
```

## File Selection Modes

Project Dumper offers three ways to select files:

### 1. Automatic Mode (Default)
```bash
project-dumper
```
Automatically selects files based on smart project detection and saved state. Only includes source code files (Python, JavaScript, TypeScript, Rust, Go, Java, C++, Ruby, PHP, Swift, Kotlin, Scala, and configuration files).

### 2. State Editor (Visual Tree Mode)
```bash
project-dumper --state-editor
```
Visual tree-based file browser with:
- **Hierarchical file tree** display showing only source files
- **Real-time navigation** with arrow keys or vim keys (j/k)
- **Directory expansion/collapse** with Enter
- **Visual selection indicators** with checkmarks and colors
- **Bulk directory selection** - selecting a directory selects all source files within
- **Dark terminal optimized** color scheme
- **Source file filtering** - only shows relevant code files

#### State Editor Controls
- `↑/↓` or `j/k`: Navigate up/down
- `Space`: Select/deselect current file or directory
- `Enter`: Expand/collapse directories
- `q`: Save selections and generate dump
- `Ctrl+C`: Cancel (exit without saving)

### 3. Interactive Mode
```bash
project-dumper --interactive
```
Combines visual file selection with advanced management options:
- **State editor** for initial file selection
- **Interactive edit mode** with pattern-based operations, token analysis, preview, and export options

#### Edit Mode
```bash
project-dumper --edit
```
Opens the state editor with previously saved file selections pre-loaded for quick editing.

## Configuration

### Project Configuration (`.claude-dump`)
```json
{
  "include_patterns": ["src/**/*.py", "tests/**/*.py"],
  "exclude_patterns": ["**/__pycache__/**", "**/node_modules/**"],
  "max_file_size": 1048576,
  "max_total_size": 10485760,
  "output_format": "markdown",
  "template_file": null
}
```

### Global Preferences
Stored in `~/.config/project-dumper/preferences.json`:
- Recent projects tracking
- Default output format
- Preferred token model
- UI preferences

## Token Counting

The tool provides real-time token analysis for:
- **Claude**: Most accurate counting using official tokenizer
- **GPT-4**: OpenAI tiktoken-based counting
- **Gemini**: Estimated token count

Includes context window warnings:
- ⚠️  80% usage: Warning
- ❌ 100% usage: Error (output will be truncated)

## Output Formats

### Markdown (Default)
Optimized for LLM prompts with:
- Project structure tree
- Formatted code blocks with syntax highlighting
- Clear file demarcation

### JSON
Structured data format with:
- File metadata
- Token counts per file
- Project statistics

### HTML
Interactive HTML view with:
- Collapsible file sections
- Syntax highlighting
- Token usage visualization

## Smart Project Detection

Automatically detects and optimizes for:
- **Python**: Includes .py files, excludes __pycache__, .pyc
- **JavaScript/TypeScript**: Includes .js/.ts, excludes node_modules, dist
- **Rust**: Includes .rs, excludes target directory
- **Go**: Includes .go, excludes vendor
- And more...

## Best Practices

1. **Initialize project config**: Run `project-dumper --init` for optimal defaults
2. **Choose the right selection mode**:
   - Use **automatic mode** for quick, repeated dumps with smart defaults
   - Use **state editor** for visual file exploration and simple selection
   - Use **interactive mode** for advanced operations (patterns, previews, token analysis)
   - Use **edit mode** to quickly modify previously saved selections
3. **Review token usage**: Check token counts before sending to LLMs
4. **Use manifests**: Generate manifests for tracking changes over time
5. **Leverage patterns**: Use glob patterns for efficient bulk selection
6. **Preview first**: Always preview output for large projects

## Notes
- Binary files are automatically skipped
- UTF-8 encoding is assumed for all text files
- Extremely large files (>1MB by default) are excluded with warning
- Token counts are estimates and may vary slightly from LLM APIs