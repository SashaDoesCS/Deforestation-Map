import os
import rasterio
import numpy as np
import pandas as pd
from tqdm import tqdm
from dash import dcc, html, Dash
from dash.dependencies import Input, Output
import plotly.graph_objs as go
from collections import defaultdict
from click_handlers import ClickHandler

# Path to the processed GeoTIFF folder
processed_folder = 'processed20'

# Initialize a hash table to store lat, lon, canopy level, gain, loss, and loss year
geo_hash_table = defaultdict(lambda: {"canopy_level": None, "gain": None, "loss": None, "loss_year": None})

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

        # Initialize dictionary to store data for each coordinate
        temp_data = defaultdict(dict)
        geotiff_data = []  # List to store data for DataFrame

        # Group files by type
        file_groups = {
            'canopy': [f for f in file_list if 'treecover2000_' in f],
            'gain': [f for f in file_list if 'gain_' in f],
            'loss': [f for f in file_list if 'loss_' in f and 'lossyear_' not in f],
            'loss_year': [f for f in file_list if 'lossyear_' in f]
        }

        # Process each file type
        total_files = len(file_list)
        with tqdm(total=total_files, desc="Processing files", unit="file") as pbar:
            # First process canopy files to establish the base coordinates
            for file_path in file_groups['canopy']:
                try:
                    with rasterio.open(file_path) as dataset:
                        data = dataset.read(1)
                        transform = dataset.transform
                        rows, cols = np.indices(data.shape)
                        lons, lats = rasterio.transform.xy(transform, rows, cols)
                        lats = np.array(lats).flatten()
                        lons = np.array(lons).flatten()
                        values = data.flatten()
                        mask = values != 0  # Exclude no-data values

                        # Store canopy values with their coordinates
                        for lat, lon, value in zip(lats[mask], lons[mask], values[mask]):
                            coord = (float(lat), float(lon))
                            temp_data[coord]['canopy_level'] = float(value)
                            # Initialize other values with defaults
                            temp_data[coord]['gain'] = 0
                            temp_data[coord]['loss'] = 0
                            temp_data[coord]['loss_year'] = 0
                    pbar.update(1)
                except Exception as e:
                    print(f"Error processing canopy file {file_path}: {str(e)}")
                    continue

            # Process gain files
            for file_path in file_groups['gain']:
                try:
                    with rasterio.open(file_path) as dataset:
                        data = dataset.read(1)
                        transform = dataset.transform
                        rows, cols = np.indices(data.shape)
                        lons, lats = rasterio.transform.xy(transform, rows, cols)
                        lats = np.array(lats).flatten()
                        lons = np.array(lons).flatten()
                        values = data.flatten()
                        mask = values != 0

                        # Update gain values for existing coordinates
                        for lat, lon, value in zip(lats[mask], lons[mask], values[mask]):
                            coord = (float(lat), float(lon))
                            if coord in temp_data:
                                temp_data[coord]['gain'] = int(value)
                    pbar.update(1)
                except Exception as e:
                    print(f"Error processing gain file {file_path}: {str(e)}")
                    continue

            # Process loss files
            for file_path in file_groups['loss']:
                try:
                    with rasterio.open(file_path) as dataset:
                        data = dataset.read(1)
                        transform = dataset.transform
                        rows, cols = np.indices(data.shape)
                        lons, lats = rasterio.transform.xy(transform, rows, cols)
                        lats = np.array(lats).flatten()
                        lons = np.array(lons).flatten()
                        values = data.flatten()
                        mask = values != 0

                        # Update loss values for existing coordinates
                        for lat, lon, value in zip(lats[mask], lons[mask], values[mask]):
                            coord = (float(lat), float(lon))
                            if coord in temp_data:
                                temp_data[coord]['loss'] = int(value)
                    pbar.update(1)
                except Exception as e:
                    print(f"Error processing loss file {file_path}: {str(e)}")
                    continue

            # Process loss year files
            for file_path in file_groups['loss_year']:
                try:
                    with rasterio.open(file_path) as dataset:
                        data = dataset.read(1)
                        transform = dataset.transform
                        rows, cols = np.indices(data.shape)
                        lons, lats = rasterio.transform.xy(transform, rows, cols)
                        lats = np.array(lats).flatten()
                        lons = np.array(lons).flatten()
                        values = data.flatten()
                        mask = values != 0

                        # Update loss year values for existing coordinates
                        for lat, lon, value in zip(lats[mask], lons[mask], values[mask]):
                            coord = (float(lat), float(lon))
                            if coord in temp_data:
                                temp_data[coord]['loss_year'] = int(value)
                    pbar.update(1)
                except Exception as e:
                    print(f"Error processing loss year file {file_path}: {str(e)}")
                    continue

        # Convert temporary data to list of tuples for DataFrame
        for (lat, lon), data in temp_data.items():
            geotiff_data.append((
                lat,
                lon,
                data['canopy_level'],
                data['gain'],
                data['loss'],
                data['loss_year']
            ))

        # Create and return DataFrame
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

def main():
    # Load processed GeoTIFFs without downsampling from all subdirectories
    df = load_geotiffs_with_coordinates(processed_folder)
    if df.empty:
        print("Error: Failed to load GeoTIFF data.")
        return

    print("Data processing complete. Starting Dash server...")

    # Initialize the ClickHandler
    click_handler = ClickHandler()

    app = Dash(__name__)
    app.layout = html.Div([
        html.H1("Tree Canopy Visualization"),
        dcc.Graph(id='globe-graph'),
        html.Div(id='click-data'),
        html.Div(id='area-analysis'),
        html.Div(id='tile-queue'),
        html.Div(id='average-log'),
        html.Div(id='full-log'),
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
         Output('area-analysis', 'children'),
         Output('tile-queue', 'children'),
         Output('average-log', 'children'),
         Output('full-log', 'children')],
        Input('globe-graph', 'clickData')
    )
    def handle_click(clickData):
        try:
            response = click_handler.handle_click(clickData, df)
            return (
                response['click_data'],
                response['area_analysis'],
                response['queue_display'],
                response['average_log'],
                response['full_log']
            )
        except Exception as e:
            print(f"Error in click callback: {e}")
            return ("Error processing click", "Error in area analysis",
                   "Error in queue display", "Error in average log", "Error in full log")

    app.run_server(debug=True)

if __name__ == "__main__":
    main()
