import os
from typing import Dict, List
from .ui_utils import colored, print_header, print_status, Colors


def estimate_tokens(text: str, model: str = 'claude') -> int:
    """Estimate token count for different LLM models."""
    # Rough estimates based on average characters per token
    char_per_token = {
        'claude': 3.5,      # Claude models
        'gpt-4': 4.0,       # GPT-4
        'gpt-3.5': 4.0,     # GPT-3.5
        'gemini': 4.0,      # Google Gemini
        'llama': 3.8,       # Llama models
    }
    
    chars = len(text)
    cpt = char_per_token.get(model.lower(), 4.0)
    return int(chars / cpt)


def analyze_token_usage(root_dir: str, selected_files: Dict[str, bool]) -> Dict[str, Dict[str, int]]:
    """Analyze token usage per file for different models."""
    token_analysis = {}
    models = ['claude', 'gpt-4', 'gemini']
    
    for file, selected in selected_files.items():
        if not selected:
            continue
            
        try:
            full_path = os.path.join(root_dir, file)
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            token_analysis[file] = {
                'size': len(content),
                'tokens': {model: estimate_tokens(content, model) for model in models}
            }
        except:
            pass
            
    return token_analysis


def check_token_limits(output_file: str, limits: Dict[str, int]) -> None:
    """Check if output exceeds token limits and warn."""
    try:
        with open(output_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        for model, limit in limits.items():
            tokens = estimate_tokens(content, model)
            if tokens > limit:
                print_status(
                    f"Output exceeds {model} token limit ({tokens:,} > {limit:,})", 
                    "warning"
                )
    except:
        pass


def show_token_analysis(root_dir: str, selected_files: Dict[str, bool]) -> None:
    """Show detailed token analysis for selected files."""
    print_header("TOKEN ANALYSIS")
    print_status("Analyzing token usage...", "info")
    
    token_data = analyze_token_usage(root_dir, selected_files)
    
    if not token_data:
        print("No files to analyze.")
        return
    
    # Sort by Claude tokens descending
    sorted_files = sorted(token_data.items(), 
                         key=lambda x: x[1]['tokens']['claude'], 
                         reverse=True)
    
    print(f"\n{colored('Top 10 files by token count (Claude):', Colors.CYAN, bold=True)}")
    headers = f"{colored('File', Colors.CYAN):<50} {colored('Claude', Colors.BLUE):>10} {colored('GPT-4', Colors.GREEN):>10} {colored('Gemini', Colors.YELLOW):>10}"
    print(headers)
    print(colored("-" * 82, Colors.DIM))
    
    for file, data in sorted_files[:10]:
        file_display = file if len(file) <= 47 else '...' + file[-44:]
        print(f"{file_display:<50} "
              f"{data['tokens']['claude']:>10,} "
              f"{data['tokens']['gpt-4']:>10,} "
              f"{data['tokens']['gemini']:>10,}")
    
    # Total tokens
    total_tokens = {model: 0 for model in ['claude', 'gpt-4', 'gemini']}
    for data in token_data.values():
        for model in total_tokens:
            total_tokens[model] += data['tokens'][model]
    
    print(f"\n{colored('Total token counts:', Colors.CYAN, bold=True)}")
    for model, tokens in total_tokens.items():
        # Estimate cost (rough estimates)
        cost_per_1k = {'claude': 0.008, 'gpt-4': 0.03, 'gemini': 0.001}
        cost = (tokens / 1000) * cost_per_1k.get(model, 0)
        
        # Color based on model
        model_colors = {'claude': Colors.BLUE, 'gpt-4': Colors.GREEN, 'gemini': Colors.YELLOW}
        model_color = model_colors.get(model, Colors.DIM)
        
        print(f"  {colored(model.capitalize(), model_color, bold=True):>8}: {tokens:>12,} tokens (~${cost:.2f} est. input cost)")
    
    # Show token limit warnings
    print(f"\n{colored('Context window usage:', Colors.CYAN, bold=True)}")
    limits = {'claude': 200000, 'gpt-4': 128000, 'gemini': 1000000}
    for model, limit in limits.items():
        usage_pct = (total_tokens[model] / limit) * 100
        
        # Color based on usage
        if usage_pct < 80:
            status = colored("✓ OK", Colors.GREEN, bold=True)
            pct_color = Colors.GREEN
        elif usage_pct < 100:
            status = colored("⚠️  WARNING", Colors.YELLOW, bold=True)
            pct_color = Colors.YELLOW
        else:
            status = colored("❌ EXCEEDS", Colors.RED, bold=True)
            pct_color = Colors.RED
            
        model_colors = {'claude': Colors.BLUE, 'gpt-4': Colors.GREEN, 'gemini': Colors.YELLOW}
        model_color = model_colors.get(model, Colors.DIM)
        
        print(f"  {colored(model.capitalize(), model_color):>8}: {colored(f'{usage_pct:>6.1f}%', pct_color)} of {limit//1000}k limit {status}")