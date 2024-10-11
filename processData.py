import os
import time
import rasterio
from rasterio.enums import Resampling
from concurrent.futures import ThreadPoolExecutor
import plotly.graph_objs as go
import pickle  # For caching
import hashlib  # For creating a unique cache file
import tkinter as tk
from tkinter import ttk
import threading

# Cache directory
CACHE_DIR = 'cache/'

# Ensure cache directory exists
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)


# Step 1: Process GeoTIFF files and apply downscaling
def process_geotiff_in_chunks(tiff_path, downscale_to=(1000, 1000)):
    cache_file = get_cache_filename(tiff_path)

    # Check if the file has already been processed (cached)
    if os.path.exists(cache_file):
        return

    # If not cached, process the file
    try:
        with rasterio.open(tiff_path) as dataset:
            num_layers = dataset.count
            layers = []

            # Calculate resampling scale factor
            for i in range(1, num_layers + 1):
                # Downscale the entire image
                layer = dataset.read(
                    i,
                    out_shape=(downscale_to[1], downscale_to[0]),
                    resampling=Resampling.bilinear
                )
                layers.append(layer)

            # Cache the processed data
            with open(cache_file, 'wb') as f:
                pickle.dump(layers, f)
    except Exception as e:
        print(f"Error processing {tiff_path}: {e}")


# Generate a unique cache filename based on the file's path
def get_cache_filename(tiff_path):
    filename_hash = hashlib.md5(tiff_path.encode('utf-8')).hexdigest()
    return os.path.join(CACHE_DIR, f"{filename_hash}.pkl")


# Step 2: Create the tkinter GUI
class ProcessingApp:
    def __init__(self, root, output_dir, downscale_to=(1000, 1000)):
        self.root = root
        self.output_dir = output_dir
        self.downscale_to = downscale_to

        self.tiff_files = [f for f in os.listdir(output_dir) if f.endswith(".tif")]
        self.total_files = len(self.tiff_files)

        self.processed_files = 0
        self.total_size = 0
        self.start_time = None

        # Create the progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(root, variable=self.progress_var, maximum=self.total_files, length=400)
        self.progress_bar.pack(pady=20)

        # Create the labels for storage and time
        self.storage_label = tk.Label(root, text="Estimated Storage: 0 MB")
        self.storage_label.pack(pady=5)

        self.time_label = tk.Label(root, text="Estimated Time Remaining: Calculating...")
        self.time_label.pack(pady=5)

        # Start processing in a new thread to avoid freezing the GUI
        threading.Thread(target=self.start_processing).start()

    def start_processing(self):
        self.start_time = time.time()

        with ThreadPoolExecutor() as executor:
            for filename in self.tiff_files:
                executor.submit(self.process_file, filename)

        # Once all files are processed, the program will display a message and exit
        self.progress_var.set(self.total_files)
        self.update_storage_and_time()
        tk.Label(self.root, text="Processing complete!").pack(pady=20)
        self.root.quit()  # Exit the application

    def process_file(self, filename):
        file_path = os.path.join(self.output_dir, filename)

        # Measure the initial size for storage estimation
        initial_size = os.path.getsize(file_path)

        # Process the file
        process_geotiff_in_chunks(file_path, self.downscale_to)

        # Measure the final size for storage estimation
        final_size = os.path.getsize(get_cache_filename(file_path))

        # Update progress and storage estimate
        self.processed_files += 1
        self.total_size += final_size
        self.progress_var.set(self.processed_files)

        # Update the storage and time estimates in the UI
        self.update_storage_and_time()

    def update_storage_and_time(self):
        # Update storage label
        estimated_storage = self.total_size / (1024 * 1024)  # Convert to MB
        self.storage_label.config(text=f"Estimated Storage: {estimated_storage:.2f} MB")

        # Update time remaining label
        elapsed_time = time.time() - self.start_time
        avg_time_per_file = elapsed_time / self.processed_files if self.processed_files > 0 else 0
        time_remaining = avg_time_per_file * (self.total_files - self.processed_files)
        self.time_label.config(text=f"Estimated Time Remaining: {time_remaining:.2f} seconds")


# Main function to start the application
def run_processing_app(output_dir, downscale_to=(1000, 1000)):
    root = tk.Tk()
    root.title("GeoTIFF Processing with Progress")
    root.geometry("500x300")

    app = ProcessingApp(root, output_dir, downscale_to)

    root.mainloop()


# Example usage: process and display progress for all files
output_dir = r"C:\Users\s\Downloads\Deforestation Risk Application"  # Updated directory path
downscale_to = (1000, 1000)  # Downscale resolution to 1000x1000

run_processing_app(output_dir, downscale_to)
