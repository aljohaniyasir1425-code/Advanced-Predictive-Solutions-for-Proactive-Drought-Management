
from PIL import Image
import streamlit as st
import pandas as pd
import geopandas as gpd
import folium
import plotly.express as px
from streamlit_folium import st_folium

# ===========================
# Page
# ===========================

st.set_page_config(
    page_title="Saudi Arabia Drought Dashboard",
    page_icon= None,
    layout="wide"
)
logo = Image.open("kacst_logo_.png.jpeg")
col1, col2 = st.columns([1, 5])

with col1:
    st.image(logo, width=170)

with col2:
    st.title("Saudi Arabia Drought Dashboard")
    
st.markdown("""
<style>

/* خلفية الداشبورد */
.stApp{
    background:
        radial-gradient(circle at bottom right,
            rgba(170,60,255,0.30) 0%,
            transparent 25%),
        radial-gradient(circle at top left,
            rgba(90,120,255,0.15) 0%,
            transparent 35%),
        linear-gradient(
            135deg,
            #010718 0%,
            #03113E 30%,
            #082C84 65%,
            #1746D8 100%
        );
    color: white;
}

/* الشريط العلوي */
header[data-testid="stHeader"]{
    background: linear-gradient(
        90deg,
        #010718,
        #082C84,
        #4A2FFF
    ) !important;
}

/* إزالة اللون الأسود خلف الصفحة */
[data-testid="stAppViewContainer"]{
    background: transparent;
}

[data-testid="stAppViewContainer"] > .main{
    background: transparent;
}

/* القائمة الجانبية إن وجدت */
[data-testid="stSidebar"]{
    background: rgba(0,0,40,0.75);
}

/* النصوص */
h1,h2,h3,h4,h5,h6,label,p,span{
    color:white !important;
}

</style>
""", unsafe_allow_html=True)


st.markdown("---")

# ===========================
# Upload Dataset
# ===========================

st.subheader("Upload Monthly Dataset")

uploaded_file = st.file_uploader(
    "",
    type=["csv"]
)

if uploaded_file is not None:
    climate = pd.read_csv(uploaded_file)
    st.success("Dataset uploaded successfully")
else:
    climate = pd.read_csv("data/climate_monthly_spi3.csv")

# ===========================
# Load GIS Files
# ===========================

grid = gpd.read_file(
    "data/al_ahsa_grid_no_empty_quarter.geojson"
)

boundary = gpd.read_file(
    "data/al_ahsa_boundary_no_empty_quarter.geojson"
)

mapping = pd.read_csv(
    "data/grid_to_climate_mapping.csv"
)
pred = pd.read_csv("predictions.csv")
satellite = pd.read_csv("data/Drought_Predictions_74_Regions.csv")
satellite["Date"] = pd.to_datetime(satellite["Date"])
satellite["year"] = satellite["Date"].dt.year
satellite["month"] = satellite["Date"].dt.month

# نفترض Region_ID = grid_id
satellite = satellite.rename(columns={"Region_ID": "grid_id"})
grid = grid.to_crs(epsg=4326)
boundary = boundary.to_crs(epsg=4326)

# ===========================
# Merge
# ===========================

merged = mapping.merge(
    climate,
    on="climate_sequence_id",
    how="left"
)

grid = grid.merge(
    merged,
    on="grid_id",
    how="left"
)

grid["year"] = pd.to_numeric(
    grid["year"],
    errors="coerce"
)

grid["month"] = pd.to_numeric(
    grid["month"],
    errors="coerce"
)

# ===========================
# Metrics
# ===========================

c1, c2, c3, c4 = st.columns(4)

c1.metric(
    "Grid Cells",
    grid["grid_id"].nunique()
)

c2.metric(
    "Climate Records",
    len(climate)
)

c3.metric(
    "Years",
    climate["year"].nunique()
)

c4.metric(
    "Months",
    climate["month"].nunique()
)

st.markdown("---")

# ===========================
# Filters
# ===========================

year = st.selectbox(
    "Year",
    sorted(grid["year"].dropna().unique())
)

month = st.selectbox(
    "Month",
    sorted(
        grid[
            grid["year"] == year
        ]["month"].dropna().unique()
    )
)
st.markdown("---")
st.subheader("Map Layer")

col1, col2 = st.columns(2)

with col1:
    climate = st.button(
        " Climate Data",
        use_container_width=True
    )

with col2:
    satellite_btn = st.button(
    "Satellite Data",
    use_container_width=True
)

if "layer" not in st.session_state:
    st.session_state.layer = "Climate Data"

if climate:
    st.session_state.layer = "Climate Data"

if satellite_btn:
    st.session_state.layer = "Satellite Data"

layer = st.session_state.layer

if layer == "Climate Data":

    map_data = grid[
        (grid["year"] == year) &
        (grid["month"] == month)
    ].copy()

else:

    map_data = grid[
    (grid["year"] == year) &
    (grid["month"] == month)
].copy()

sat_data = satellite[
    (satellite["year"] == year) &
    (satellite["month"] == month)
]
print(map_data.columns.tolist())
map_data = map_data.merge(
    sat_data[["grid_id", "Drought_Prediction"]],
    on="grid_id",
    how="left"
)
   
map_data = gpd.GeoDataFrame(
    map_data,
    geometry="geometry",
    crs=grid.crs
)
c1, c2, c3, c4 = st.columns(4)

if layer == "Climate Data":

    c1.metric("Temperature", f"{map_data['T2M_mean'].mean():.1f} °C")
    c2.metric("Rainfall", f"{map_data['precip_accum'].mean():.2f}")
    c3.metric("Humidity", f"{map_data['RH2M_mean'].mean():.1f}%")
    c4.metric("SPI-3", f"{map_data['target_spi3'].mean():.2f}")

else:

    drought = (map_data["Drought_Prediction"] == "Yes (جفاف)").sum()
    normal = (map_data["Drought_Prediction"] == "No (طبيعي)").sum()
    rate = drought / len(map_data) * 100

    c1.metric("Drought Cells", drought)
    c2.metric("Normal Cells", normal)
    c3.metric("Drought Rate", f"{rate:.1f}%")
    c4.metric("Prediction", map_data["Drought_Prediction"].mode()[0])
# ===========================
# Map
# ===========================

colors = {
    "Extreme": "#800026",
    "Severe": "#BD0026",
    "Moderate": "#FD8D3C",
    "Mild": "#FED976",
    "Near Normal": "#31A354"
}
prediction_colors = {
    "high": "#800026",
    "medium": "#FD8D3C",
    "low": "#31A354"
}
m = folium.Map(
    location=[25.3, 49.6],
    zoom_start=8,
    tiles=None
)

folium.TileLayer(
    tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    attr="Esri",
    name="Esri Satellite",
    overlay=False,
    control=True
).add_to(m)

# حدود الأحساء
folium.GeoJson(
    boundary.to_json(),
    style_function=lambda feature: {
        "fillColor": "none",
        "color": "black",
        "weight": 2
    }
).add_to(m)
if layer == "Climate Data":
    color_field = "drought_level"
else:
    color_field = "Drought_Prediction"
# طبقة الجفاف
folium.GeoJson(
    map_data.to_json(),

    style_function=lambda feature: {
        "fillColor":
    colors.get(feature["properties"]["drought_level"], "#808080")
    if layer == "Climate Data"
    else (
    "#E53935" if feature["properties"]["Drought_Prediction"] == "Yes (جفاف)"
    else "#43A047"
),
        "fillOpacity": 0.75,
        "color": "#ffffff",
"weight": 0.1
    },

    tooltip=folium.GeoJsonTooltip(
        fields=[
    "grid_id",
   "drought_level" if layer == "Climate Data" else "Drought_Prediction"
],

aliases=[
    "Grid ID",
    "Drought Level" if layer == "Climate Data" else "Prediction"
]
    ),

    popup=folium.GeoJsonPopup(
    fields=[
        "grid_id",
        "drought_level" if layer == "Climate Data" else "Drought_Prediction",
        "target_spi3",
        "T2M_mean",
        "precip_accum",
        "RH2M_mean"
    ],
    aliases=[
        "Grid ID",
        "Drought Level" if layer == "Climate Data" else "Prediction",
        "SPI-3",
        "Temperature (°C)",
        "Rainfall (mm)",
        "Humidity (%)"
    ]
)
).add_to(m)
if layer == "Climate Data":
    legend_title = "Drought Levels"
else:
    legend_title = "Prediction Risk"
legend_html = f"""
<div style="
position: fixed;
bottom: 40px;
left: 40px;
width: 170px;
background-color: white;
border: 2px solid #666;
border-radius: 10px;
padding: 10px;
font-family: Arial;
font-size: 13px;
font-weight: bold;
color: black;
z-index:9999;
">

<div style="margin-bottom:8px; color:black;">
{legend_title}
</div>

<div style="color:black;"><span style="color:#31A354;">■</span> Near Normal</div>
<div style="color:black;"><span style="color:#FED976;">■</span> Mild</div>
<div style="color:black;"><span style="color:#FD8D3C;">■</span> Moderate</div>
<div style="color:black;"><span style="color:#BD0026;">■</span> Severe</div>
<div style="color:black;"><span style="color:#800026;">■</span> Extreme</div>

</div>
"""
if layer == "Climate Data":
    legend_title = "Drought Levels"
else:
    legend_title = "Prediction Risk"
m.get_root().html.add_child(folium.Element(legend_html))
st_folium(
    m,
    width=1200,
    height=700
)
st.markdown("---")
st.subheader("Drought Level Distribution")

st.markdown("---")
if layer == "Climate Data":

    st.subheader("Climate Variables")

    fig = px.bar(
        x=["Temperature", "Rainfall", "Humidity", "SPI-3"],
        y=[
            map_data["T2M_mean"].mean(),
            map_data["precip_accum"].mean(),
            map_data["RH2M_mean"].mean(),
            map_data["target_spi3"].mean()
        ],
        labels={"x":"Variable","y":"Average"},
        template="plotly_dark"
    )

    st.plotly_chart(fig, use_container_width=True)

else:

    st.subheader("Satellite Prediction Analysis")

    # Pie Chart
    pie = px.pie(
    map_data,
    names="Drought_Prediction",
    title="Prediction Distribution",
    color="Drought_Prediction",
    color_discrete_sequence=["#1F4E79", "#3B82F6"],
    template="plotly_dark"
)

    st.plotly_chart(pie, use_container_width=True)

    # Bar Chart
    bar = px.histogram(
    map_data,
    x="Drought_Prediction",
    title="Prediction Count",
    color="Drought_Prediction",
    color_discrete_sequence=["#1F4E79", "#3B82F6"],
    template="plotly_dark"
)

    st.plotly_chart(bar, use_container_width=True)
st.dataframe(
    map_data[
        [
            "grid_id",
            "drought_level",
            "target_spi3",
            "T2M_mean",
            "precip_accum",
            "RH2M_mean"
        ]
    ],
    use_container_width=True
)