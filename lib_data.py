"""
lib_data.py — Data loading & parsing layer for the Quantum Hardware Web Dashboard.

This module is completely self-contained and uses only RELATIVE paths
(relative to this file's own folder). It never reads or writes anything
outside the `web_dashboard_version/` folder, and never touches the
original project's Excel files in `Final/` or `Anat/`.
"""

import os
import re
from pathlib import Path

import numpy as np
import pandas as pd

# ─── Paths (all relative to this file — no machine-specific paths) ───────────

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
PENDING_DIR = BASE_DIR / "pending_review"
PROCESSED_DIR = PENDING_DIR / "processed"
UPLOAD_DIR = BASE_DIR / "uploaded_pdfs"
INSTRUCTIONS_PATH = BASE_DIR / "quantum_eval_instructions.md"

PLATFORMS = ['Superconducting Circuits', 'Trapped Ions', 'Neutral Atoms', 'Photonics']
FILE_MAP = {p: DATA_DIR / f"{p}.xlsx" for p in PLATFORMS}

PLATFORM_COLORS = {
    'Superconducting Circuits': '#2196F3',
    'Trapped Ions': '#E53935',
    'Neutral Atoms': '#43A047',
    'Photonics': '#8E24AA',
}
PLATFORM_SHORT = {
    'Superconducting Circuits': 'SC Qubits',
    'Trapped Ions': 'Trapped Ions',
    'Neutral Atoms': 'Neutral Atoms',
    'Photonics': 'Photonics',
}

PARAM_GROUPS = {
    'Coherence Times': {
        'T₁': ('µs', True),
        'T₂* (Ramsey)': ('µs', True),
        'T₂ (Hahn Echo)': ('µs', True),
        'T₂ (CPMG)': ('µs', True),
    },
    'Gate Fidelities': {
        'Single-Qubit Gate Fidelity': ('%', True),
        'Two-Qubit Gate Fidelity': ('%', True),
        'Readout Fidelity': ('%', True),
    },
    'Gate Speeds': {
        'Single-Qubit Gate Time': ('µs', False),
        'Two-Qubit Gate Time': ('µs', False),
        'Readout Time': ('µs', False),
        'Transport Time': ('µs', False),
    },
}

SCORE_WARN = 5


def ensure_dirs():
    for d in (DATA_DIR, PENDING_DIR, PROCESSED_DIR, UPLOAD_DIR):
        d.mkdir(parents=True, exist_ok=True)


# ─── Parsing ──────────────────────────────────────────────────────────────────

def parse_cell(cell_str):
    """Returns (value_float, unit_str_or_None, total_score_int) or None."""
    if not cell_str or not isinstance(cell_str, str):
        return None
    s = cell_str.strip()
    flag_it = list(re.finditer(r'\((-?\d+),\s*(-?\d+),\s*(-?\d+),\s*(-?\d+),\s*(-?\d+)\)', s))
    if not flag_it:
        return None
    total = int(flag_it[-1].group(5))
    s_num = s.lstrip('~<>≈').strip()
    nm = re.match(r'(\d+\.?\d*)', s_num)
    if not nm:
        return None
    try:
        value = float(nm.group(1))
    except ValueError:
        return None
    um = re.search(r'\b(ns|µs|ms|(?<!\w)s(?!\w)|%)\b', s[:100])
    unit = um.group(1) if um else None
    return value, unit, total


def to_us(value, unit):
    if unit is None:
        return value
    conv = {'ns': 1e-3, 'µs': 1.0, 'ms': 1e3, 's': 1e6}
    return value * conv.get(unit, 1.0)


def extract_numeric(cell, as_unit=None):
    p = parse_cell(str(cell) if cell is not None else '')
    if p is None:
        return None
    value, unit, _ = p
    if as_unit == 'µs':
        return to_us(value, unit)
    if as_unit == '%':
        if unit == '%':
            return value
        if unit is None and value <= 1.0:
            return value * 100
        return value
    if as_unit == 'fraction':
        if unit == '%' or value > 1.0:
            return value / 100.0
        return value
    if as_unit == 'hz':
        us = to_us(value, unit)
        return 1e6 / us if us and us != 0 else None
    return value


def get_score(cell):
    p = parse_cell(str(cell) if cell is not None else '')
    return p[2] if p else None


def format_authors_short(authors_str):
    if not authors_str:
        return 'Unknown'
    s = authors_str.replace(' and ', ', ').replace(' & ', ', ')
    parts = [p.strip() for p in s.split(',') if p.strip()]
    if not parts:
        return 'Unknown'
    if len(parts) == 1:
        return parts[0]
    return f"{parts[0]} … {parts[-1]}"


# ─── Data Manager ─────────────────────────────────────────────────────────────

class DataManager:
    def __init__(self):
        ensure_dirs()
        self.dfs = {}
        self.reload()

    def reload(self):
        self.dfs = {}
        for platform in PLATFORMS:
            path = FILE_MAP[platform]
            if path.exists():
                try:
                    df = pd.read_excel(path, engine='openpyxl')
                    df.columns = [str(c).replace('\n', ' ').strip() for c in df.columns]
                    df['Platform'] = platform
                    self.dfs[platform] = df
                except Exception as e:
                    print(f"Error loading {platform}: {e}")
                    self.dfs[platform] = pd.DataFrame()
            else:
                self.dfs[platform] = pd.DataFrame()

    def combined(self, platforms=None):
        sel = platforms or PLATFORMS
        frames = [self.dfs[p] for p in sel if p in self.dfs and not self.dfs[p].empty]
        return pd.concat(frames, ignore_index=True, sort=False) if frames else pd.DataFrame()

    def param_cols(self, platform=None):
        meta = {'Paper Title', 'Authors', 'Research Group / Institution',
                'Journal', 'Year', 'URL', 'Platform'}
        if platform:
            df = self.dfs.get(platform, pd.DataFrame())
            return [c for c in df.columns if c not in meta]
        all_cols, seen = [], set()
        for df in self.dfs.values():
            for c in df.columns:
                if c not in meta and c not in seen:
                    all_cols.append(c)
                    seen.add(c)
        return all_cols

    def match_col(self, df, name):
        for c in df.columns:
            if name.lower() in c.lower():
                return c
        return None

    def stat_cards(self):
        df = self.combined()
        if df.empty:
            return {'# Papers': 0, '# Platforms': 0, '# Research Groups': 0, 'Year Range': 'N/A'}
        groups = set()
        for p in PLATFORMS:
            d = self.dfs.get(p, pd.DataFrame())
            if not d.empty and 'Research Group / Institution' in d.columns:
                groups.update(d['Research Group / Institution'].dropna())
        years = df['Year'].dropna()
        try:
            yr = f"{int(years.min())}–{int(years.max())}"
        except Exception:
            yr = 'N/A'
        platforms_with_data = sum(1 for p in PLATFORMS if not self.dfs.get(p, pd.DataFrame()).empty)
        return {
            '# Papers': len(df),
            '# Platforms': platforms_with_data,
            '# Research Groups': len(groups),
            'Year Range': yr,
        }

    def _best_in_col(self, df, col_kw, unit, highest):
        col = self.match_col(df, col_kw)
        if not col:
            return None
        vals = []
        for idx, row in df.iterrows():
            v = extract_numeric(row.get(col), as_unit=unit)
            if v is not None:
                vals.append((v, idx))
        if not vals:
            return None
        best_v, best_idx = (max if highest else min)(vals)
        row = df.loc[best_idx]
        return {'value': best_v, 'platform': row.get('Platform', ''),
                'paper': str(row.get('Paper Title', '')), 'year': row.get('Year', '')}

    def best_values_by_platform(self):
        specs = [
            ('Best T₁', 'T₁', 'µs', True, 'µs'),
            ('Best 2Q Gate Fidelity', 'Two-Qubit Gate Fidelity', '%', True, '%'),
            ('Best Readout Fidelity', 'Readout Fidelity', '%', True, '%'),
            ('Shortest 1Q Gate Time', 'Single-Qubit Gate Time', 'µs', False, 'µs'),
        ]
        result = {}
        for label, col_kw, unit, highest, disp_unit in specs:
            result[label] = {'disp_unit': disp_unit}
            for p in PLATFORMS:
                df = self.dfs.get(p, pd.DataFrame())
                if df.empty:
                    continue
                info = self._best_in_col(df, col_kw, unit, highest)
                if info:
                    info['disp_unit'] = disp_unit
                    result[label][p] = info
        return result

    def low_score_entries(self, platforms=None):
        target = platforms if platforms else list(self.dfs.keys())
        out = []
        meta = {'Paper Title', 'Authors', 'Research Group / Institution', 'Journal', 'Year', 'URL', 'Platform'}
        for platform in target:
            df = self.dfs.get(platform, pd.DataFrame())
            if df.empty:
                continue
            for _, row in df.iterrows():
                for col in df.columns:
                    if col in meta:
                        continue
                    sc = get_score(row.get(col))
                    if sc is not None and sc < SCORE_WARN:
                        out.append({
                            'platform': platform,
                            'paper': str(row.get('Paper Title', ''))[:80],
                            'parameter': col,
                            'score': sc,
                            'url': str(row.get('URL', '')),
                        })
        return out

    def get_param_values(self, platforms, col_kw, unit):
        result = {}
        for p in platforms:
            df = self.dfs.get(p, pd.DataFrame())
            if df.empty:
                result[p] = []
                continue
            col = self.match_col(df, col_kw)
            if not col:
                result[p] = []
                continue
            result[p] = [v for v in (extract_numeric(c, as_unit=unit) for c in df[col]) if v is not None]
        return result

    def get_timeseries(self, platforms, col_kw, unit):
        rows = []
        for p in platforms:
            df = self.dfs.get(p, pd.DataFrame())
            if df.empty or 'Year' not in df.columns:
                continue
            col = self.match_col(df, col_kw)
            if not col:
                continue
            for _, row in df.iterrows():
                v = extract_numeric(row.get(col), as_unit=unit)
                y = row.get('Year')
                if v is not None and y is not None:
                    try:
                        rows.append({
                            'year': int(y), 'value': v, 'platform': p,
                            'paper': str(row.get('Paper Title', '') or ''),
                            'authors': str(row.get('Authors', '') or ''),
                            'journal': str(row.get('Journal', '') or ''),
                        })
                    except Exception:
                        pass
        return rows

    def get_scatter_xy(self, platforms, xcol_kw, ycol_kw, xunit, yunit):
        rows = []
        for p in platforms:
            df = self.dfs.get(p, pd.DataFrame())
            if df.empty:
                continue
            xc = self.match_col(df, xcol_kw)
            yc = self.match_col(df, ycol_kw)
            if not xc or not yc:
                continue
            for _, row in df.iterrows():
                x = extract_numeric(row.get(xc), as_unit=xunit)
                y = extract_numeric(row.get(yc), as_unit=yunit)
                if x is not None and y is not None:
                    rows.append({
                        'x': x, 'y': y, 'platform': p,
                        'paper': str(row.get('Paper Title', '') or ''),
                    })
        return rows
