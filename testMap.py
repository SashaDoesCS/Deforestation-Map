import os
import rasterio
import numpy as np
import pandas as pd
from tqdm import tqdm
from dash import dcc, html, Dash
from dash.dependencies import Input, Output
import plotly.graph_objs as go
from collections import deque, defaultdict

# Path to the processed GeoTIFF folder
processed_folder = 'processed20'

# Initialize a hash table to store lat, lon, canopy level, gain, loss, and loss year
geo_hash_table = defaultdict(lambda: {"canopy_level": None, "gain": None, "loss": None, "loss_year": None})

# Initialize a queue to store up to 3 unique tiles with all their data
tile_queue = deque(maxlen=3)

# Initialize a list to store the log of all points clicked and their data
click_log = []


def load_geotiffs_with_coordinates(folder):
    """
    Load GeoTIFF files from the processed folder and its subfolders,
    and calculate geographic coordinates for each pixel.
    Gracefully handles any errors encountered during file loading.
    """
    try:
        geotiff_data = []

        # Recursively search for all .tif files in the folder and subfolders
        file_list = []
        for root, dirs, files in os.walk(folder):
            for file in files:
                if file.endswith('.tif'):
                    file_list.append(os.path.join(root, file))

        total_files = len(file_list)

        if total_files == 0:
            raise FileNotFoundError(f"Found {total_files} GeoTIFF files. Please check the folder structure.")

        print(f"Found {total_files} GeoTIFF files. Loading without downsampling...")

        with tqdm(total=total_files, desc="Loading files", unit="file") as pbar:
            for file_path in file_list:
                try:
                    with rasterio.open(file_path) as dataset:
                        # Read all bands
                        data = dataset.read(1)  # Canopy
                        gain_data = dataset.read(2) if dataset.count >= 2 else np.zeros_like(data)
                        loss_data = dataset.read(3) if dataset.count >= 3 else np.zeros_like(data)
                        loss_year_data = dataset.read(4) if dataset.count >= 4 else np.zeros_like(data)

                        transform = dataset.transform
                        rows, cols = np.indices(data.shape)
                        lons, lats = rasterio.transform.xy(transform, rows, cols)

                        lats = np.array(lats).flatten()
                        lons = np.array(lons).flatten()
                        values = data.flatten()
                        gain_values = gain_data.flatten()
                        loss_values = loss_data.flatten()
                        loss_year_values = loss_year_data.flatten()

                        mask = values != 0  # Exclude no-data values
                        lats = lats[mask]
                        lons = lons[mask]
                        values = values[mask]
                        gain_values = gain_values[mask]
                        loss_values = loss_values[mask]
                        loss_year_values = loss_year_values[mask]

                        geotiff_data.extend(zip(lats, lons, values, gain_values, loss_values, loss_year_values))

                        # Store all values in the hash table
                        for lat, lon, value, gain, loss, loss_year in zip(lats, lons, values, gain_values, loss_values,
                                                                          loss_year_values):
                            geo_hash_table[(float(lat), float(lon))] = {
                                "canopy_level": float(value),
                                "gain": int(gain),
                                "loss": int(loss),
                                "loss_year": int(loss_year)
                            }

                except rasterio.errors.RasterioIOError as e:
                    print(f"Error reading file {file_path}: {e}")
                except Exception as e:
                    print(f"Unexpected error in file {file_path}: {e}")
                finally:
                    pbar.update(1)

        print("GeoTIFF files loaded successfully.")
        return pd.DataFrame(geotiff_data, columns=['lat', 'lon', 'canopy_level', 'gain', 'loss', 'loss_year'])

    except FileNotFoundError as fnf_error:
        print(f"File not found: {fnf_error}")
    except Exception as e:
        print(f"Error loading GeoTIFF files: {e}")
    return pd.DataFrame()


def create_visualization(df):
    """
    Create a Plotly globe visualization for the given DataFrame.
    """
    try:
        df_sample = df.sample(n=500000) if len(df) > 500000 else df

        return {
            'data': [go.Scattergeo(
                lon=df_sample['lon'],
                lat=df_sample['lat'],
                text=[
                    f'Canopy: {c:.1f}%<br>Gain: {"Yes" if g else "No"}<br>Loss: {"Yes" if l else "No"}<br>Loss Year: {2000 + ly if l else "N/A"}'
                    for c, g, l, ly in
                    zip(df_sample['canopy_level'], df_sample['gain'], df_sample['loss'], df_sample['loss_year'])],
                mode='markers',
                marker=dict(
                    size=2,
                    opacity=0.6,
                    color=df_sample['canopy_level'],
                    colorscale='Viridis',
                    showscale=True,
                    colorbar=dict(title='Canopy Level (%)')
                ),
                hoverinfo='text'
            )],
            'layout': go.Layout(
                title='Tree Canopy Visualization',
                geo=dict(
                    projection_type='orthographic',
                    center=dict(lon=-78, lat=22),
                    projection=dict(rotation=dict(lon=-78, lat=22, roll=0)),
                    showland=True,
                    landcolor='rgb(250, 250, 250)',
                    showocean=True,
                    oceancolor='rgb(220, 220, 220)',
                    coastlinecolor='rgb(100, 100, 100)',
                ),
                height=600,
                margin=dict(l=0, r=0, b=0, t=30)
            )
        }
    except Exception as e:
        print(f"Error creating visualization: {e}")
        return None


def calculate_average_canopy(queue):
    """
    Calculate the average canopy level of the tiles in the queue.
    """
    try:
        if not queue:
            return None

        # Extract only the canopy levels from the tiles in the queue
        canopy_levels = [data["canopy_level"] for _, _, data in queue]
        return sum(canopy_levels) / len(canopy_levels)
    except Exception as e:
        print(f"Error calculating average canopy: {e}")
        return None


def main():
    # Load processed GeoTIFFs without downsampling from all subdirectories
    df = load_geotiffs_with_coordinates(processed_folder)
    if df.empty:
        print("Error: Failed to load GeoTIFF data.")
        return

    print("Data processing complete. Starting Dash server...")

    app = Dash(__name__)
    app.layout = html.Div([
        html.H1("Tree Canopy Visualization"),
        dcc.Graph(id='globe-graph'),
        html.Div(id='click-data', children="Click on a point to see canopy data"),
        html.Div(id='tile-queue', children="Tile queue: Empty"),
        html.Div(id='average-log', children="Average canopy log: None"),
        html.Div(id='full-log', children="Full log: Empty"),
        dcc.Store(id='geotiff-data')
    ])

    @app.callback(
        Output('geotiff-data', 'data'),
        Input('globe-graph', 'id')
    )
    def store_geotiff_data(id):
        try:
            return df.to_dict('records')
        except Exception as e:
            print(f"Error storing GeoTIFF data: {e}")
            return None

    @app.callback(
        Output('globe-graph', 'figure'),
        Input('geotiff-data', 'data')
    )
    def update_graph(data):
        try:
            if data is None:
                return go.Figure()
            df = pd.DataFrame(data)
            return create_visualization(df)
        except Exception as e:
            print(f"Error updating graph: {e}")
            return go.Figure()

    @app.callback(
        [Output('click-data', 'children'),
         Output('tile-queue', 'children'),
         Output('average-log', 'children'),
         Output('full-log', 'children')],
        Input('globe-graph', 'clickData')
    )
    def handle_click(clickData):
        try:
            if clickData is None:
                return "Click on a point to see canopy data", "Tile queue: Empty", "Average canopy log: None", "Full log: Empty"

            lat = clickData['points'][0]['lat']
            lon = clickData['points'][0]['lon']

            # Get data from hash table
            data = geo_hash_table.get((lat, lon))
            if data is None:
                return f"Clicked on: Latitude {lat:.4f}, Longitude {lon:.4f}, Data not available", \
                    f"Tile queue: Empty", "Average canopy log: None", "Full log: Empty"

            # Store the complete tile data in the queue
            tile_queue.append((lat, lon, data))

            # Calculate status string
            status = []
            if data["gain"] == 1:
                status.append("Gain detected")
            if data["loss"] == 1:
                status.append(f"Loss in year {2000 + data['loss_year']}")
            if not status:
                status.append("No change")
            status_str = ", ".join(status)

            # Calculate average canopy
            avg_canopy = calculate_average_canopy(tile_queue)
            average_log = f"Average canopy level of last {len(tile_queue)} points: {avg_canopy:.2f}%" if avg_canopy is not None else "Average canopy log: None"

            # Format current tile queue for display
            queue_display = "Tile queue: " + ", ".join([
                f"({lat:.4f}, {lon:.4f}: {data['canopy_level']:.1f}%)"
                for lat, lon, data in tile_queue
            ])

            # Add to click log
            click_log.append(
                f"Latitude {lat:.4f}, Longitude {lon:.4f}: "
                f"Canopy level {data['canopy_level']:.1f}%, {status_str}"
            )

            return (
                f"Clicked on: Latitude {lat:.4f}, Longitude {lon:.4f}, "
                f"Canopy Level: {data['canopy_level']:.1f}%, {status_str}",
                queue_display,
                average_log,
                "Full log: " + " | ".join(click_log[-5:])  # Show last 5 entries
            )

        except Exception as e:
            print(f"Error handling click event: {e}")
            return "Error occurred on click", "Tile queue: Empty", "Average canopy log: None", "Full log: Empty"

    app.run_server(debug=True)


if __name__ == "__main__":
    main()