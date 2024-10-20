import os
import rasterio
from rasterio.enums import Resampling
import numpy as np
from tqdm import tqdm  # Progress bar for processing


# Step 1: Process GeoTIFF files (downsample and save to final folder)
def process_geotiff(file_path):
    # Open the GeoTIFF file
    with rasterio.open(file_path) as src:
        data = src.read()
        metadata = src.meta

    print(f"Processing {file_path}...")
    print(f"Shape: {data.shape}")
    print(f"Data type: {data.dtype}")
    print(f"Min value: {np.min(data)}")
    print(f"Max value: {np.max(data)}")
    print(f"Mean value: {np.mean(data)}")

    return metadata


# Step 2: Resize GeoTIFF file while preserving metadata
def resize_geotiff(input_path, output_path, target_size=(400, 400)):
    with rasterio.open(input_path) as src:
        # Calculate the scaling factors
        scale_factor_width = src.width / target_size[0]
        scale_factor_height = src.height / target_size[1]

        # Create a new transform for the resized raster
        new_transform = src.transform * src.transform.scale(scale_factor_width, scale_factor_height)

        # Resample data to target shape
        data = src.read(
            out_shape=(src.count, target_size[1], target_size[0]),  # Resize to target_size
            resampling=Resampling.nearest  # Use nearest-neighbor resampling
        )

        # Update metadata (preserving all relevant metadata)
        out_meta = src.meta.copy()
        out_meta.update({
            "driver": "GTiff",
            "height": target_size[1],
            "width": target_size[0],
            "transform": new_transform,
            "crs": src.crs,  # Ensure CRS is preserved
            "dtype": src.dtypes[0],  # Keep data type unchanged
            "count": src.count  # Preserve band count
        })

        # Write the resized raster while keeping metadata intact
        with rasterio.open(output_path, "w", **out_meta) as dest:
            dest.write(data)


# Step 3: Organize and process GeoTIFF files from 'processed' folder
def organize_and_process(file_path, processed_folder, final_folder, target_size=(1000, 1000)):
    # Extract coordinates from the file name
    filename = os.path.basename(file_path)
    coords = filename.split('_')[-2:]  # e.g., "40N_080W"
    coord_folder = '_'.join(coords).replace(".tif", "")

    # Create directory for processed files
    output_dir = os.path.join(final_folder, coord_folder)
    os.makedirs(output_dir, exist_ok=True)

    # Resize and process
    output_path = os.path.join(output_dir, filename)
    resize_geotiff(file_path, output_path, target_size)

    # Process file and print metadata
    metadata = process_geotiff(output_path)
    print(f"Metadata for {output_path}: {metadata}")


# Step 4: Main function to handle all files in the processed folder
def main():
    processed_folder = "processed"
    final_folder = "final_processed"
    os.makedirs(final_folder, exist_ok=True)

    # Loop through all GeoTIFF files in the processed folder
    for root, dirs, files in os.walk(processed_folder):
        for file in files:
            if file.endswith('.tif'):
                file_path = os.path.join(root, file)
                organize_and_process(file_path, processed_folder, final_folder)


if __name__ == "__main__":
    main()
