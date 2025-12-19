import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.table import Table
import pandas as pd
from io import BytesIO
from datetime import datetime
import warnings
import re
import json
import os

# Import database functions
try:
    from rank_db import save_previous_rankings, load_previous_rankings
    USE_DATABASE = True
    print("✅ Using database for rank tracking")
except ImportError as e:
    print(f"⚠️ Database import failed ({e}), using JSON fallback")
    USE_DATABASE = False

def calculate_rank_changes(current_rankings, previous_rankings, session_name):
    """
    Calculate rank changes between current and previous rankings.
    
    Args:
        current_rankings: List of (symbol, rank) tuples for current scan
        previous_rankings: List of (symbol, rank) tuples for previous scan
        session_name: Session name for logging
    
    Returns:
        Dict of symbol -> rank_change (positive = moved up, negative = moved down)
    """
    if not previous_rankings:
        return {}
    
    # Create dictionaries for easy lookup
    current_dict = {symbol: rank for symbol, rank in current_rankings}
    previous_dict = {symbol: rank for symbol, rank in previous_rankings}
    
    rank_changes = {}
    
    # Calculate changes for symbols that exist in both scans
    for symbol in current_dict:
        if symbol in previous_dict:
            current_rank = current_dict[symbol]
            previous_rank = previous_dict[symbol]
            change = previous_rank - current_rank  # Positive = moved up
            if change != 0:
                rank_changes[symbol] = change
    
    return rank_changes

# File to store previous rankings (fallback)
RANKINGS_FILE = "previous_rankings.json"

def save_previous_rankings_fallback(rankings_data: dict):
    """
    Save current rankings to JSON file for comparison in next run (fallback).

    Args:
        rankings_data: Dictionary with session_name as key and list of (symbol, rank) tuples as value
    """
    try:
        with open(RANKINGS_FILE, 'w') as f:
            json.dump(rankings_data, f, indent=2)
    except Exception as e:
        print(f"Warning: Could not save rankings data: {e}")

def load_previous_rankings_fallback() -> dict:
    """
    Load previous rankings from JSON file (fallback).

    Returns:
        Dictionary with session_name as key and list of (symbol, rank) tuples as value
    """
    if not os.path.exists(RANKINGS_FILE):
        return {}

    try:
        with open(RANKINGS_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Warning: Could not load rankings data: {e}")
        return {}

def calculate_rank_changes(current_rankings: list, previous_rankings: list, session_name: str) -> dict:
    """
    Calculate rank changes between current and previous rankings.

    Args:
        current_rankings: List of (symbol, rank) tuples for current session
        previous_rankings: List of (symbol, rank) tuples for previous session
        session_name: Current session name

    Returns:
        Dictionary mapping symbol to rank change (positive = moved up, negative = moved down)
    """
    if not previous_rankings:
        return {}

    # Create symbol to rank mapping for both current and previous
    current_map = {symbol: rank for symbol, rank in current_rankings}
    previous_map = {symbol: rank for symbol, rank in previous_rankings}

    rank_changes = {}

    # Calculate changes for symbols that appear in both rankings
    for symbol in current_map:
        if symbol in previous_map:
            # Rank change = previous_rank - current_rank (positive means moved up)
            rank_changes[symbol] = previous_map[symbol] - current_map[symbol]

    return rank_changes

def generate_table_image(table_data: str, session_name: str = "UNKNOWN", weight: str = "0.0", last_updated: str = None, footer_text: str = None, interval_str: str = None, next_update: str = None) -> BytesIO:
    """
    Generate a table image from VWAP scanner data.

    Args:
        table_data: Raw table text data
        session_name: Current trading session name
        weight: Session weight value
        last_updated: Timestamp string
        footer_text: Optional footer text to display at bottom
        interval_str: Optional interval string (e.g., "10m", "30m", "1h") for title
        next_update: Optional next update time string

    Returns:
        BytesIO object containing the table image
    """
    # Set matplotlib backend for headless operation
    plt.switch_backend('Agg')

    # Parse the table data
    parsed_data = parse_table_data(table_data)

    if not parsed_data:
        # Return a simple error image if parsing fails
        return generate_error_image("No data available")

    # Extract current rankings for this session (list of (symbol, rank) tuples)
    current_rankings = [(row[1], int(row[0])) for row in parsed_data]  # (symbol, rank)

    # Parse interval from interval_str (e.g., "10m" -> 600, "1h" -> 3600)
    interval_seconds = 120  # Default
    if interval_str:
        interval_lower = interval_str.lower()
        if 'm' in interval_lower:
            interval_seconds = int(interval_lower.replace('m', '')) * 60
        elif 'h' in interval_lower:
            interval_seconds = int(float(interval_lower.replace('h', '')) * 3600)
        elif 's' in interval_lower:
            interval_seconds = int(interval_lower.replace('s', ''))

    # Load previous rankings and calculate changes
    if USE_DATABASE:
        previous_rankings = load_previous_rankings(session_name, interval_seconds)
    else:
        # Fallback to JSON (keep session-only for backward compatibility)
        previous_rankings_data = load_previous_rankings_fallback()
        previous_rankings = previous_rankings_data.get(session_name, [])

    # Calculate rank changes
    rank_changes = calculate_rank_changes(current_rankings, previous_rankings, session_name)

    # Save current rankings for next comparison
    if USE_DATABASE:
        save_previous_rankings(session_name, current_rankings, interval_seconds)
    else:
        # Fallback to JSON
        previous_rankings_data[session_name] = current_rankings
        save_previous_rankings_fallback(previous_rankings_data)

    # Create figure with custom styling
    fig, ax = plt.subplots(figsize=(16, 10), facecolor='#ffffff')
    ax.set_facecolor('#ffffff')

    # Hide axes
    ax.axis('off')

    # Create table
    table = Table(ax, bbox=[0.05, 0.10, 0.9, 0.78])

    # Set table style
    table.auto_set_font_size(False)
    table.set_fontsize(10)

    # Define colors - Light theme
    header_color = '#2563eb'  # Blue header
    alt_row_colors = ['#f8fafc', '#f1f5f9']  # Alternating row colors (even rows darker)
    text_color = '#1e293b'
    border_color = '#e2e8f0'

    # Column headers
    headers = ['Rank', 'Symbol', 'Signal', 'Score', 'Price', 'VWAP', 'Volume', 'RSI', 'MACD', 'Stoch']

    # Add headers
    for j, header in enumerate(headers):
        cell = table.add_cell(0, j, width=1/len(headers), height=0.08, text=header,
                             loc='center', facecolor=header_color, edgecolor=border_color)
        cell.get_text().set_color(text_color)
        cell.get_text().set_fontweight('bold')
        cell.get_text().set_fontsize(11)

    # Add data rows
    for i, row in enumerate(parsed_data[:15], 1):  # Limit to top 15 for readability
        row_color = alt_row_colors[i % 2]

        for j, (header, value) in enumerate(zip(headers, row)):
            # Determine cell color based on signal
            cell_color = row_color
            text_color_for_cell = text_color  # Initialize default text color
            is_bold = False  # Initialize bold flag
            
            if header == 'Signal':
                # Keep default cell color, but color the text
                if 'STRONG BUY' in str(value):
                    text_color_for_cell = '#0f5132'  # Very dark green for strong buy
                    is_bold = True
                elif 'BUY' in str(value):
                    text_color_for_cell = '#22c55e'  # Green for buy
                    is_bold = True
                elif 'STRONG SELL' in str(value):
                    text_color_for_cell = '#b91c1c'  # Very dark red for strong sell
                    is_bold = True
                elif 'SELL' in str(value):
                    text_color_for_cell = '#ef4444'  # Red for sell
                    is_bold = True

            # Special handling for Rank column to add change indicators
            display_text = str(value)
            if header == 'Rank':
                text_color_for_cell = text_color  # Default text color for rank column
                symbol = row[1]  # Symbol is in the second column
                if symbol in rank_changes:
                    change = rank_changes[symbol]
                    if change > 0:
                        # Moved up - green text
                        display_text = f"{value} (▲{change})"
                        text_color_for_cell = '#16a34a'  # Dark green text
                    elif change < 0:
                        # Moved down - red text
                        display_text = f"{value} (▼{abs(change)})"
                        text_color_for_cell = '#dc2626'  # Dark red text

            cell = table.add_cell(i, j, width=1/len(headers), height=0.06, text=display_text,
                                 loc='center', facecolor=cell_color, edgecolor=border_color)
            cell.get_text().set_color(text_color_for_cell)
            if is_bold:
                cell.get_text().set_fontweight('bold')
            cell.get_text().set_fontsize(9)

    # Add table to axes
    ax.add_table(table)

    # Add title with optional interval/timeframe
    if interval_str:
        title_text = f"BYBIT FUTURES VWAP SCANNER - UPDATED EVERY {interval_str.upper()}"
    else:
        title_text = f"BYBIT FUTURES VWAP SCANNER"
    ax.text(0.5, 0.95, title_text, transform=ax.transAxes,
            fontsize=16, fontweight='bold', color='#1e293b',
            ha='center', va='top')

    # Add session info and timestamp on same line
    if last_updated and next_update:
        session_text = f"Current Session: {session_name} | Weight: {weight} | Last Updated: {last_updated} | Next Update: {next_update}"
    elif last_updated:
        session_text = f"Current Session: {session_name} | Weight: {weight} | Last Updated: {last_updated}"
    else:
        session_text = f"Current Session: {session_name} | Weight: {weight}"
    ax.text(0.5, 0.92, session_text, transform=ax.transAxes,
            fontsize=11, color='#64748b',
            ha='center', va='top')

    # Add configurable footer text if provided
    if footer_text:
        ax.text(0.5, 0.05, footer_text, transform=ax.transAxes,
                fontsize=9, color='#94a3b8',
                ha='center', va='bottom')

    # Adjust layout
    plt.tight_layout()

    # Save to BytesIO
    buf = BytesIO()
    fig.savefig(buf, format='png', dpi=150, facecolor='#ffffff',
                edgecolor='none', bbox_inches='tight')
    buf.seek(0)

    # Close figure to free memory
    plt.close(fig)

    return buf

def parse_table_data(table_data: str) -> list:
    """
    Parse the raw table text data into structured format.

    Args:
        table_data: Raw table text

    Returns:
        List of tuples containing parsed row data
    """
    if not isinstance(table_data, str):
        return []

    lines = table_data.split('\n')
    parsed_rows = []

    for line in lines:
        line = line.strip()
        if not line or line.startswith('=') or line.startswith('-') or 'RANK' in line.upper() or 'BYBIT' in line.upper() or 'Session' in line.upper() or 'SYMBOL' in line.upper() or 'SIGNAL' in line.upper():
            continue
            continue

        parts = line.split()
        if len(parts) < 10:
            continue

        try:
            # Extract data similar to the original parsing logic
            rank = parts[0]
            
            # Validate rank is numeric (skip emoji/warning lines)
            if not rank.isdigit():
                continue

            # Find symbol (usually second element)
            symbol = parts[1]

            # Find signal (contains text before numeric data)
            signal_parts = []
            score_idx = -1
            for j, part in enumerate(parts[2:], 2):
                if part.replace('.', '').replace('-', '').isdigit():
                    score_idx = j
                    break
                signal_parts.append(part)

            # Clean signal text
            signal = ' '.join(signal_parts).strip()
            signal = re.sub(r'[🔴🟢⚪🔥]\s*', '', signal).strip()

            # Extract numeric data
            score = parts[score_idx] if score_idx > 0 else "N/A"
            price = parts[score_idx + 1] if score_idx + 1 < len(parts) else "N/A"
            vwap = parts[score_idx + 2] if score_idx + 2 < len(parts) else "N/A"
            volume = parts[score_idx + 3] if score_idx + 3 < len(parts) else "N/A"
            rsi = parts[score_idx + 4] if score_idx + 4 < len(parts) else "N/A"
            macd = parts[score_idx + 5] if score_idx + 5 < len(parts) else "N/A"
            stoch = parts[score_idx + 6] if score_idx + 6 < len(parts) else "N/A"

            parsed_rows.append((rank, symbol, signal, score, price, vwap, volume, rsi, macd, stoch))

        except (IndexError, ValueError):
            continue

    return parsed_rows

def generate_error_image(error_message: str) -> BytesIO:
    """
    Generate a simple error image when data parsing fails.

    Args:
        error_message: Error message to display

    Returns:
        BytesIO object containing the error image
    """
    plt.switch_backend('Agg')

    fig, ax = plt.subplots(figsize=(12, 6), facecolor='#ffffff')
    ax.set_facecolor('#ffffff')
    ax.axis('off')

    # Add error message
    ax.text(0.5, 0.6, "Error", transform=ax.transAxes,
            fontsize=24, color='#dc2626', ha='center', va='center', fontweight='bold')

    ax.text(0.5, 0.4, error_message, transform=ax.transAxes,
            fontsize=14, color='#64748b', ha='center', va='center')

    # Add timestamp
    timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
    ax.text(0.5, 0.1, f"Generated: {timestamp}", transform=ax.transAxes,
            fontsize=10, color='#94a3b8', ha='center', va='center')

    buf = BytesIO()
    fig.savefig(buf, format='png', dpi=150, facecolor='#ffffff', edgecolor='none')
    buf.seek(0)

    plt.close(fig)
    return buf