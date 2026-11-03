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

# --- DATA LOADING & VALIDATION ---
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
        f"Error loading Excel files from repository root. Ensure 'Regulatory Governance.xlsx' and 'VC_Flow.xlsx' are uploaded. Details: {err}"
    )
    st.stop()

# --- SIDEBAR CONTROLS ---
st.sidebar.header("Global Dashboard Controls")
default_focus = ["United States", "Germany", "Korea"] if all(c in df_gov["Region"].values for c in ["United States", "Germany", "Korea"]) else []
target_countries = st.sidebar.multiselect(
    "Select Focus Countries (Deep-Dives & Sankey)",
    options=sorted(df_gov["Region"].unique()),
    default=default_focus,
)


# --- SECTION 1: REGULATORY GOVERNANCE SCORE MAP ---
st.header("Regulatory Governance Score")
st.markdown(
    "Interactive choropleth map zoomed into North America, Europe, North Africa, and Asia. Unselected countries appear in muted gray."
)

if all(c in df_gov.columns for c in ["Region", "Year", "VALUE (0 - 4)"]):
    map_df = (
        df_gov.groupby(["Region", "Year"], as_index=False)["VALUE (0 - 4)"]
        .mean()
        .rename(columns={"Region": "Country", "VALUE (0 - 4)": "Score"})
    )

    all_countries_list = sorted(map_df["Country"].unique().tolist())

    col_ctrl1, col_ctrl2 = st.columns(2)
    with col_ctrl1:
        map_year_mode = st.radio(
            "Select Year View", options=["2021", "2024", "Animate Both (Loop)"], horizontal=True, key="map_view"
        )
    with col_ctrl2:
        highlight_map_countries = st.multiselect(
            "Highlight Countries on Map",
            options=all_countries_list,
            default=["United States", "Germany", "Korea"] if "United States" in all_countries_list else all_countries_list[:3],
            key="map_highlight"
        )

    # Filter scores for unselected countries so they turn neutral gray
    map_df["Plot Score"] = map_df.apply(
        lambda row: row["Score"] if row["Country"] in highlight_map_countries else np.nan,
        axis=1
    )

    data_min = float(map_df["Score"].min())
    data_max = float(map_df["Score"].max())
    data_mean = float(map_df["Score"].mean())

    if map_year_mode != "Animate Both (Loop)":
        target_yr = 2021 if map_year_mode == "2021" else 2024
        filtered_map_df = map_df[map_df["Year"] == target_yr].copy()
        
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
            title=f"Regulatory Governance Scores ({target_yr})",
        )
    else:
        fig_map = px.choropleth(
            map_df,
            locations="Country",
            locationmode="country names",
            color="Plot Score",
            animation_frame="Year",
            hover_name="Country",
            hover_data={"Score": ":.2f", "Plot Score": False},
            color_continuous_scale="RdYlGn",
            color_continuous_midpoint=data_mean,
            range_color=[data_min, data_max],
            title="OECD Regulatory Governance Score Evolution (2021 vs 2024 Loop)",
        )
        
        # Force automatic animation playback and looping behavior via layout updatemenus
        fig_map.layout.updatemenus[0].buttons[0].args[1]["frame"]["duration"] = 2000
        fig_map.layout.updatemenus[0].buttons[0].args[1]["transition"]["duration"] = 800
        fig_map.layout.updatemenus[0].buttons[0].args[1]["fromcurrent"] = True
        fig_map.layout.updatemenus[0].buttons[0].args[1]["mode"] = "immediate"
        
        # Add auto-play trigger on load
        fig_map.layout.sliders[0]["pad"]["t"] = 50

    # Zoomed-in projection focusing on North America, Europe, North Africa, and Asia (excluding Australia/Antarctica)
    fig_map.update_layout(
        geo=dict(
            showframe=False,
            showcoastlines=True,
            projection_type="mercator",
            center=dict(lat=42, lon=20),
            projection_scale=2.0,  # Zooms in to eliminate Australia and frame Northern Hemisphere focus
            bgcolor="rgba(0,0,0,0)",
        ),
        coloraxis_colorbar=dict(title=f"Score<br>(Mean: {data_mean:.2f})"),
        height=650,
        margin=dict(l=0, r=0, t=50, b=0),
    )
    fig_map.update_traces(marker_line_width=0.5, selector=dict(type='choropleth'))
    st.plotly_chart(fig_map, use_container_width=True)
else:
    st.warning("Required columns ('Region', 'Year', 'VALUE (0 - 4)') not found in Regulatory Governance dataset.")


# --- SECTION 2: ANIMATED SANKEY DIAGRAM ---
st.header("Animated Sankey Diagram: Cross-Border AI VC Flows (2021–2026)")
st.markdown(
    "Tracking venture capital investment flows (in millions USD) from source countries into selected focus countries."
)

if all(c in df_vc.columns for c in ["Country source", "Destination", "Investment (In USD millions)", "year"]):
    vc_filtered = df_vc[df_vc["Destination"].isin(target_countries)].copy()

    if not vc_filtered.empty:
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
                            color="skyblue",
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
                title_text=f"AI VC Investment Flows to Focus Countries ({selected_sankey_year})",
                font_size=11,
                height=500,
            )
            st.plotly_chart(sankey_fig, use_container_width=True)
        else:
            st.info("No VC flow data available for the selected year.")
    else:
        st.info("Please select at least one focus country in the sidebar for the Sankey diagram.")
else:
    st.warning("Required columns not found in VC_Flow dataset.")


# --- SECTION 3: COMPARATIVE HORIZONTAL BAR CHART ---
st.header("Comparative Governance Benchmarking")
st.markdown(
    "Horizontal bar chart comparing all countries against the OECD average score vertical benchmark."
)

if all(c in df_gov.columns for c in ["Region", "Year", "VALUE (0 - 4)"]):
    latest_year = df_gov["Year"].max()
    latest_gov = df_gov[df_gov["Year"] == latest_year]
    
    oecd_avg_row = latest_gov[latest_gov["Region"].str.contains("OECD average", case=False, na=False)]
    avg_score = oecd_avg_row["VALUE (0 - 4)"].mean() if not oecd_avg_row.empty else latest_gov["VALUE (0 - 4)"].mean()

    country_avg = (
        latest_gov[~latest_gov["Region"].str.contains("OECD average", case=False, na=False)]
        .groupby("Region", as_index=False)["VALUE (0 - 4)"]
        .mean()
        .sort_values(by="VALUE (0 - 4)", ascending=True)
    )

    bar_fig = px.bar(
        country_avg,
        x="VALUE (0 - 4)",
        y="Region",
        orientation="h",
        title=f"Latest Regulatory Governance Scores vs. OECD Average Benchmark ({int(latest_year)})",
        labels={"VALUE (0 - 4)": "Governance Score (0-4)", "Region": "Country / Region"},
        height=700,
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
st.header("Country Deep-Dive: Investment Trends & Regulatory Performance")
st.markdown(
    "Dual-axis time series tracking investment amounts (Left Y-axis) alongside country regulatory scores and the OECD average (Right Y-axis)."
)

if not target_countries:
    st.info("Please select focus countries in the sidebar to view deep-dive time series.")

for country in target_countries:
    st.subheader(f"Deep-Dive: {country}")
    
    inv_trend = pd.DataFrame(columns=["year", "Investment (In USD millions)"])
    if all(c in df_vc.columns for c in ["Destination", "year", "Investment (In USD millions)"]):
        inv_trend = (
            df_vc[df_vc["Destination"] == country]
            .groupby("year", as_index=False)["Investment (In USD millions)"]
            .sum()
        )

    gov_trend = pd.DataFrame(columns=["year", "Score"])
    oecd_gov_trend = pd.DataFrame(columns=["year", "OECD Average Score"])
    
    if all(c in df_gov.columns for c in ["Region", "Year", "VALUE (0 - 4)"]):
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

    merged_ts = pd.merge(inv_trend, gov_trend, on="year", how="outer")
    merged_ts = pd.merge(merged_ts, oecd_gov_trend, on="year", how="outer").sort_values("year")

    if not merged_ts.empty:
        fig_dual = make_subplots(specs=[[{"secondary_y": True}]])
        fig_dual.add_trace(
            go.Bar(
                x=merged_ts["year"],
                y=merged_ts["Investment (In USD millions)"],
                name="VC Investment ($M)",
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
                    line=dict(width=3),
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
                    line=dict(dash="dot", width=2),
                ),
                secondary_y=True,
            )

        fig_dual.update_layout(
            title_text=f"{country}: Investment Trend vs. Regulatory Governance Scores",
            xaxis_title="Year",
            height=450,
        )
        fig_dual.update_yaxes(title_text="Investment ($ Millions)", secondary_y=False)
        fig_dual.update_yaxes(title_text="Regulatory Score (0-4)", secondary_y=True, range=[0, 4])
        st.plotly_chart(fig_dual, use_container_width=True)
    else:
        st.info(f"Insufficient time-series data for {country}.")


# --- SECTION 5: COMPARATIVE HEATMAPS (EXCLUDING CHINA) ---
st.header("Comparative Heatmaps (Excluding China)")

hm_col1, hm_col2 = st.columns(2)

with hm_col1:
    st.subheader("VC Flow YoY % Change (Sorted)")
    if all(c in df_vc.columns for c in ["Destination", "year", "Investment (In USD millions)"]):
        vc_nochina = df_vc[~df_vc["Destination"].str.contains("China", case=False, na=False)]
        pivot_vc = vc_nochina.pivot_table(
            index="Destination", columns="year", values="Investment (In USD millions)", aggfunc="sum"
        ).pct_change(axis=1) * 100
        
        if not pivot_vc.empty:
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
            st.info("Insufficient data for VC YoY heatmap.")
    else:
        st.warning("Required columns missing for VC heatmap.")

with hm_col2:
    st.subheader("2024 Regulatory Governance (Sorted)")
    if all(c in df_gov.columns for c in ["Region", "Year", "VALUE (0 - 4)"]):
        gov_2024 = df_gov[
            (df_gov["Year"] == 2024) 
            & (~df_gov["Region"].str.contains("China|OECD average", case=False, na=False))
        ]
        gov_2024_piv = (
            gov_2024.groupby("Region", as_index=False)["VALUE (0 - 4)"]
            .mean()
            .sort_values(by="VALUE (0 - 4)", ascending=True)
        )

        if not gov_2024_piv.empty:
            fig_hm2 = px.bar(
                gov_2024_piv,
                x="VALUE (0 - 4)",
                y="Region",
                orientation="h",
                title="2024 Governance Scores (Ascending)",
                labels={"VALUE (0 - 4)": "Score", "Region": "Country"},
                height=500,
            )
            st.plotly_chart(fig_hm2, use_container_width=True)
        else:
            st.info("No data available for 2024 governance scores.")
    else:
        st.warning("Required columns missing for Governance heatmap.")
