import xarray as xr
import rioxarray
import geopandas as gpd

# 1. The OPeNDAP URL for the ensemble evaporation change
url = "https://thredds.met.no/thredds/dodsC/KSS/Klima_i_Norge/utgave2025/ClimateStatistics/change-evap/ensemble-mean_rcp45_both-bc-estobs_disthbv_norway_1km_change-evap.nc"

# 2. Load and prepare catchment shapefile
catchment = gpd.read_file("_ags_data_ExampleCatchment/NedbfeltF_v4.shp") #change to catchment name
if catchment.crs != "EPSG:25833":
    catchment = catchment.to_crs("EPSG:25833")

print("Connecting to KSS THREDDS server...")
# 3. Open the dataset
ds = xr.open_dataset(url)
ds.rio.write_crs("EPSG:25833", inplace=True)

print("Clipping data to ExampleCatchment...") #change to catchment name
# 4. Clip to polygon
clipped = ds.rio.clip(catchment.geometry, catchment.crs, drop=True)

# 5. Average the data across the X and Y spatial dimensions
mean_change = clipped.mean(dim=['Xc', 'Yc'], skipna=True).to_dataframe()

print("\n--- Evaporation change for ExampleCatchment ---") #change to catchment name

if 'spatial_ref' in mean_change.columns:
    mean_change = mean_change.drop(columns=['spatial_ref'])

print(mean_change.dropna())