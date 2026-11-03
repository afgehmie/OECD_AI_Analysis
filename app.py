import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Page Configuration
st.set_page_config(
    page_title="OECD AI Regulation & VC Investment Dashboard",
    page_icon="📊",
    layout="wide",
)

st.title(
    "OECD AI Regulation & Venture Capital Investment Analysis (2021–2026)"
)
st.markdown(
    "This dashboard tracks regulatory governance benchmarks and cross-border AI-related VC investment flows."
)


# --- DATA LOADING & CACHING ---
@st.cache_data
def load_data():
    # Load datasets directly from repository root
    df_gov = pd.read_excel("Regulatory Governance.xlsx")
    df_vc = pd.read_excel("VC_Flow.xlsx")
    return df_gov, df_gov_clean, df_vc


# Clean and prepare Regulatory Governance data
# Assuming columns: Region (or Country), Measure, Year, VALUE (0 - 4)
try:
    df_gov = pd.read_excel("Regulatory Governance.xlsx")
    df_vc = pd.read_excel("VC_Flow.xlsx")
except Exception as e:
    st.error(
        f"Error loading Excel files. Ensure 'Regulatory Governance.xlsx' and 'VC_Flow.xlsx' are in the repository root. Details: {e}"
    )
    st.stop()


# Standardize column names just in case
df_gov.columns = [c.strip() for c in df_gov.columns]
df_vc.columns = [c.strip() for c in df_vc.columns]

# --- SIDEBAR CONTROLS ---
st.sidebar.header("Dashboard Controls")
target_countries = st.sidebar.multiselect(
    "Select Focus Countries",
    options=["United States", "Germany", "Korea"],
    default=["United States", "Germany", "Korea"],
)

# --- SECTION 1: REGULATORY GOVERNANCE SCORE MAP ---
st.header("Regulatory Governance Score")
st.markdown(
    "Interactive choropleth map showing OECD regulatory governance performance. Use the controls below to toggle years, auto-play the animation, or highlight specific countries."
)

if (
    "Region" in df_gov.columns
    and "Year" in df_gov.columns
    and "VALUE (0 - 4)" in df_gov.columns
):
    map_df = (
        df_gov.groupby(["Region", "Year"], as_index=False)["VALUE (0 - 4)"]
        .mean()
        .rename(columns={"Region": "Country", "VALUE (0 - 4)": "Score"})
    )

    # Sidebar or inline controls for map
    col_ctrl1, col_ctrl2 = st.columns(2)
    with col_ctrl1:
        map_year_mode = st.radio(
            "Select Year View", options=["2021", "2024", "Animate Both"], horizontal=True
        )
    with col_ctrl2:
        highlight_map_countries = st.multiselect(
            "Highlight Countries on Map",
            options=["United States", "Germany", "Korea"],
            default=["United States", "Germany", "Korea"],
        )

    # Filter or structure data based on mode
    if map_year_mode != "Animate Both":
        filtered_map_df = map_df[map_df["Year"] == int(map_year_mode)].copy()
    else:
        filtered_map_df = map_df.copy()

    # Assign display colors/categories for highlighting
    filtered_map_df["Display Score"] = filtered_map_df.apply(
        lambda row: row["Score"]
        if row["Country"] in highlight_map_countries
        else np.nan,
        axis=1,
    )

    # Plotly Map with Diverging Color Scale (RdYlGn: Red to Yellow to Green)
    if map_year_mode == "Animate Both":
        fig_map = px.choropleth(
            filtered_map_df,
            locations="Country",
            locationmode="country names",
            color="Score",
            animation_frame="Year",
            hover_name="Country",
            color_continuous_scale="RdYlGn",
            range_color=[0, 4],
            title="OECD Regulatory Governance Score Evolution (2021 vs 2024)",
        )
        # Configure play/pause transition speed for smooth auto-loop
        fig_map.layout.updatemenus[0].buttons[0].args[1]["frame"]["duration"] = (
            2000  # 2 seconds per frame
        )
        fig_map.layout.updatemenus[0].buttons[0].args[1]["transition"][
            "duration"
        ] = 800
    else:
        fig_map = px.choropleth(
            filtered_map_df,
            locations="Country",
            locationmode="country names",
            color="Score",
            hover_name="Country",
            color_continuous_scale="RdYlGn",
            range_color=[0, 4],
            title=f"Regulatory Governance Scores ({map_year_mode})",
        )

    # Enlarge and improve map framing/projection for better clarity
    fig_map.update_layout(
        geo=dict(
            showframe=False,
            showcoastlines=True,
            projection_type="winkel tripel",  # Provides a balanced, clear global view
            center=dict(lat=45, lon=10),
            zoom=1.8,
        ),
        height=600,
        margin=dict(l=0, r=0, t=50, b=0),
    )
    st.plotly_chart(fig_map, use_container_width=True)
else:
    st.warning(
        "Expected columns ('Region', 'Year', 'VALUE (0 - 4)') not found in Regulatory Governance dataset."
    )

# --- SECTION 2: ANIMATED SANKEY DIAGRAM ---
st.header(
    "2. Animated Sankey Diagram: Cross-Border AI VC Flows (2021–2026)"
)
st.markdown(
    "Tracking venture capital investment flows (in millions USD) from source countries into United States, Germany, and Korea."
)

if all(
    col in df_vc.columns
    for col in [
        "Country source",
        "Destination",
        "Investment (In USD millions)",
        "year",
    ]
):
    # Filter VC flows where destination is among target countries
    vc_filtered = df_vc[df_vc["Destination"].isin(target_countries)].copy()

    # Create year-by-year Sankey or aggregate
    selected_sankey_year = st.slider(
        "Select Year for Sankey Flow",
        int(vc_filtered["year"].min()),
        int(vc_filtered["year"].max()),
        2021,
    )
    vc_year_data = vc_filtered[vc_filtered["year"] == selected_sankey_year]

    if not vc_year_data.empty:
        sources = vc_year_data["Country source"].tolist()
        destinations = vc_year_data["Destination"].tolist()
        values = vc_year_data["Investment (In USD millions)"].tolist()

        all_nodes = list(set(sources + destinations))
        node_indices = {node: i for i, node in enumerate(all_nodes)}

        sankey_fig = go.Figure(
            data=[
                go.Sankey(
                    node=dict(
                        pad=15,
                        thickness=20,
                        line=dict(color="black", width=0.5),
                        label=all_nodes,
                        color="blue",
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
            title_text=f"AI VC Investment Flows to Target Countries ({selected_sankey_year})",
            font_size=10,
        )
        st.plotly_chart(sankey_fig, use_container_width=True)
    else:
        st.info("No VC flow data available for the selected year and destinations.")
else:
    st.warning("Expected columns not found in VC_Flow dataset.")


# --- SECTION 3: COMPARATIVE HORIZONTAL BAR CHART ---
st.header("3. Regulatory Governance Score vs. OECD Average")
st.markdown(
    "Horizontal bar chart benchmarking all countries against the OECD average score."
)

if "Region" in df_gov.columns and "VALUE (0 - 4)" in df_gov.columns:
    latest_gov = df_gov[df_gov["Year"] == df_gov["Year"].max()]
    avg_score = latest_gov[latest_gov["Region"].str.contains("OECD average", case=False, na=False)][
        "VALUE (0 - 4)"
    ].mean()
    if np.isnan(avg_score):
        avg_score = latest_gov["VALUE (0 - 4)"].mean()

    country_avg = (
        latest_gov.groupby("Region", as_index=False)["VALUE (0 - 4)"]
        .mean()
        .sort_values(by="VALUE (0 - 4)", ascending=True)
    )

    bar_fig = px.bar(
        country_avg,
        x="VALUE (0 - 4)",
        y="Region",
        orientation="h",
        title=f"Latest Regulatory Governance Scores vs OECD Benchmark ({int(latest_gov['Year'].max())})",
        labels={"VALUE (0 - 4)": "Governance Score", "Region": "Country"},
    )
    bar_fig.add_vline(
        x=avg_score,
        line_dash="dash",
        line_color="red",
        annotation_text=f"OECD Average: {avg_score:.2f}",
        annotation_position="top right",
    )
    st.plotly_chart(bar_fig, use_container_width=True)


# --- SECTION 4: DUAL-AXIS TIME SERIES FOR TARGET COUNTRIES ---
st.header("4. Country Deep-Dive: Investment Trend & Regulatory Performance")
st.markdown(
    "Dual-axis time series tracking investment amounts (Left Y-axis) alongside country regulatory scores and OECD average (Right Y-axis)."
)

for country in target_countries:
    st.subheader(f"Deep-Dive: {country}")
    # Prepare investment time series
    if all(col in df_vc.columns for col in ["Destination", "year", "Investment (In USD millions)"]):
        inv_trend = (
            df_vc[df_vc["Destination"] == country]
            .groupby("year", as_index=False)["Investment (In USD millions)"]
            .sum()
        )
    else:
        inv_trend = pd.DataFrame(columns=["year", "Investment (In USD millions)"])

    # Prepare governance time series
    if all(col in df_gov.columns for col in ["Region", "Year", "VALUE (0 - 4)"]):
        gov_trend = (
            df_gov[df_gov["Region"] == country]
            .groupby("Year", as_index=False)["VALUE (0 - 4)"]
            .mean()
            .rename(columns={"Year": "year", "VALUE (0 - 4)": "Score"})
        )
        oecd_gov_trend = (
            df_gov[df_gov["Region"].str.contains("OECD average", case=False, na=False)]
            .groupby("Year", as_index=False)["VALUE (0 - 4)"]
            .mean()
            .rename(columns={"Year": "year", "VALUE (0 - 4)": "OECD Average Score"})
        )
    else:
        gov_trend = pd.DataFrame(columns=["year", "Score"])
        oecd_gov_trend = pd.DataFrame(columns=["year", "OECD Average Score"])

    merged_ts = pd.merge(inv_trend, gov_trend, on="year", how="outer")
    merged_ts = pd.merge(merged_ts, oecd_gov_trend, on="year", how="outer").sort_values("year")

    if not merged_ts.empty and "Investment (In USD millions)" in merged_ts.columns:
        from plotly.subplots import make_subplots

        fig_dual = make_subplots(specs=[[{"secondary_y": True}]])
        fig_dual.add_trace(
            go.Bar(
                x=merged_ts["year"],
                y=merged_ts["Investment (In USD millions)"],
                name="VC Investment (M USD)",
                marker_color="cornflowerblue",
            ),
            secondary_y=False,
        )
        if "Score" in merged_ts.columns:
            fig_dual.add_trace(
                go.Scatter(
                    x=merged_ts["year"],
                    y=merged_ts["Score"],
                    name=f"{country} Regulatory Score",
                    marker_color="darkorange",
                    mode="lines+markers",
                ),
                secondary_y=True,
            )
        if "OECD Average Score" in merged_ts.columns:
            fig_dual.add_trace(
                go.Scatter(
                    x=merged_ts["year"],
                    y=merged_ts["OECD Average Score"],
                    name="OECD Average Score",
                    marker_color="gray",
                    line=dict(dash="dot"),
                ),
                secondary_y=True,
            )

        fig_dual.update_layout(
            title_text=f"{country}: Investment Trend vs. Regulatory Governance Scores",
            xaxis_title="Year",
        )
        fig_dual.update_yaxes(title_text="Investment ($ Millions)", secondary_y=False)
        fig_dual.update_yaxes(title_text="Regulatory Score (0-4)", secondary_y=True, range=[0, 4])
        st.plotly_chart(fig_dual, use_container_width=True)
    else:
        st.info(f"Insufficient time-series data for {country}.")


# --- SECTION 5: HEATMAPS ---
st.header("5. Comparative Heatmaps (Excluding China)")

col1, col2 = st.columns(2)

with col1:
    st.subheader("VC Flow YoY % Change (Sorted)")
    if all(col in df_vc.columns for col in ["Destination", "year", "Investment (In USD millions)"]):
        # Exclude China
        vc_nochina = df_vc[~df_vc["Destination"].str.contains("China", case=False, na=False)]
        pivot_vc = vc_nochina.pivot_table(
            index="Destination", columns="year", values="Investment (In USD millions)", aggfunc="sum"
        ).pct_change(axis=1) * 100
        pivot_vc["mean_val"] = pivot_vc.mean(axis=1)
        pivot_vc = pivot_vc.sort_values(by="mean_val", ascending=True).drop(columns="mean_val")

        fig_hm1 = px.imshow(
            pivot_vc,
            labels=dict(x="Year", y="Country", color="YoY % Change"),
            title="VC Flow YoY % Change (Ascending)",
            aspect="auto",
            color_continuous_scale="RdBu",
        )
        st.plotly_chart(fig_hm1, use_container_width=True)
    else:
        st.warning("Data columns missing for VC heatmap.")

with col2:
    st.subheader("2024 Regulatory Governance Scores (Sorted)")
    if all(col in df_gov.columns for col in ["Region", "Year", "VALUE (0 - 4)"]):
        gov_2024 = df_gov[(df_gov["Year"] == 2024) & (~df_gov["Region"].str.contains("China|OECD average", case=False, na=False))]
        gov_2024_piv = (
            gov_2024.groupby("Region", as_index=False)["VALUE (0 - 4)"]
            .mean()
            .sort_values(by="VALUE (0 - 4)", ascending=True)
        )

        fig_hm2 = px.bar(
            gov_2024_piv,
            x="VALUE (0 - 4)",
            y="Region",
            orientation="h",
            title="2024 Governance Scores (Ascending)",
            labels={"VALUE (0 - 4)": "Score", "Region": "Country"},
        )
        st.plotly_chart(fig_hm2, use_container_width=True)
    else:
        st.warning("Data columns missing for Governance heatmap.")
