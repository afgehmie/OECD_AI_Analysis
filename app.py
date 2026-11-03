import time
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Balancing Regulation & Freedom to Foster Firms Innovation",
    page_icon="📊",
    layout="wide",
)

st.title(
    "Balancing Regulation & Freedom to Foster Firms Innovation: OECD Case Study of United States, Germany, and Korea"
)
st.markdown(
    "Comprehensive dashboard tracking regulatory governance benchmarks and cross-border AI-related venture capital flows."
)


# --- DATA LOADING & CLEANING ---
@st.cache_data
def load_data():
    try:
        df_gov = pd.read_excel("Regulatory Governance.xlsx")
        df_vc = pd.read_excel("VC_Flow.xlsx")
    except Exception as e:
        return None, None, str(e)

    df_gov.columns = [c.strip() for c in df_gov.columns]
    df_vc.columns = [c.strip() for c in df_vc.columns]
    return df_gov, df_vc, None


df_gov, df_vc, err = load_data()

if err:
    st.error(
        f"Error loading Excel files from repository root. Details: {err}"
    )
    st.stop()

# Flexibly resolve column names
gov_region_col = next(
    (c for c in df_gov.columns if c.lower() in ["region", "country"]),
    df_gov.columns[0],
)
gov_year_col = next(
    (c for c in df_gov.columns if c.lower() in ["year", "time"]),
    df_gov.columns[2] if len(df_gov.columns) > 2 else df_gov.columns[0],
)
gov_val_col = next(
    (c for c in df_gov.columns if "value" in c.lower() or "score" in c.lower()),
    df_gov.columns[3] if len(df_gov.columns) > 3 else df_gov.columns[0],
)

vc_dest_col = next(
    (c for c in df_vc.columns if "dest" in c.lower()), df_vc.columns[1]
)
vc_src_col = next(
    (c for c in df_vc.columns if "source" in c.lower()), df_vc.columns[2]
)
vc_inv_col = next(
    (c for c in df_vc.columns if "invest" in c.lower()), df_vc.columns[4]
)
vc_year_col = next(
    (c for c in df_vc.columns if "year" in c.lower()), df_vc.columns[5]
)

# Sidebar focus control
st.sidebar.header("Global Dashboard Controls")
focus_countries = ["United States", "Germany", "Korea"]
selected_deepdive_countries = st.sidebar.multiselect(
    "Focus Countries for Deep-Dive",
    options=sorted(df_gov[gov_region_col].astype(str).unique()),
    default=[
        c
        for c in focus_countries
        if c in df_gov[gov_region_col].astype(str).values
    ],
)


# --- PLOT 1: REGULATORY GOVERNANCE SCORE MAP ---
st.header("1. Regulatory Governance Score Map")
st.markdown(
    "Choropleth map framed across North America, Europe, North Africa, and Asia (excluding Australia)."
)

map_df = (
    df_gov.groupby([gov_region_col, gov_year_col], as_index=False)[gov_val_col]
    .mean()
    .rename(
        columns={
            gov_region_col: "Country",
            gov_year_col: "Year",
            gov_val_col: "Score",
        }
    )
)

all_countries_list = sorted(map_df["Country"].unique().tolist())

col1, col2 = st.columns(2)
with col1:
    map_mode = st.radio(
        "Select Year View",
        options=["2021", "2024", "Animate Both (Loop)"],
        horizontal=True,
    )
with col2:
    highlight_map = st.multiselect(
        "Highlight Countries on Map",
        options=all_countries_list,
        default=[c for c in focus_countries if c in all_countries_list],
    )

if map_mode == "Animate Both (Loop)":
    if "map_loop_year" not in st.session_state:
        st.session_state.map_loop_year = 2021
    current_map_year = st.session_state.map_loop_year
else:
    current_map_year = int(map_mode)

filtered_map_df = map_df[map_df["Year"] == current_map_year].copy()
filtered_map_df["Plot Score"] = filtered_map_df.apply(
    lambda r: r["Score"] if r["Country"] in highlight_map else np.nan, axis=1
)

data_min, data_max, data_mean = (
    float(map_df["Score"].min()),
    float(map_df["Score"].max()),
    float(map_df["Score"].mean()),
)

fig_map = px.choropleth(
    filtered_map_df,
    locations="Country",
    locationmode="country names",
    color="Plot Score",
    hover_name="Country",
    hover_data={"Score": ":.2f", "Plot Score": False},
    color_continuous_scale="RdYlGn",
    color_continuous_midpoint=data_mean,
    range_color=[data_min, data_max],
    title=f"Regulatory Governance Scores ({current_map_year})",
)

fig_map.update_layout(
    geo=dict(
        showframe=False,
        showcoastlines=True,
        projection_type="natural earth",
        center=dict(lat=35, lon=10),
        projection_scale=1.15,
        bgcolor="rgba(0,0,0,0)",
    ),
    coloraxis_colorbar=dict(title=f"Score<br>(Mean: {data_mean:.2f})"),
    height=600,
    margin=dict(l=0, r=0, t=50, b=0),
)
st.plotly_chart(fig_map, use_container_width=True)

if map_mode == "Animate Both (Loop)":
    time.sleep(2.5)
    st.session_state.map_loop_year = (
        2024 if st.session_state.map_loop_year == 2021 else 2021
    )
    st.rerun()


# --- PLOT 2: CROSS-BORDER AI VENTURE CAPITAL FLOW (2021-2026) ---
st.header("Cross-border AI Venture Capital Flow (2021-2026)")
st.markdown(
    "Interactive Sankey diagram tracking cross-border VC investments from source countries (left) to destination countries (right) with the year scale below."
)

if all(
    c in df_vc.columns
    for c in [vc_src_col, vc_dest_col, vc_inv_col, vc_year_col]
):
    min_yr = int(df_vc[vc_year_col].min())
    max_yr = int(df_vc[vc_year_col].max())
    
    selected_sankey_year = st.slider(
        "Select Year for Sankey Flow",
        min_yr,
        max_yr,
        2021,
    )
    
    sankey_data = df_vc[df_vc[vc_year_col] == selected_sankey_year].groupby(
        [vc_src_col, vc_dest_col], as_index=False
    )[vc_inv_col].sum()

    if not sankey_data.empty:
        sources = sankey_data[vc_src_col].astype(str).tolist()
        destinations = sankey_data[vc_dest_col].astype(str).tolist()
        values = sankey_data[vc_inv_col].tolist()

        unique_sources = sorted(list(set(sources)))
        unique_dests = sorted(list(set(destinations)))
        all_nodes = unique_sources + unique_dests

        src_indices = {s: i for i, s in enumerate(unique_sources)}
        dest_indices = {d: i + len(unique_sources) for i, d in enumerate(unique_dests)}

        mapped_sources = [src_indices[s] for s in sources]
        mapped_destinations = [dest_indices[d] for d in destinations]

        node_colors = []
        for n in all_nodes:
            if n == "United States" or n == "USA":
                node_colors.append("#1f77b4")  # Blue
            elif n == "Germany" or n == "DEU":
                node_colors.append("#ff7f0e")  # Orange
            elif n == "Korea" or n == "KOR":
                node_colors.append("#2ca02c")  # Green
            else:
                node_colors.append("#aec7e8")  # Muted gray-blue

        sankey_fig = go.Figure(
            data=[
                go.Sankey(
                    node=dict(
                        pad=15,
                        thickness=20,
                        line=dict(color="black", width=0.5),
                        label=all_nodes,
                        color=node_colors,
                    ),
                    link=dict(
                        source=mapped_sources,
                        target=mapped_destinations,
                        value=values,
                    ),
                )
            ]
        )
        sankey_fig.update_layout(
            title_text=f"Cross-border AI VC Flow ({selected_sankey_year})",
            font_size=11,
            height=650,
        )
        st.plotly_chart(sankey_fig, use_container_width=True)
    else:
        st.info("No VC records available for the selected year.")
else:
    st.warning("Required columns missing in VC_Flow dataset.")


# --- PLOT 3: DIVERGING HORIZONTAL BAR CHART ---
st.header("3. Comparative Governance Benchmarking (All Countries)")
st.markdown(
    "Diverging bar chart displaying all countries. United States, Germany, and Korea are highlighted with light accent."
)

latest_yr = df_gov[gov_year_col].max()
latest_gov = df_gov[df_gov[gov_year_col] == latest_yr].copy()

oecd_avg_val = latest_gov[
    latest_gov[gov_region_col].str.contains("OECD average", case=False, na=False)
][gov_val_col].mean()
if np.isnan(oecd_avg_val):
    oecd_avg_val = latest_gov[gov_val_col].mean()

bar_df = (
    latest_gov[
        ~latest_gov[gov_region_col].str.contains(
            "OECD average", case=False, na=False
        )
    ]
    .groupby(gov_region_col, as_index=False)[gov_val_col]
    .mean()
)
bar_df["Divergence"] = bar_df[gov_val_col] - oecd_avg_val
bar_df = bar_df.sort_values(by="Divergence", ascending=True)

colors = []
for _, row in bar_df.iterrows():
    c = row[gov_region_col]
    if c in focus_countries:
        colors.append("#ffbb78")
    else:
        colors.append("dodgerblue" if row["Divergence"] >= 0 else "lightcoral")

bar_fig = go.Figure()
bar_fig.add_trace(
    go.Bar(
        y=bar_df[gov_region_col],
        x=bar_df["Divergence"],
        orientation="h",
        text=bar_df[gov_val_col].apply(lambda x: f"{x:.2f}"),
        textposition="outside",
        marker_color=colors,
    )
)
bar_fig.update_layout(
    title=f"Regulatory Governance Divergence from OECD Average ({oecd_avg_val:.2f}) - {int(latest_yr)}",
    xaxis_title="Divergence from OECD Average Score",
    yaxis=dict(title="Country", tickfont=dict(size=9)),
    height=900,
    shapes=[
        dict(
            type="line",
            x0=0,
            y0=-0.5,
            x1=0,
            y1=len(bar_df) - 0.5,
            line=dict(color="black", width=2, dash="dash"),
        )
    ],
)
st.plotly_chart(bar_fig, use_container_width=True)


# --- PLOTS 4, 5, & 6: SIDE-BY-SIDE COUNTRY DEEP-DIVE PANELS ---
st.header("4. Country Deep-Dives: Investment Trend & Governance Comparison")
st.markdown(
    "Side-by-side panels: Left panel shows investment trend (2021–2026); right panel displays double-bar comparative governance performance (2021 vs 2024)."
)

for country in selected_deepdive_countries:
    st.subheader(f"Deep-Dive Panel: {country}")
    
    sub_col1, sub_col2 = st.columns(2)

    with sub_col1:
        inv_ts = (
            df_vc[df_vc[vc_dest_col] == country]
            .groupby(vc_year_col, as_index=False)[vc_inv_col]
            .sum()
            .rename(columns={vc_year_col: "Year", vc_inv_col: "Investment"})
        )
        
        fig_inv = px.line(
            inv_ts,
            x="Year",
            y="Investment",
            markers=True,
            title=f"{country}: Investment Trend ($M USD)",
            labels={"Investment": "Investment ($M USD)", "Year": "Year"}
        )
        fig_inv.update_traces(line=dict(color="crimson", width=3))
        fig_inv.update_layout(height=400)
        st.plotly_chart(fig_inv, use_container_width=True)

    with sub_col2:
        gov_comp = df_gov[
            (df_gov[gov_region_col].isin([country])) |
            (df_gov[gov_region_col].str.contains("OECD average", case=False, na=False))
        ].copy()
        
        gov_comp["Entity"] = gov_comp[gov_region_col].apply(
            lambda x: "OECD Average" if "OECD average" in str(x) else country
        )
        
        gov_grouped = gov_comp.groupby(["Year", "Entity"], as_index=False)[gov_val_col].mean()
        gov_grouped = gov_grouped[gov_grouped["Year"].isin([2021, 2024])]

        fig_bars = px.bar(
            gov_grouped,
            x="Year",
            y=gov_val_col,
            color="Entity",
            barmode="group",
            title=f"{country} vs. OECD Average Governance (0–4)",
            labels={gov_val_col: "Governance Score (0–4)", "Year": "Year"},
            color_discrete_map={country: "royalblue", "OECD Average": "gray"}
        )
        fig_bars.update_yaxes(range=[0, 4])
        fig_bars.update_layout(height=400)
        st.plotly_chart(fig_bars, use_container_width=True)


# --- PLOT 5 & 6: HEATMAPS ---
st.header("5. Comparative Heatmaps")

col_hm1, col_hm2 = st.columns(2)

with col_hm1:
    st.subheader("VC Flow YoY % Change Heatmap")
    vc_no_china = df_vc[
        ~df_vc[vc_dest_col].str.contains("China", case=False, na=False)
    ]
    
    piv_vc = (
        vc_no_china.pivot_table(
            index=vc_dest_col,
            columns=vc_year_col,
            values=vc_inv_col,
            aggfunc="sum",
        )
        .pct_change(axis=1)
        * 100
    )

    if 2021 in piv_vc.columns:
        piv_vc = piv_vc.drop(columns=[2021])

    if not piv_vc.empty:
        piv_vc = piv_vc.round(2)
        sort_col = 2026 if 2026 in piv_vc.columns else piv_vc.columns[-1]
        piv_vc = piv_vc.sort_values(by=sort_col, ascending=False)

        fig_hm1 = px.imshow(
            piv_vc,
            labels=dict(x="Year", y="Country", color="YoY % Change (%)"),
            title="",
            color_continuous_scale="RdBu",
            text_auto=True,
            aspect="auto",
        )
        fig_hm1.update_layout(height=550, margin=dict(t=10, b=10))
        st.plotly_chart(fig_hm1, use_container_width=True)

with col_hm2:
    st.subheader("2024 Regulatory Governance (Score ≥ 0.75)")
    gov_2024 = df_gov[
        (df_gov[gov_year_col] == 2024)
        & (
            ~df_gov[gov_region_col].str.contains(
                "China|OECD average", case=False, na=False
            )
        )
    ]
    gov_2024_filtered = (
        gov_2024.groupby(gov_region_col, as_index=False)[gov_val_col]
        .mean()
    )
    gov_2024_filtered = gov_2024_filtered[
        gov_2024_filtered[gov_val_col] >= 0.75
    ].sort_values(by=gov_val_col, ascending=True)

    if not gov_2024_filtered.empty:
        colors_hm2 = [
            "#ffbb78" if c in focus_countries else "dodgerblue"
            for c in gov_2024_filtered[gov_region_col]
        ]

        bar_hm2 = go.Figure(
            go.Bar(
                x=gov_2024_filtered[gov_val_col],
                y=gov_2024_filtered[gov_region_col],
                orientation="h",
                text=gov_2024_filtered[gov_val_col].apply(lambda x: f"{x:.2f}"),
                textposition="outside",
                marker_color=colors_hm2,
            )
        )
        bar_hm2.update_layout(
            title="",
            xaxis_title="Score",
            yaxis=dict(title="Country", tickfont=dict(size=9)),
            height=550,
            margin=dict(t=10, b=10),
        )
        st.plotly_chart(bar_hm2, use_container_width=True)
