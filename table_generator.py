import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.table import Table
import pandas as pd
from io import BytesIO
from datetime import datetime
import warnings
import re

def generate_table_image(table_data: str, session_name: str = "UNKNOWN", weight: str = "0.0", last_updated: str = None) -> BytesIO:
    """
    Generate a table image from VWAP scanner data.

    Args:
        table_data: Raw table text data
        session_name: Current trading session name
        weight: Session weight value
        last_updated: Timestamp string

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

    # Create figure with custom styling
    fig, ax = plt.subplots(figsize=(16, 10), facecolor='#ffffff')
    ax.set_facecolor('#ffffff')

    # Hide axes
    ax.axis('off')

    # Create table
    table = Table(ax, bbox=[0.05, 0.12, 0.9, 0.78])

    # Set table style
    table.auto_set_font_size(False)
    table.set_fontsize(10)

    # Define colors - Light theme
    header_color = '#2563eb'  # Blue header
    alt_row_colors = ['#f8fafc', '#ffffff']  # Alternating light row colors
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
            if header == 'Signal':
                if 'STRONG BUY' in str(value):
                    cell_color = '#dcfce7'  # Light green for strong buy
                elif 'BUY' in str(value):
                    cell_color = '#ecfdf5'  # Very light green for buy
                elif 'STRONG SELL' in str(value):
                    cell_color = '#fef2f2'  # Light red for strong sell
                elif 'SELL' in str(value):
                    cell_color = '#fef2f2'  # Light red for sell

            cell = table.add_cell(i, j, width=1/len(headers), height=0.06, text=str(value),
                                 loc='center', facecolor=cell_color, edgecolor=border_color)
            cell.get_text().set_color(text_color)
            cell.get_text().set_fontsize(9)

    # Add table to axes
    ax.add_table(table)

    # Add title
    title_text = f"BYBIT FUTURES VWAP SCANNER"
    ax.text(0.5, 0.95, title_text, transform=ax.transAxes,
            fontsize=16, fontweight='bold', color='#1e293b',
            ha='center', va='top')

    # Add session info and timestamp on same line
    if last_updated:
        session_text = f"Session: {session_name} | Weight: {weight} | Last Updated: {last_updated}"
    else:
        session_text = f"Session: {session_name} | Weight: {weight}"
    ax.text(0.5, 0.92, session_text, transform=ax.transAxes,
            fontsize=11, color='#64748b',
            ha='center', va='top')

    # Add refresh info
    refresh_text = "Auto-updates every 30 seconds | Use !stop to end scanning"
    ax.text(0.5, 0.05, refresh_text, transform=ax.transAxes,
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
        if not line or line.startswith('=') or line.startswith('-') or 'RANK' in line or 'BYBIT' in line or 'Session' in line:
            continue

        parts = line.split()
        if len(parts) < 10:
            continue

        try:
            # Extract data similar to the original parsing logic
            rank = parts[0]

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