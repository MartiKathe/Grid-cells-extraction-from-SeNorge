import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import requests
import io
import re
import numpy as np

# 1. Load shapefile directly from the ZIP archive. If the shapefile is downloaded from a catchment created in NEVINA,
# it is typically found inside a folder containing 8 elements all with name Nedbfelt_v4.

# here the shapefile and relative files were all saved inside a folder named _ags_data_ExampleCatchment
zip_path = "_ags_data_ExampleCatchment/NedbfeltF_v4.shp"  #change to zip path
catchment = gpd.read_file(zip_path)

# Ensure the coordinate reference system (CRS) is UTM 33N (EPSG:25833).
# SeNorge/Norgeskart uses meters in this specific projection.
# should not be needed as in the zip folder it is specified that: Koordinatsystem EUREF89/WGS84, UTM 33
if catchment.crs != "EPSG:25833":
    catchment = catchment.to_crs("EPSG:25833")

# 2. Generate a 1x1 km grid over the catchment bounding box
minx, miny, maxx, maxy = catchment.total_bounds

# SeNorge grid cell centers typically end in 500. We generate points every 1000m.
x_coords = np.arange(np.floor(minx / 1000) * 1000 + 500, maxx, 1000)
y_coords = np.arange(np.floor(miny / 1000) * 1000 + 500, maxy, 1000)

# Create point geometries for each grid cell center
points = [Point(x, y) for x in x_coords for y in y_coords]
grid_gdf = gpd.GeoDataFrame(geometry=points, crs="EPSG:25833")

# 3. Filter points to only those inside the catchment
# A spatial join checks which grid points intersect the catchment polygon
cells_in_catchment = gpd.sjoin(grid_gdf, catchment, predicate='intersects')

print(f"Found {len(cells_in_catchment)} grid cells intersecting the catchment area.")

# 4. API connection
# adapt this to relevant dates
# if not working, check if the API url needs to be updated

start_date = "1971-01-01"
end_date = "2000-12-31"
base_url = "https://gts.nve.no/api/GridTimeSeries"

precip_list = []
temp_list = []
altitudes = []

print("Fetching data from SeNorge API...")

# 5. Fetch and process data
for idx, row in cells_in_catchment.iterrows():
    # Extract integer coordinates from the geometry
    x = int(row.geometry.x)
    y = int(row.geometry.y)

    # API URLs
    url_rr = f"{base_url}/{x}/{y}/{start_date}/{end_date}/rr.csv"
    url_tm = f"{base_url}/{x}/{y}/{start_date}/{end_date}/tm.csv"

    resp_rr = requests.get(url_rr)
    resp_tm = requests.get(url_tm)

    if resp_rr.status_code == 200 and resp_tm.status_code == 200:
        lines_rr = resp_rr.text.strip().split('\n')
        lines_tm = resp_tm.text.strip().split('\n')

        # Extract altitude via regex from the metadata row
        alt_match = re.search(r'Altitude:\s*([-\d.]+)', lines_rr[0])
        if alt_match:
            altitudes.append(float(alt_match.group(1)))

        # Process precipitation (rr)
        df_rr = pd.read_csv(io.StringIO('\n'.join(lines_rr[1:])), sep=';')
        df_rr.columns = df_rr.columns.str.strip()
        rr_col = df_rr.columns[1]
        df_rr[rr_col] = df_rr[rr_col].replace(65535, np.nan)  # Handle NoData
        df_rr = df_rr.set_index('Date')
        precip_list.append(df_rr[rr_col].rename(f'rr_{x}_{y}'))

        # Process temperature (tm)
        df_tm = pd.read_csv(io.StringIO('\n'.join(lines_tm[1:])), sep=';')
        df_tm.columns = df_tm.columns.str.strip()
        tm_col = df_tm.columns[1]
        df_tm[tm_col] = df_tm[tm_col].replace(65535, np.nan)
        df_tm = df_tm.set_index('Date')
        temp_list.append(df_tm[tm_col].rename(f'tm_{x}_{y}'))
    else:
        print(f"Failed to fetch data for coordinate: ({x}, {y}) - Status: {resp_rr.status_code}")

print("Data extraction complete. Calculating averages...")

# 6. Calculate area averages
all_precip = pd.concat(precip_list, axis=1)
all_temp = pd.concat(temp_list, axis=1)

avg_precip = all_precip.mean(axis=1, skipna=True)
avg_temp = all_temp.mean(axis=1, skipna=True)
avg_altitude = sum(altitudes) / len(altitudes) if altitudes else np.nan

# Compile final average series
final_df = pd.DataFrame({
    'Average_Precipitation_mm': avg_precip,
    'Average_Temperature_C': avg_temp
})

final_df.index = pd.to_datetime(final_df.index, format='%d.%m.%Y %H:%M:%S', errors='coerce')

print("\n--- Final Catchment Results ---")
print(f"Average Catchment Altitude: {avg_altitude:.1f} meters")
print(final_df.head())

# 7. Exporting to SeNorge format: CSVs

# Extract exact start and end dates from the index for the header
start_str = final_df.index[0].strftime('%d.%m.%Y %H:%M:%S')
end_str = final_df.index[-1].strftime('%d.%m.%Y %H:%M:%S')

# Round the average altitude to a whole number for the header
alt_str = str(int(round(avg_altitude))) if pd.notna(avg_altitude) else "NaN"

# Rebuild the custom metadata headers (removing X and Y, inserting average altitude)
header_rr = f"# Theme: rr; Fullname: Døgnnedbør; NoDataValue: 65535; Startdate: {start_str}; Enddate: {end_str}; PrognoseStartDate: ; Unit: mm; TimeResolution: 1440; Altitude: {alt_str};\n"
header_tm = f"# Theme: tm; Fullname: Døgntemperatur; NoDataValue: 65535; Startdate: {start_str}; Enddate: {end_str}; PrognoseStartDate: ; Unit: Celcius; TimeResolution: 1440; Altitude: {alt_str};\n"

# Prepare precipitation dataframe for export
df_export_rr = final_df[['Average_Precipitation_mm']].copy()
df_export_rr.index = df_export_rr.index.strftime('%d.%m.%Y %H:%M:%S')
df_export_rr.columns = ['rr(mm)']

# Prepare temperature dataframe for export
df_export_tm = final_df[['Average_Temperature_C']].copy()
df_export_tm.index = df_export_tm.index.strftime('%d.%m.%Y %H:%M:%S')
df_export_tm.columns = ['tm(Celcius)']

# Write precipitation CSV
with open("ExampleCatchment daily precipitation grid cells.csv", "w", encoding="utf-8") as f_rr:  #change ExampleCatchment to catchment name
    f_rr.write(header_rr)
    # float_format='%.1f' ensures numbers look like -0.2 instead of -0.20000000000000004
    df_export_rr.to_csv(f_rr, sep=';', index_label='Date', float_format='%.1f')

# Write temperature CSV
with open("ExampleCatchment daily temperature grid cells.csv", "w", encoding="utf-8") as f_tm:  #change ExampleCatchment to catchment name
    f_tm.write(header_tm)
    df_export_tm.to_csv(f_tm, sep=';', index_label='Date', float_format='%.1f')

print(
    "Successfully saved 'ExampleCatchment daily precipitation grid cells.csv' and 'ExampleCatchment daily temperature grid cells.csv'!")  #change ExampleCatchment to catchment name

# clean blank spaces
# The two files just generated

files_to_clean = [
    "ExampleCatchment daily precipitation grid cells.csv",  #change ExampleCatchment to catchment name
    "ExampleCatchment daily temperature grid cells.csv"  #change ExampleCatchment to catchment name
]

for file_path in files_to_clean:
    # Read all lines from the current file
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Open the file again in 'write' mode to overwrite it
    with open(file_path, 'w', encoding='utf-8', newline='') as f:
        for line in lines:
            # .strip() removes invisible spaces. If the line has actual text, it writes it.
            if line.strip():
                f.write(line)

print("Blank lines successfully removed from both files")
