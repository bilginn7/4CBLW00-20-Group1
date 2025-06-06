import geopandas as gpd
import matplotlib.pyplot as plt

# Paths to GeoPackage files
lsoa_gpkg_path = "data/geo/london_lsoa.gpkg"
ward_gpkg_path = "data/geo/london_ward.gpkg"
borough_gpkg_path = "data/geo/london_borough.gpkg"

# Load GeoPackages
gdf_lsoa = gpd.read_file(lsoa_gpkg_path)
gdf_ward = gpd.read_file(ward_gpkg_path)
gdf_borough = gpd.read_file(borough_gpkg_path)

# Print basic information for each layer
print("=== LSOA GeoPackage ===")
print(f"CRS: {gdf_lsoa.crs}")
print(f"Number of LSOAs: {len(gdf_lsoa)}")
print("Columns:", gdf_lsoa.columns.tolist())
print("Head:\n", gdf_lsoa.head(), "\n")

print("=== Ward GeoPackage ===")
print(f"CRS: {gdf_ward.crs}")
print(f"Number of Wards: {len(gdf_ward)}")
print("Columns:", gdf_ward.columns.tolist())
print("Head:\n", gdf_ward.head(), "\n")

print("=== Borough GeoPackage ===")
print(f"CRS: {gdf_borough.crs}")
print(f"Number of Boroughs: {len(gdf_borough)}")
print("Columns:", gdf_borough.columns.tolist())
print("Head:\n", gdf_borough.head(), "\n")

# Convert multipart to singlepart for plotting
gdf_lsoa_single = gdf_lsoa.explode(ignore_index=True)
gdf_ward_single = gdf_ward.explode(ignore_index=True)
gdf_borough_single = gdf_borough.explode(ignore_index=True)

# Plot the boundaries to visualize
fig, axes = plt.subplots(1, 3, figsize=(18, 6))

gdf_lsoa_single.boundary.plot(ax=axes[0], linewidth=0.2, edgecolor='black')
axes[0].set_title("LSOA Boundaries")
axes[0].axis('off')

gdf_ward_single.boundary.plot(ax=axes[1], linewidth=0.5, edgecolor='blue')
axes[1].set_title("Ward Boundaries")
axes[1].axis('off')

gdf_borough_single.boundary.plot(ax=axes[2], linewidth=1.0, edgecolor='red')
axes[2].set_title("Borough Boundaries")
axes[2].axis('off')

plt.tight_layout()
plt.show()
