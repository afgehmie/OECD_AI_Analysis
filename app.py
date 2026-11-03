import time
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="OECD AI Regulation & VC Investment Dashboard",
    page_icon="📊",
    layout="wide",
)

st.title(
    "OECD AI Regulation & Venture Capital Investment Analysis (2021–2026)"
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

# Continuous loop state handling
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

# Centered bounding box including North America, Europe, Africa, & Asia (excluding Australia)
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

# Trigger auto-refresh loop for year switching
if map_mode == "Animate Both (Loop)":
    time.sleep(2.5)
    st.session_state.map_loop_year = (
        2024 if st.session_state.map_loop_year == 2021 else 2021
    )
    st.rerun()


# --- PLOT 2: ANIMATED SANKEY DIAGRAM ---
st.header("2. Animated Sankey Diagram: VC Flow (2021–2026)")
st.markdown(
    "Tracking venture capital investment flows from source countries to destination countries."
)

vc_filtered = df_vc[
    df_vc[vc_dest_col].isin(selected_deepdive_countries)
].copy()

if not vc_filtered.empty:
    selected_sankey_year = st.slider(
        "Select Year for Sankey Flow",
        int(vc_filtered[vc_year_col].min()),
        int(vc_filtered[vc_year_col].max()),
        2021,
    )
    sankey_data = vc_filtered[
        vc_filtered[vc_year_col] == selected_sankey_year
    ]

    if not sankey_data.empty:
        sources = sankey_data[vc_src_col].astype(str).tolist()
        destinations = sankey_data[vc_dest_col].astype(str).tolist()
        values = sankey_data[vc_inv_col].tolist()

        all_nodes = list(set(sources + destinations))
        node_indices = {n: i for i, n in enumerate(all_nodes)}

        sankey_fig = go.Figure(
            data=[
                go.Sankey(
                    node=dict(
                        pad=15,
                        thickness=20,
                        line=dict(color="black", width=0.5),
                        label=all_nodes,
                        color="cornflowerblue",
                    ),
                    link=dict(
                        source=[node_indices[s] for s in sources],
                        target=[node_indices[d] for d in destinations],
                        value=values,
                    ),
                )
            ]
        )
        sankey_fig.update_layout(
            title_text=f"AI VC Investment Flows ({selected_sankey_year})",
            font_size=11,
            height=500,
        )
        st.plotly_chart(sankey_fig, use_container_width=True)
else:
    st.info("Select focus countries in the sidebar to display the Sankey diagram.")


# --- PLOT 3: DIVERGING HORIZONTAL BAR CHART ---
st.header("3. Comparative Governance Benchmarking (Diverging)")
st.markdown(
    "Diverging bar chart centered at the OECD average benchmark. Scores above average extend rightward (green); scores below average extend leftward (orange)."
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

# Assign custom color scale
colors = []
for _, row in bar_df.iterrows():
    c = row[gov_region_col]
    if c in focus_countries:
        colors.append("royalblue" if c == "United States" else "gold" if c == "Germany" else "crimson")
    else:
        colors.append("mediumseagreen" if row["Divergence"] >= 0 else "coral")

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
    yaxis_title="Country",
    height=750,
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


# --- PLOTS 4, 5, & 6: COUNTRY DEEP-DIVE TIME SERIES ---
st.header("4. Country Deep-Dives: VC Investment vs. Regulatory Governance")
st.markdown(
    "Time-series deep-dives corresponding to your reference drawing. Dual Y-axes track investment flow ($M USD) against regulatory score (0–4)."
)

for country in selected_deepdive_countries:
    st.subheader(f"Deep-Dive: {country}")

    inv_ts = (
        df_vc[df_vc[vc_dest_col] == country]
        .groupby(vc_year_col, as_index=False)[vc_inv_col]
        .sum()
        .rename(columns={vc_year_col: "Year", vc_inv_col: "Investment"})
    )

    gov_ts = (
        df_gov[df_gov[gov_region_col] == country]
        .groupby(gov_year_col, as_index=False)[gov_val_col]
        .mean()
        .rename(columns={gov_year_col: "Year", gov_val_col: "Score"})
    )

    oecd_ts = (
        df_gov[
            df_gov[gov_region_col].str.contains(
                "OECD average", case=False, na=False
            )
        ]
        .groupby(gov_year_col, as_index=False)[gov_val_col]
        .mean()
        .rename(columns={gov_year_col: "Year", gov_val_col: "OECD_Avg"})
    )

    merged_ts = pd.merge(inv_ts, gov_ts, on="Year", how="outer")
    merged_ts = pd.merge(merged_ts, oecd_ts, on="Year", how="outer").sort_values(
        "Year"
    )

    if not merged_ts.empty:
        fig_dual = make_subplots(specs=[[{"secondary_y": True}]])

        # Red Line: Investment Flow (Left Y-Axis)
        fig_dual.add_trace(
            go.Scatter(
                x=merged_ts["Year"],
                y=merged_ts["Investment"],
                name="Investment ($M USD)",
                line=dict(color="red", width=3),
                mode="lines+markers",
            ),
            secondary_y=False,
        )

        # Blue Line: Country Regulatory Governance Score (Right Y-Axis)
        fig_dual.add_trace(
            go.Scatter(
                x=merged_ts["Year"],
                y=merged_ts["Score"],
                name=f"{country} Governance Score",
                line=dict(color="blue", width=3),
                mode="lines+markers",
            ),
            secondary_y=True,
        )

        # Gray Dashed Line: OECD Average Score (Right Y-Axis)
        fig_dual.add_trace(
            go.Scatter(
                x=merged_ts["Year"],
                y=merged_ts["OECD_Avg"],
                name="OECD Average Score",
                line=dict(color="gray", width=2, dash="dash"),
                mode="lines",
            ),
            secondary_y=True,
        )

        fig_dual.update_layout(
            title=f"{country}: Investment Flow vs. Regulatory Compliance",
            xaxis=dict(title="Year", dtick=1),
            height=450,
        )
        fig_dual.update_yaxes(
            title_text="Investment (in millions USD)", secondary_y=False
        )
        fig_dual.update_yaxes(
            title_text="Regulatory Governance Score",
            secondary_y=True,
            range=[0, 4],
        )
        st.plotly_chart(fig_dual, use_container_width=True)


# --- PLOT 5: COMPARATIVE HEATMAPS (TOP 20 PERFORMERS) ---
st.header("5. Comparative Heatmaps (Top 20 Performers, Excluding China)")

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

    if not piv_vc.empty:
        piv_vc["mean_pct"] = piv_vc.mean(axis=1)
        top20_vc = piv_vc.sort_values(by="mean_pct", ascending=False).head(20)
        top20_vc = top20_vc.drop(columns="mean_pct")

        fig_hm1 = px.imshow(
            top20_vc,
            labels=dict(x="Year", y="Country", color="YoY % Change"),
            title="Top 20 VC YoY % Change Heatmap",
            color_continuous_scale="RdBu",
            aspect="auto",
        )
        st.plotly_chart(fig_hm1, use_container_width=True)

with col_hm2:
    st.subheader("2024 Regulatory Governance Heatmap")
    gov_2024 = df_gov[
        (df_gov[gov_year_col] == 2024)
        & (
            ~df_gov[gov_region_col].str.contains(
                "China|OECD average", case=False, na=False
            )
        )
    ]
    gov_2024_piv = (
        gov_2024.groupby(gov_region_col, as_index=False)[gov_val_col]
        .mean()
        .sort_values(by=gov_val_col, ascending=False)
        .head(20)
    )

    if not gov_2024_piv.empty:
        matrix_data = gov_2024_piv.set_index(gov_region_col)[[gov_val_col]]

        fig_hm2 = px.imshow(
            matrix_data,
            labels=dict(x="Metric", y="Country", color="Score (0-4)"),
            title="Top 20 Regulatory Governance Heatmap (2024)",
            color_continuous_scale="YlGnBu",
            aspect="auto",
        )
        st.plotly_chart(fig_hm2, use_container_width=True)
