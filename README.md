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
```bash
pipx install project-dumper
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
```bash
# Output options
project-dumper --output-file output.txt     # Specify output file (default: project_code.txt)
project-dumper --format json                # Export format: markdown, json, html
project-dumper --template custom.hbs        # Use custom Handlebars template

# Configuration options
project-dumper --state-file .my-state.json  # Custom state file location
project-dumper --manifest manifest.json     # Generate manifest with metadata

# Initialize configuration
project-dumper --init                       # Create .claude-dump with smart defaults
```

## Interactive Mode Features

When you run `project-dumper`, you'll enter an interactive mode with:

- **Color-coded file tree** with size information
- **Token usage visualization** with model-specific counts
- **Quick summary** showing total files, size, and token usage
- **Pattern-based operations** for bulk selection
- **Related file detection** for comprehensive context
- **Preview before export** with per-file token breakdown

### Interactive Commands
- `Space`: Toggle file/directory selection
- `Enter`: Confirm and generate output
- `q`: Quit without saving
- `p`: Preview output
- `s`: Quick summary view

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
2. **Review token usage**: Check token counts before sending to LLMs
3. **Use manifests**: Generate manifests for tracking changes over time
4. **Leverage patterns**: Use glob patterns for efficient bulk selection
5. **Preview first**: Always preview output for large projects

## Notes
- Binary files are automatically skipped
- UTF-8 encoding is assumed for all text files
- Extremely large files (>1MB by default) are excluded with warning
- Token counts are estimates and may vary slightly from LLM APIs