"""
Quantum Hardware Web Dashboard (Streamlit)

A browser-based companion to the desktop dashboard in `Final/dashboard.py`.
Reads/writes ONLY the local copy of the database inside this folder's own
`data/` directory — it never touches the original project files.

Run locally:
    streamlit run app.py
"""

import json
import os
import re
import textwrap
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from lib_data import (
    DataManager, PLATFORMS, PLATFORM_COLORS, PLATFORM_SHORT, PARAM_GROUPS,
    SCORE_WARN, extract_numeric, get_score, format_authors_short,
    ensure_dirs, PENDING_DIR, PROCESSED_DIR, UPLOAD_DIR, INSTRUCTIONS_PATH, DATA_DIR,
)
from write_to_db_web import write_paper

ensure_dirs()

st.set_page_config(
    page_title="Quantum Hardware Web Dashboard",
    page_icon="⚛️",
    layout="wide",
)

# ─── Data manager (fresh read each rerun — keeps all users in sync) ──────────

@st.cache_resource(ttl=2)
def get_dm():
    """Cached for 2 seconds only — long enough to avoid re-reading Excel on
    every widget interaction, short enough that uploads from any user show
    up for everyone almost immediately."""
    return DataManager()


def fmt_value(v, disp_unit):
    if disp_unit == 'µs' and v >= 1e6:
        return f"{v/1e6:.2f} s"
    if disp_unit == 'µs' and v >= 1000:
        return f"{v/1000:.2f} ms"
    if disp_unit == 'µs':
        return f"{v:.2f} µs"
    if disp_unit == '%':
        return f"{v:.3f}%"
    return f"{v:.3g}"


def parse_axis_label(text):
    m = re.match(r'(.+?)\s*\((.+?)\)$', text)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return text, None


def fit_ellipse_points(pts, n=60):
    """Return x,y boundary arrays of a covariance ellipse around pts (linear space)."""
    arr = np.array(pts)
    cx, cy = arr.mean(axis=0)
    if len(arr) >= 3:
        try:
            cov = np.cov(arr.T)
            vals, vecs = np.linalg.eigh(cov)
            order = vals.argsort()[::-1]
            vals, vecs = vals[order], vecs[:, order]
            a = 2.2 * np.sqrt(max(vals[0], 1e-12))
            b = 2.2 * np.sqrt(max(vals[1], 1e-12))
            theta = np.arctan2(vecs[1, 0], vecs[0, 0])
        except Exception:
            a = (arr[:, 0].ptp() or abs(cx) * 0.2 or 1) * 0.8
            b = (arr[:, 1].ptp() or abs(cy) * 0.2 or 1) * 0.8
            theta = 0
    else:
        a = (arr[:, 0].ptp() or abs(cx) * 0.2 or 1) * 0.8
        b = (arr[:, 1].ptp() or abs(cy) * 0.2 or 1) * 0.8
        theta = 0
    t = np.linspace(0, 2 * np.pi, n)
    ex = a * np.cos(t)
    ey = b * np.sin(t)
    x = cx + ex * np.cos(theta) - ey * np.sin(theta)
    y = cy + ex * np.sin(theta) + ey * np.cos(theta)
    return x, y, cx, cy


# ─── Pages ────────────────────────────────────────────────────────────────────

def page_overview(dm: DataManager):
    st.header("📊 Database Overview")

    cards = dm.stat_cards()
    cols = st.columns(4)
    for col, (k, v) in zip(cols, cards.items()):
        col.metric(k, v)

    st.subheader("Best Reported Values (by Platform)")
    best = dm.best_values_by_platform()
    for metric_label, plat_data in best.items():
        disp_unit = plat_data.get('disp_unit', '')
        entries = [(p, info) for p, info in plat_data.items() if p in PLATFORMS]
        if not entries:
            continue
        st.markdown(f"**{metric_label}**")
        cols = st.columns(len(entries))
        for col, (p, info) in zip(cols, entries):
            v = fmt_value(info['value'], disp_unit)
            col.markdown(
                f"<div style='border:1.5px solid {PLATFORM_COLORS[p]}; border-radius:6px; "
                f"padding:8px;'>"
                f"<span style='color:{PLATFORM_COLORS[p]}; font-weight:bold; font-size:12px;'>"
                f"{PLATFORM_SHORT[p]}</span><br>"
                f"<span style='color:{PLATFORM_COLORS[p]}; font-weight:bold; font-size:20px;'>{v}</span><br>"
                f"<span style='color:#777; font-size:11px;'>{info['year']}</span><br>"
                f"<span style='font-size:11px;'>{info['paper']}</span>"
                f"</div>", unsafe_allow_html=True)

    st.subheader("Database Table")
    plat_filter = st.selectbox("Platform", ['All'] + PLATFORMS, key='ov_platform')
    platforms = PLATFORMS if plat_filter == 'All' else [plat_filter]
    df = dm.combined(platforms)

    warns = dm.low_score_entries(None if plat_filter == 'All' else [plat_filter])
    if warns:
        with st.expander(f"⚠ {len(warns)} low-reliability-score entries (score < {SCORE_WARN})"):
            st.dataframe(pd.DataFrame(warns), use_container_width=True)

    if df.empty:
        st.info("No data for this selection.")
        return

    display_cols = ['Platform', 'Paper Title', 'Research Group / Institution', 'Year',
                    'Single-Qubit Gate Fidelity', 'Two-Qubit Gate Fidelity', 'Readout Fidelity',
                    'T₁', 'T₂* (Ramsey)', 'Single-Qubit Gate Time', 'Two-Qubit Gate Time',
                    'Readout Time', 'Transport Time', 'URL']
    seen, ordered = set(), []
    for dc in display_cols:
        for c in df.columns:
            if (dc == c or dc.lower() in c.lower()) and c not in seen:
                ordered.append(c)
                seen.add(c)

    st.dataframe(
        df[ordered],
        use_container_width=True,
        height=420,
        column_config={
            "URL": st.column_config.LinkColumn("URL"),
        },
    )

    # ── Parameter Glossary ────────────────────────────────────────────────────
    st.divider()
    st.subheader("📖 Parameter Glossary")
    st.caption("Short explanations of every measured parameter in the database.")

    GLOSSARY = [
        ("T₁ — Energy Relaxation Time",
         "The characteristic time for a qubit to relax from its excited state (|1⟩) to its "
         "ground state (|0⟩) through energy exchange with the environment. "
         "It sets an upper bound on how long quantum information can be stored in the energy degree of freedom."),
        ("T₂* — Ramsey Coherence Time",
         "The coherence time measured using the Ramsey interferometry protocol, in which the "
         "qubit evolves freely between two π/2 pulses. "
         "It characterises the total dephasing rate, including contributions from both energy "
         "relaxation and low-frequency phase noise present during free evolution."),
        ("T₂ — Hahn Echo Coherence Time",
         "The coherence time measured using a spin-echo sequence, in which a refocusing π pulse "
         "is applied at the midpoint of free evolution. "
         "It characterises dephasing that remains after quasi-static, low-frequency noise has "
         "been refocused by the echo pulse."),
        ("T₂ — CPMG Coherence Time",
         "The coherence time measured using the Carr-Purcell-Meiboom-Gill (CPMG) protocol, "
         "which applies a periodic train of refocusing π pulses during free evolution. "
         "It characterises dephasing that remains after noise components within the pulse "
         "repetition bandwidth have been suppressed."),
        ("Single-Qubit Gate Fidelity",
         "A measure of how accurately a single-qubit unitary operation is implemented on the "
         "physical qubit, relative to the intended ideal operation. "
         "It is quantified as the overlap between the actual and ideal output states, "
         "averaged over a representative set of input states."),
        ("Two-Qubit Gate Fidelity",
         "A measure of how accurately a two-qubit unitary operation — typically an entangling "
         "gate — is implemented on the physical qubits, relative to the intended ideal operation. "
         "It is quantified as the overlap between the actual and ideal output states, "
         "averaged over a representative set of input states."),
        ("Readout Fidelity",
         "The probability of correctly identifying the quantum state of a qubit upon measurement. "
         "It accounts for both assignment errors (misidentifying |0⟩ as |1⟩ or vice versa) "
         "and, in some definitions, errors induced by the measurement process itself."),
        ("Single-Qubit Gate Time",
         "The duration of a single-qubit gate operation, defined as the time from the start "
         "to the end of the control pulse applied to the qubit. "
         "It is determined by the drive amplitude and the required rotation angle."),
        ("Two-Qubit Gate Time",
         "The duration of a two-qubit gate operation, defined as the time required to implement "
         "the entangling interaction between the two qubits. "
         "It depends on the coupling mechanism and the strength of the qubit–qubit interaction."),
        ("Readout Time",
         "The duration of the measurement operation applied to a qubit to determine its state. "
         "It encompasses the time required for the measurement signal to be acquired and "
         "processed to a binary outcome."),
        ("Transport Time",
         "The time required to physically relocate a qubit within the processor from one "
         "trapping or operational zone to another. "
         "It is relevant to architectures in which qubit connectivity is achieved through "
         "physical movement rather than fixed coupling."),
    ]

    for param_name, explanation in GLOSSARY:
        with st.expander(param_name):
            st.write(explanation)

    # ── Contact Us ────────────────────────────────────────────────────────────
    st.divider()
    st.subheader("✉️ Contact Us")
    st.markdown(
        "Found an error in the database, have a suggestion, or want to contribute a paper? "
        "We'd love to hear from you."
    )
    st.markdown(
        "<div style='background:#f0f4ff; border:1.5px solid #90aee8; border-radius:8px; "
        "padding:14px 20px; display:inline-block; font-size:16px;'>"
        "📧 <a href='mailto:romi283@gmail.com' style='color:#1a56db; text-decoration:none;'>"
        "romi283@gmail.com</a>"
        "</div>",
        unsafe_allow_html=True,
    )


def page_explorer(dm: DataManager):
    st.header("🔍 Parameter Explorer")

    c1, c2, c3 = st.columns(3)
    platform = c1.selectbox("Platform", PLATFORMS, key='exp_platform')
    df = dm.dfs.get(platform, pd.DataFrame())
    cols = dm.param_cols(platform)
    if not cols:
        st.info("No parameter columns for this platform.")
        return
    param = c2.selectbox("Parameter", cols, key='exp_param')
    view = c3.selectbox("View As", ['Table', 'Bar Chart', 'Box Plot'], key='exp_view')

    explanations = {
        'Table': "Shows each paper with a value for this parameter. Papers without data "
                 "for this parameter are excluded.",
        'Bar Chart': "Each bar = one paper's value. Hover a bar to see the full paper title.",
        'Box Plot': "Shows the statistical distribution: box = middle 50% (IQR), "
                    "line = median, whiskers = data range.",
    }
    st.caption(explanations.get(view, ''))

    if df.empty or not param:
        st.info("No data.")
        return
    col = dm.match_col(df, param)
    if not col:
        st.info("No data.")
        return

    unit = 'µs'
    for group, params in PARAM_GROUPS.items():
        if any(k.lower() in param.lower() for k in params):
            for k, (u, _) in params.items():
                if k.lower() in param.lower():
                    unit = u
                    break

    if view == 'Table':
        meta = ['Paper Title', 'Research Group / Institution', 'Year', 'URL']
        disp_cols = [c for c in meta if c in df.columns] + [col]
        mask = df[col].apply(lambda v: isinstance(v, str) and v.strip() != '')
        sub = df.loc[mask, disp_cols]
        st.dataframe(
            sub, use_container_width=True, height=420,
            column_config={"URL": st.column_config.LinkColumn("URL")},
        )
        return

    vals, labels = [], []
    for _, row in df.iterrows():
        v = extract_numeric(row.get(col), as_unit=unit)
        if v is not None:
            vals.append(v)
            labels.append(str(row.get('Paper Title', '')) or 'Untitled')

    if not vals:
        st.info("No numeric data for this parameter.")
        return

    color = PLATFORM_COLORS.get(platform, '#1565C0')

    if view == 'Bar Chart':
        # Short numeric x-axis labels; full paper title + value shown on hover only.
        idx = list(range(1, len(vals) + 1))
        fig = go.Figure(go.Bar(
            x=idx, y=vals, marker_color=color,
            marker_line_color='black', marker_line_width=0.7,
            customdata=labels,
            hovertemplate="<b>%{customdata}</b><br>Value: %{y:.4g} " + unit + "<extra></extra>",
        ))
        fig.update_xaxes(title="Paper # (hover a bar for full title)", dtick=1)
        fig.update_yaxes(title=f"{param} ({unit})")
        fig.update_layout(title=f"{platform} — {param}", height=520)
        st.plotly_chart(fig, use_container_width=True)
    else:  # Box Plot
        fig = go.Figure(go.Box(
            y=vals, name=param, marker_color=color, boxmean=True,
        ))
        fig.update_yaxes(title=f"{param} ({unit})")
        fig.update_layout(title=f"{platform} — {param}", height=520)
        st.plotly_chart(fig, use_container_width=True)


def page_comparison(dm: DataManager):
    st.header("⚖️ Technology Comparison")

    c1, c2, c3 = st.columns([2, 2, 1])
    all_params = [p for group in PARAM_GROUPS.values() for p in group]
    param = c1.selectbox("Parameter", all_params, key='cmp_param')
    chart_type = c2.selectbox("Chart Type", ['Box Plot', 'Scatter (by paper)', 'Bar (mean ± std)'],
                              key='cmp_chart')
    log_y = c3.checkbox("Log Y", value=True, key='cmp_log')

    platforms = st.multiselect("Platforms", PLATFORMS, default=PLATFORMS, key='cmp_platforms')
    if not platforms:
        st.info("Select at least one platform.")
        return

    unit = 'µs'
    for group, params in PARAM_GROUPS.items():
        if param in params:
            unit, _ = params[param]
            break

    data = dm.get_param_values(platforms, param, unit)
    active = [(p, data[p]) for p in platforms if data.get(p)]
    if not active:
        st.info("No data for this selection.")
        return

    fig = go.Figure()
    if chart_type == 'Box Plot':
        for p, vals in active:
            fig.add_trace(go.Box(y=vals, name=PLATFORM_SHORT[p], marker_color=PLATFORM_COLORS[p]))
    elif chart_type == 'Scatter (by paper)':
        for p, vals in active:
            fig.add_trace(go.Scatter(
                x=[PLATFORM_SHORT[p]] * len(vals), y=vals, mode='markers',
                marker=dict(color=PLATFORM_COLORS[p], size=10, line=dict(color='black', width=0.7)),
                name=PLATFORM_SHORT[p]))
    else:  # Bar (mean ± std)
        means = [np.mean(v) for _, v in active]
        stds = [np.std(v) for _, v in active]
        labels = [PLATFORM_SHORT[p] for p, _ in active]
        colors = [PLATFORM_COLORS[p] for p, _ in active]
        fig.add_trace(go.Bar(x=labels, y=means, error_y=dict(type='data', array=stds),
                             marker_color=colors, marker_line_color='black', marker_line_width=0.7))

    if log_y:
        fig.update_yaxes(type='log')
    fig.update_yaxes(title=f"{param} ({unit})", gridcolor='#DDDDDD', griddash='dash')
    fig.update_xaxes(gridcolor='#DDDDDD', griddash='dash')
    fig.update_layout(title=f"{param} by Platform", height=560, plot_bgcolor='#F9F9F9')
    st.plotly_chart(fig, use_container_width=True)


def page_roadmap(dm: DataManager):
    st.header("📈 Roadmap Over Time")

    c1, c2, c3 = st.columns([2, 2, 1])
    all_params = [p for group in PARAM_GROUPS.values() for p in group]
    param = c1.selectbox("Parameter", all_params, key='rm_param')
    platforms = c2.multiselect("Platforms", PLATFORMS, default=PLATFORMS, key='rm_platforms')
    log_y = c3.checkbox("Log Y", value=True, key='rm_log')
    trend = st.checkbox("Show trend line per platform", value=True, key='rm_trend')

    if not platforms:
        st.info("Select at least one platform.")
        return

    unit = 'µs'
    for group, params in PARAM_GROUPS.items():
        if param in params:
            unit, _ = params[param]
            break

    rows = dm.get_timeseries(platforms, param, unit)
    if not rows:
        st.info("No data for this selection.")
        return

    fig = go.Figure()
    by_plat = {}
    for r in rows:
        by_plat.setdefault(r['platform'], []).append(r)

    for p, pts in by_plat.items():
        pts.sort(key=lambda r: r['year'])
        xs = [r['year'] for r in pts]
        ys = [r['value'] for r in pts]
        hover_text = [
            f"{format_authors_short(r['authors'])}, {r['journal']}, {r['year']}"
            if r['journal'] else f"{format_authors_short(r['authors'])}, {r['year']}"
            for r in pts
        ]
        fig.add_trace(go.Scatter(
            x=xs, y=ys, mode='markers', name=PLATFORM_SHORT[p],
            marker=dict(color=PLATFORM_COLORS[p], size=11, line=dict(color='black', width=0.7)),
            customdata=hover_text,
            hovertemplate="%{customdata}<br>Value: %{y:.4g} " + unit + "<extra></extra>",
        ))
        if trend and len(pts) >= 2:
            try:
                log_vals = np.log10(ys) if log_y else np.array(ys)
                z = np.polyfit(xs, log_vals, 1)
                px_ = np.linspace(min(xs), max(xs), 50)
                py = np.poly1d(z)(px_)
                if log_y:
                    py = 10 ** py
                fig.add_trace(go.Scatter(
                    x=px_, y=py, mode='lines', line=dict(color=PLATFORM_COLORS[p], dash='dash'),
                    showlegend=False, hoverinfo='skip'))
            except Exception:
                pass

    if log_y:
        fig.update_yaxes(type='log')
    fig.update_xaxes(title='Year', gridcolor='#DDDDDD', griddash='dash')
    fig.update_yaxes(title=f"{param} ({unit})", gridcolor='#DDDDDD', griddash='dash')
    fig.update_layout(title=f"{param} over Time", height=580, plot_bgcolor='#F9F9F9')
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Hover a point to see: First Author … Last Author, Journal, Year")


def page_tradeoff(dm: DataManager):
    st.header("🔀 Trade-off / Benchmark")
    st.caption("Square = Single-Qubit pair · Triangle = Two-Qubit pair · Circle = Mixed parameters. "
              "Ellipses show each platform's cluster.")

    x_options = ['Single-Qubit Gate Time (µs)', 'Two-Qubit Gate Time (µs)', 'Readout Time (µs)',
                'T₁ (µs)', 'T₂* (Ramsey) (µs)', 'T₂ (Hahn Echo) (µs)']
    y_options = ['Single-Qubit Gate Fidelity (%)', 'Two-Qubit Gate Fidelity (%)',
                'Readout Fidelity (%)', 'T₂ (Hahn Echo) (µs)', 'T₁ (µs)']

    c1, c2 = st.columns(2)
    x_label = c1.selectbox("X Axis", x_options, key='tb_x')
    y_label = c2.selectbox("Y Axis", y_options, key='tb_y')

    preset = st.radio("Quick preset", ['(custom)', '2Q Fidelity vs Gate Time',
                                       '1Q Fidelity vs Gate Time', 'Readout F vs Readout Time'],
                      horizontal=True, key='tb_preset')
    presets = {
        '2Q Fidelity vs Gate Time': ('Two-Qubit Gate Time (µs)', 'Two-Qubit Gate Fidelity (%)'),
        '1Q Fidelity vs Gate Time': ('Single-Qubit Gate Time (µs)', 'Single-Qubit Gate Fidelity (%)'),
        'Readout F vs Readout Time': ('Readout Time (µs)', 'Readout Fidelity (%)'),
    }
    if preset in presets:
        x_label, y_label = presets[preset]

    platforms = st.multiselect("Platforms", PLATFORMS, default=PLATFORMS, key='tb_platforms')
    if not platforms:
        st.info("Select at least one platform.")
        return

    xcol, xunit = parse_axis_label(x_label)
    ycol, yunit = parse_axis_label(y_label)
    rows = dm.get_scatter_xy(platforms, xcol, ycol, xunit or 'µs', yunit or '%')
    if not rows:
        st.info("No data for this selection.")
        return

    combo = (xcol + ' ' + ycol).lower()
    if 'two-qubit' in combo:
        marker_symbol, marker_name = 'triangle-up', 'Two-Qubit pair'
    elif 'single-qubit' in combo:
        marker_symbol, marker_name = 'square', 'Single-Qubit pair'
    else:
        marker_symbol, marker_name = 'circle', 'Mixed parameters'

    by_plat = {}
    for r in rows:
        by_plat.setdefault(r['platform'], []).append(r)

    fig = go.Figure()
    # Ellipses first (behind points)
    for p, pts in by_plat.items():
        if len(pts) < 2:
            continue
        xy = [(r['x'], r['y']) for r in pts]
        ex, ey, cx, cy = fit_ellipse_points(xy)
        fig.add_trace(go.Scatter(
            x=ex, y=ey, mode='lines', fill='toself',
            fillcolor=PLATFORM_COLORS[p].replace(')', ', 0.13)').replace('rgb', 'rgba')
                      if PLATFORM_COLORS[p].startswith('rgb') else PLATFORM_COLORS[p] + '22',
            line=dict(color=PLATFORM_COLORS[p], width=1.4),
            showlegend=False, hoverinfo='skip'))
        fig.add_annotation(x=cx, y=cy, text=f"<b>{PLATFORM_SHORT[p]}</b>",
                           showarrow=False, font=dict(color=PLATFORM_COLORS[p], size=11),
                           yshift=25)

    for p, pts in by_plat.items():
        fig.add_trace(go.Scatter(
            x=[r['x'] for r in pts], y=[r['y'] for r in pts], mode='markers',
            marker=dict(symbol=marker_symbol, color=PLATFORM_COLORS[p], size=13,
                       line=dict(color='black', width=1)),
            name=PLATFORM_SHORT[p],
            customdata=[r['paper'] for r in pts],
            hovertemplate="<b>%{customdata}</b><br>x=%{x:.4g}, y=%{y:.4g}<extra></extra>",
        ))

    fig.update_xaxes(title=x_label, gridcolor='#DDDDDD', griddash='dash')
    fig.update_yaxes(title=y_label, gridcolor='#DDDDDD', griddash='dash')
    fig.update_layout(title=f"{ycol} vs {xcol} — {marker_name}", height=620, plot_bgcolor='#F9F9F9')
    st.plotly_chart(fig, use_container_width=True)


# ─── Add Paper (PDF) — shared, writes only to the local web copy ────────────

def build_prompt(pdf_path):
    return (
        f"Please run the quantum-eval skill on this paper:\n"
        f"@\"{pdf_path}\"\n\n"
        f"After extracting the parameters, do NOT write directly to any database — "
        f"the user wants to review the extracted values first.\n\n"
        f"Instead, save the extracted data as a JSON file inside this folder "
        f"(create it if it does not already exist):\n"
        f"{PENDING_DIR}\n\n"
        f"Name the file <platform>_<short-title-slug>.json and use exactly this structure:\n"
        "{\n"
        '  "platform": "<platform name>",\n'
        '  "paper_title": "<title>",\n'
        '  "authors": "<authors>",\n'
        '  "institution": "<institution>",\n'
        '  "year": <year as integer>,\n'
        '  "parameters": {"<column name>": "<value string>", ...}\n'
        "}\n"
    )


def list_pending_files():
    if not PENDING_DIR.is_dir():
        return []
    files = [f for f in PENDING_DIR.iterdir() if f.suffix == '.json' and f.is_file()]
    files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
    return files


def page_add_paper(dm: DataManager):
    st.header("📄 Add Paper to Database")
    st.info(
        "**This database is shared** — once a paper is approved here, every visitor to "
        "this dashboard sees it immediately (everyone reads/writes the same web copy).\n\n"
        "**How it works:**\n"
        "1. Upload a PDF below.\n"
        "2. Copy the generated prompt and paste it into your own Claude Code "
        "(no API key needed — it uses your own Claude Code authentication).\n"
        "3. Claude Code extracts the parameters and saves them for review.\n"
        "4. Come back here, click **Check for Extracted Data**, review/edit, then "
        "**Approve & Save**."
    )

    ss = st.session_state

    # ── Step 1: upload PDF ──────────────────────────────────────────────────
    st.subheader("Step 1 — Upload PDF")
    uploaded = st.file_uploader("Choose a PDF", type=['pdf'], key='pdf_uploader')
    if uploaded is not None:
        save_path = UPLOAD_DIR / uploaded.name
        with open(save_path, 'wb') as f:
            f.write(uploaded.getbuffer())
        ss['current_pdf_path'] = str(save_path)
        st.success(f"Saved: {uploaded.name}")

    if ss.get('current_pdf_path'):
        st.subheader("Step 2 — Copy & Paste into Claude Code")
        prompt = build_prompt(ss['current_pdf_path'])
        st.code(prompt, language='text')
        st.caption("Click the copy icon in the top-right of the box above, "
                  "then paste into Claude Code and press Enter.")

    # ── Step 3: load & review pending extraction ────────────────────────────
    st.subheader("Step 3 — Load & Review Extracted Data")
    if st.button("🔍 Check for Extracted Data"):
        files = list_pending_files()
        ss['pending_files'] = [str(f) for f in files]
        if not files:
            st.warning("No extracted data found yet. Make sure Claude Code finished "
                      "and saved a JSON file into the pending_review folder.")

    pending_files = ss.get('pending_files', [])
    if pending_files:
        chosen = st.selectbox("Extracted file", pending_files,
                              format_func=lambda p: Path(p).name, key='chosen_pending')
        try:
            with open(chosen, encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            st.error(f"Could not read file: {e}")
            data = None

        if data is not None:
            st.markdown("**Review and edit before saving:**")
            c1, c2 = st.columns(2)
            platform = c1.selectbox("Platform", PLATFORMS,
                                    index=PLATFORMS.index(data.get('platform')) if data.get('platform') in PLATFORMS else 0,
                                    key='rv_platform')
            year = c2.text_input("Year", str(data.get('year', '')), key='rv_year')
            title = st.text_input("Paper Title", data.get('paper_title', ''), key='rv_title')
            authors = st.text_input("Authors", data.get('authors', ''), key='rv_authors')
            institution = st.text_input("Research Group / Institution",
                                        data.get('institution', ''), key='rv_inst')

            st.markdown("**Extracted Parameters** (edit values directly in the table):")
            params = data.get('parameters', {}) or {}
            param_df = pd.DataFrame(
                [{'Parameter': k, 'Value': v, 'Score': get_score(str(v))} for k, v in params.items()]
            )
            edited = st.data_editor(
                param_df, num_rows="dynamic", use_container_width=True, key='rv_params_editor',
                column_config={
                    "Score": st.column_config.NumberColumn("Reliability Score", disabled=True),
                },
            )

            if st.button("✅ Approve & Save to Database", type="primary"):
                ss['review_payload'] = {
                    'platform': platform,
                    'paper_title': title.strip(),
                    'authors': authors.strip(),
                    'institution': institution.strip(),
                    'year': int(year) if year.strip().isdigit() else year.strip(),
                    'parameters': {row['Parameter']: row['Value'] for _, row in edited.iterrows()
                                  if row['Parameter'] and str(row['Value']).strip()},
                    'source_file': chosen,
                }
                ss['show_confirm'] = True

    # ── Confirmation step ────────────────────────────────────────────────────
    if ss.get('show_confirm') and ss.get('review_payload'):
        payload = ss['review_payload']
        st.warning("**Please confirm the technology and parameters are correct before "
                  "they are written to the shared database.**")
        st.markdown(f"**Platform:** {payload['platform']}")
        st.markdown(f"**Paper:** {payload['paper_title']}")
        st.markdown(f"**Year:** {payload['year']}")
        st.markdown("**Parameters that will be written:**")
        for name, val in payload['parameters'].items():
            sc = get_score(str(val))
            flag = " ⚠ low score" if (sc is not None and sc < SCORE_WARN) else ""
            st.markdown(f"- **{name}:** {val}{flag}")

        cc1, cc2 = st.columns(2)
        if cc1.button("✅ Yes, these are correct"):
            ss['show_confirm'] = False
            ss['show_journal_url'] = True
        if cc2.button("✖ No, let me edit"):
            ss['show_confirm'] = False
            ss['review_payload'] = None

    # ── Journal / URL step ───────────────────────────────────────────────────
    if ss.get('show_journal_url') and ss.get('review_payload'):
        payload = ss['review_payload']
        st.subheader("Journal & Source Link")
        st.caption(f"For: {payload['paper_title']}")
        journal = st.text_input("Journal", key='jr_journal',
                                placeholder="e.g. Nature, Physical Review Letters, arXiv …")
        url = st.text_input("URL (link to the paper)", key='jr_url', placeholder="https://...")
        st.caption("Both fields can be left blank and filled in later directly in Excel.")

        if st.button("💾 Save with these details", type="primary"):
            payload['journal'] = journal.strip()
            payload['url'] = url.strip()
            # Store the approved paper in session state only.
            # In the deployed version each user has their own session — additions
            # are visible only to that user for the duration of their session and
            # are not written to the shared database or shown to other visitors.
            if 'session_papers' not in ss:
                ss['session_papers'] = []
            ss['session_papers'].append(payload)
            # archive the pending JSON locally if it exists
            try:
                src = Path(payload['source_file'])
                if src.exists():
                    src.replace(PROCESSED_DIR / src.name)
            except Exception:
                pass
            st.success(
                f"✅ '{payload['paper_title']}' has been saved to your session. "
                f"It is visible to you for the rest of this session. "
                f"Other visitors to the dashboard see the shared baseline database only."
            )
            for k in ['show_journal_url', 'review_payload', 'show_confirm',
                     'pending_files', 'current_pdf_path']:
                ss.pop(k, None)

    # Show papers added this session
    if ss.get('session_papers'):
        st.divider()
        st.markdown(f"**Papers added this session ({len(ss['session_papers'])}):**")
        for sp in ss['session_papers']:
            st.markdown(f"- {sp.get('paper_title','(untitled)')} — "
                       f"{sp.get('platform','')} — {sp.get('year','')}")


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    st.sidebar.title("⚛️ Quantum Hardware Dashboard")
    st.sidebar.caption("Web version — shared database, read by every visitor")
    page = st.sidebar.radio("Go to", [
        "Overview", "Parameter Explorer", "Technology Comparison",
        "Roadmap Over Time", "Trade-off / Benchmark", "Add Paper (PDF)",
    ])
    if st.sidebar.button("↺ Refresh data"):
        get_dm.clear()

    dm = get_dm()

    pages = {
        "Overview": page_overview,
        "Parameter Explorer": page_explorer,
        "Technology Comparison": page_comparison,
        "Roadmap Over Time": page_roadmap,
        "Trade-off / Benchmark": page_tradeoff,
        "Add Paper (PDF)": page_add_paper,
    }
    pages[page](dm)


if __name__ == "__main__":
    main()
