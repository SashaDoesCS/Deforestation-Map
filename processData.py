# created with the help of chatGPT 4o
# Warning: To prevent any mishaps, the urldata.txt file is not present in the
# Files given, as the run time for the program several hours long
# If you wish to run this program, you may find the dataset by going to
# https://earthenginepartners.appspot.com/science-2013-global-forest/download_v1.2.html
# This is not a required step to run the program and should only be used if you wish.
# To increase the resolution of the data beyond 20 by 20, however this is not recommended
# due to the increase in lag. For a machine with 32 gigabytes of ram 50 by 50 will run decently
# To download, locate the links to file downloads provided, create a file called urldata.txt
# Copy and paste all links with no empty lines into the urldata, make sure it matches target and run
# Original file sizes can be over 4 gigs, If program is interrupted delete files from download, as those are temporary
# And will sit there if left unattended

import os
import requests
from tqdm import tqdm  # Progress bar for downloads
import rasterio
from rasterio.enums import Resampling
import numpy as np


# Step 1: Download files
def download_file(url, output_folder):
    filename = url.split("/")[-1]
    output_path = os.path.join(output_folder, filename)

    response = requests.get(url, stream=True)
    total_size = int(response.headers.get('content-length', 0))

    with open(output_path, 'wb') as f:
        for data in tqdm(response.iter_content(1024), total=total_size // 1024, unit='KB'):
            f.write(data)

    return output_path


# Step 2: Process GeoTIFF files
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


# Step 3: Resize GeoTIFF file while preserving metadata
def resize_geotiff(input_path, output_path, target_size=(20, 20)):  # change the target size at your own risk
    with rasterio.open(input_path) as src:
        # Calculate the scaling factors
        scale_factor_width = src.width / target_size[0]
        scale_factor_height = src.height / target_size[1]

        # Create a new transform for the resized raster
        new_transform = src.transform * src.transform.scale(scale_factor_width, scale_factor_height)

        # Resample data to target shape
        data = src.read(
            out_shape=(src.count, target_size[1], target_size[0]),
            resampling=Resampling.nearest
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


# Step 4: Organize into folders based on coordinates
def organize_and_process(url, download_folder, processed_folder, target_size=(20, 20)):  # change the target size at
    # your own risk
    # Extract coordinates from the URL (last part before .tif)
    filename = url.split("/")[-1]
    coords = filename.split('_')[-2:]  # e.g., "40N_080W"
    coord_folder = '_'.join(coords).replace(".tif", "")

    # Create directory for processed files
    output_dir = os.path.join(processed_folder, coord_folder)
    os.makedirs(output_dir, exist_ok=True)

    # Download file
    file_path = download_file(url, download_folder)

    # Resize and process
    output_path = os.path.join(output_dir, filename)
    resize_geotiff(file_path, output_path, target_size)

    # Process file and delete the original file
    metadata = process_geotiff(output_path)
    print(f"Metadata for {output_path}: {metadata}")
    os.remove(file_path)


# Step 5: Main function to handle all files in the url list
def main():
    download_folder = "downloads"
    processed_folder = "processed"
    os.makedirs(download_folder, exist_ok=True)
    os.makedirs(processed_folder, exist_ok=True)

    with open('urldata.txt', 'r') as f:
        urls = f.readlines()

    for url in urls:
        url = url.strip()  # Remove any extra whitespace
        organize_and_process(url, download_folder, processed_folder)


if __name__ == "__main__":
    main()
