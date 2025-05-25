"""Additional creative features for the project dumper."""

import os
import json
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Set
from .file_utils import format_file_size
from .token_utils import estimate_tokens
from .ui_utils import print_status, colored, Colors, print_header


def create_dump_manifest(root_dir: str, selected_files: Dict[str, bool], 
                        output_file: str, config: Dict) -> str:
    """Create a manifest file with metadata about the dump."""
    manifest = {
        "timestamp": datetime.now().isoformat(),
        "project_path": os.path.abspath(root_dir),
        "project_type": config.get("project_type", "unknown"),
        "output_file": output_file,
        "statistics": {
            "total_files": len(selected_files),
            "selected_files": sum(1 for v in selected_files.values() if v),
            "total_size": 0,
            "token_estimates": {}
        },
        "files": []
    }
    
    # Calculate statistics
    for file_path, selected in selected_files.items():
        if selected:
            full_path = os.path.join(root_dir, file_path)
            try:
                size = os.path.getsize(full_path)
                manifest["statistics"]["total_size"] += size
                
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Calculate file hash
                file_hash = hashlib.md5(content.encode()).hexdigest()[:8]
                
                manifest["files"].append({
                    "path": file_path,
                    "size": size,
                    "hash": file_hash,
                    "tokens": {
                        "claude": estimate_tokens(content, "claude"),
                        "gpt-4": estimate_tokens(content, "gpt-4")
                    }
                })
            except:
                pass
    
    # Total token estimates
    total_content = ""
    for file_data in manifest["files"]:
        full_path = os.path.join(root_dir, file_data["path"])
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                total_content += f.read() + "\n"
        except:
            pass
    
    manifest["statistics"]["token_estimates"] = {
        "claude": estimate_tokens(total_content, "claude"),
        "gpt-4": estimate_tokens(total_content, "gpt-4"),
        "gemini": estimate_tokens(total_content, "gemini")
    }
    
    # Save manifest
    manifest_file = output_file.replace('.txt', '.manifest.json')
    with open(manifest_file, 'w') as f:
        json.dump(manifest, f, indent=2)
    
    return manifest_file


def generate_dump_summary(root_dir: str, selected_files: Dict[str, bool]) -> str:
    """Generate a human-readable summary of the dump."""
    summary_lines = []
    
    # File type breakdown
    extensions = {}
    total_size = 0
    
    for file_path, selected in selected_files.items():
        if selected:
            ext = os.path.splitext(file_path)[1] or 'no extension'
            extensions[ext] = extensions.get(ext, 0) + 1
            
            try:
                size = os.path.getsize(os.path.join(root_dir, file_path))
                total_size += size
            except:
                pass
    
    summary_lines.append("📊 DUMP SUMMARY")
    summary_lines.append("=" * 40)
    summary_lines.append(f"Total files: {sum(1 for v in selected_files.values() if v)}")
    summary_lines.append(f"Total size: {format_file_size(total_size)}")
    summary_lines.append("\nFile types:")
    
    # Sort by count
    sorted_exts = sorted(extensions.items(), key=lambda x: x[1], reverse=True)
    for ext, count in sorted_exts[:10]:
        summary_lines.append(f"  {ext:>15}: {count:>4} files")
    
    if len(sorted_exts) > 10:
        summary_lines.append(f"  ... and {len(sorted_exts) - 10} more types")
    
    return "\n".join(summary_lines)


def create_incremental_dump(root_dir: str, selected_files: Dict[str, bool], 
                           previous_manifest: Optional[str] = None) -> Set[str]:
    """Create an incremental dump by comparing with previous manifest."""
    if not previous_manifest or not os.path.exists(previous_manifest):
        # No previous manifest, include all selected files
        return set(f for f, s in selected_files.items() if s)
    
    # Load previous manifest
    with open(previous_manifest, 'r') as f:
        prev = json.load(f)
    
    # Build hash map of previous files
    prev_hashes = {f["path"]: f["hash"] for f in prev.get("files", [])}
    
    # Find changed files
    changed_files = set()
    
    for file_path, selected in selected_files.items():
        if not selected:
            continue
            
        full_path = os.path.join(root_dir, file_path)
        
        # New file
        if file_path not in prev_hashes:
            changed_files.add(file_path)
            continue
        
        # Check if file has changed
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
                current_hash = hashlib.md5(content.encode()).hexdigest()[:8]
                
            if current_hash != prev_hashes[file_path]:
                changed_files.add(file_path)
        except:
            # Error reading file, include it anyway
            changed_files.add(file_path)
    
    return changed_files


def suggest_related_files(root_dir: str, selected_files: Dict[str, bool]) -> List[str]:
    """Suggest related files that might be worth including."""
    suggestions = []
    selected_set = set(f for f, s in selected_files.items() if s)
    
    # Common patterns to look for
    patterns = {
        "test": ["test_", "_test", ".test.", "tests/"],
        "config": ["config", "settings", ".env", ".ini", ".yaml", ".yml"],
        "docs": ["README", "CHANGELOG", "LICENSE", "docs/", ".md"],
        "interface": [".proto", ".graphql", ".swagger", "api/"],
        "ci": [".github/", ".gitlab", "Jenkinsfile", ".travis"],
    }
    
    for category, keywords in patterns.items():
        category_files = []
        
        for file_path in selected_files:
            if file_path in selected_set:
                continue
                
            file_lower = file_path.lower()
            if any(kw in file_lower for kw in keywords):
                category_files.append(file_path)
        
        if category_files:
            suggestions.extend(category_files[:3])  # Max 3 per category
    
    return suggestions[:10]  # Return max 10 suggestions


def export_to_formats(output_file: str, format_type: str = "markdown") -> Optional[str]:
    """Export the dump to different formats."""
    if not os.path.exists(output_file):
        return None
    
    with open(output_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if format_type == "json":
        # Convert to JSON format
        lines = content.split('\n')
        json_data = {
            "content": content,
            "lines": len(lines),
            "size": len(content)
        }
        
        json_file = output_file.replace('.txt', '.json')
        with open(json_file, 'w') as f:
            json.dump(json_data, f, indent=2)
        
        return json_file
    
    elif format_type == "html":
        # Basic HTML conversion
        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>Project Dump</title>
    <style>
        body {{ font-family: monospace; white-space: pre-wrap; }}
        .file-header {{ background: #f0f0f0; padding: 5px; margin: 10px 0; }}
        pre {{ background: #f8f8f8; padding: 10px; overflow-x: auto; }}
    </style>
</head>
<body>
<pre>{content}</pre>
</body>
</html>"""
        
        html_file = output_file.replace('.txt', '.html')
        with open(html_file, 'w') as f:
            f.write(html_content)
        
        return html_file
    
    return None