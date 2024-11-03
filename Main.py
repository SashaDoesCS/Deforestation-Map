# created with the help of chatGPT 4o
# Creator notes: This program was created and tested on Windows 11 only, keep in mind
# Before running. On run there will be a loading bar via the terminal, allow about 10-20 seconds
# to load the visualization, and some latency is expected for rotating the globe
# Make sure your target processed folder is listed correctly, double check names matching if error occurs
# Please follow instructions listed in the readme before runtime
import os
import rasterio
import numpy as np
import pandas as pd
from tqdm import tqdm
from dash import dcc, html, Dash
from dash.dependencies import Input, Output, State
import plotly.graph_objs as go
from collections import defaultdict
from click_handlers import ClickHandler
from search_system import BinaryTileSearch  # To switch between search_system and
# search_systemtimsort remove or add the timsort to the end of the import, and make sure
# and that search_system and search_systemtimsort are in the same directory

# Path to the processed GeoTIFF folder. If you want to load in a different data set, follow
# Instructions listed on processData and keep in mind the size and time, it is not recommended
# To change the dataset given
processed_folder = 'procesed20'

# Initialize a hash table to store lat, lon, canopy level, gain, loss, and loss year
geo_hash_table = defaultdict(lambda: {"canopy_level": None, "gain": None, "loss": None, "loss_year": None})


def load_geotiffs_with_coordinates(folder):
    """
    Load GeoTIFF files from the processed folder and its subfolders,
    and calculate geographic coordinates for each pixel.
    handles any errors encountered during file loading.
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
            # Process each file type (processing code remains the same...)
            # [Previous file processing code remains unchanged]
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
                        mask = values != 0

                        for lat, lon, value in zip(lats[mask], lons[mask], values[mask]):
                            coord = (float(lat), float(lon))
                            temp_data[coord]['canopy_level'] = float(value)
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

        return pd.DataFrame(geotiff_data, columns=['lat', 'lon', 'canopy_level', 'gain', 'loss', 'loss_year'])
    except Exception as e:
        print(f"Error loading GeoTIFF files: {e}")
        return pd.DataFrame()


def create_visualization(df, search_results=None):
    """
    Create a Plotly globe visualization for the given DataFrame.
    Optionally highlight search results if provided.
    """
    try:
        df_sample = df.sample(n=500000) if len(df) > 500000 else df

        # Base visualization
        base_scatter = go.Scattergeo(
            lon=df_sample['lon'],
            lat=df_sample['lat'],
            text=[
                f'Canopy: {c:.1f}%<br>Gain: {"Yes" if g else "No"}<br>Loss: {"Yes" if l else "No"}<br>Loss Year: {2000 + ly if l else "N/A"}'
                for c, g, l, ly in
                zip(df_sample['canopy_level'], df_sample['gain'], df_sample['loss'], df_sample['loss_year'])
            ],
            mode='markers',
            marker=dict(
                size=2,
                opacity=0.6,
                color=df_sample['canopy_level'],
                colorscale='Viridis',
                showscale=True,
                colorbar=dict(title='Canopy Level (%)')
            ),
            hoverinfo='text',
            name=' '
        )

        data = [base_scatter]

        # Add search results if provided
        if search_results is not None and not search_results.empty:
            search_scatter = go.Scattergeo(
                lon=search_results['lon'],
                lat=search_results['lat'],
                text=[
                    f'Canopy: {c:.1f}%<br>Gain: {"Yes" if g else "No"}<br>Loss: {"Yes" if l else "No"}<br>Loss Year: {2000 + ly if l else "N/A"}'
                    for c, g, l, ly in
                    zip(search_results['canopy_level'], search_results['gain'], search_results['loss'],
                        search_results['loss_year'])
                ],
                mode='markers',
                marker=dict(
                    size=4,
                    opacity=1.0,
                    color='red',
                ),
                hoverinfo='text',
                name=' '
            )
            data.append(search_scatter)

        return {
            'data': data,
            'layout': go.Layout(
                title='Tree Canopy Visualization',
                geo=dict(
                    projection_type='orthographic',
                    center=dict(lon=-78, lat=22),
                    projection=dict(rotation=dict(lon=-78, lat=22, roll=0)),  # To change starting location, change
                    # to desired coordinates
                    showland=True,
                    landcolor='rgb(250, 250, 250)',
                    showocean=True,
                    oceancolor='rgb(220, 220, 220)',
                    coastlinecolor='rgb(100, 100, 100)',
                ),
                height=600,
                margin=dict(l=0, r=0, b=0, t=30),
                showlegend=True
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

    # Initialize the search system
    tile_search = BinaryTileSearch(df)
    click_handler = ClickHandler()

    app = Dash(__name__)
    app.layout = html.Div([
        html.H1("Tree Canopy Visualization and Search"),

        # Search controls
        html.Div([
            html.H3("Search Filters"),
            html.Div([
                html.Label("Minimum Canopy Level (%) - Will not search if min > max"),
                dcc.Input(id='min-canopy', type='number', value=None, min=0, max=100),

                html.Label("Maximum Canopy Level (%) - Will not search if min > max"),
                dcc.Input(id='max-canopy', type='number', value=None, min=0, max=100),

                html.Label("Minimum Loss Year - Will not search if min > max"),
                dcc.Input(id='min-loss-year', type='number', value=None, min=2000, max=2014),

                html.Label("Maximum Loss Year - Will not search if min > max"),
                dcc.Input(id='max-loss-year', type='number', value=None, min=2000, max=2014),

                html.Label("Has Gain"),
                dcc.Dropdown(
                    id='has-gain',
                    options=[
                        {'label': 'Any', 'value': 'any'},
                        {'label': 'Yes', 'value': 'true'},
                        {'label': 'No', 'value': 'false'}
                    ],
                    value='any'
                ),

                html.Label("Has Loss"),
                dcc.Dropdown(
                    id='has-loss',
                    options=[
                        {'label': 'Any', 'value': 'any'},
                        {'label': 'Yes', 'value': 'true'},
                        {'label': 'No', 'value': 'false'}
                    ],
                    value='any'
                ),
                html.Button('Search', id='search-button', n_clicks=0)
            ], style={'display': 'flex', 'flexDirection': 'column', 'gap': '10px', 'padding': '20px'})
        ]),

        # Visualization
        dcc.Graph(id='globe-graph'),

        # Results and analysis
        html.Div([
            html.Div(id='search-results-summary'),
            html.Div(id='click-data'),
            html.Div(id='area-analysis'),
            html.Div(id='tile-queue'),
            html.Div(id='average-log'),
            html.Div(id='full-log')
        ]),

        # Store components for data
        dcc.Store(id='geotiff-data'),
        dcc.Store(id='search-results-data')
    ])

    @app.callback(
        [Output('search-results-data', 'data'),
         Output('search-results-summary', 'children')],
        [Input('search-button', 'n_clicks')],
        [State('min-canopy', 'value'),
         State('max-canopy', 'value'),
         State('min-loss-year', 'value'),
         State('max-loss-year', 'value'),
         State('has-gain', 'value'),
         State('has-loss', 'value')]
    )
    def perform_search(n_clicks, min_canopy, max_canopy, min_loss_year, max_loss_year, has_gain, has_loss):
        if n_clicks == 0:
            return None, "No search performed yet"

        # Convert string values back to appropriate types
        has_gain = None if has_gain == 'any' else (has_gain == 'true')
        has_loss = None if has_loss == 'any' else (has_loss == 'true')

        criteria = {
            'min_canopy': min_canopy,
            'max_canopy': max_canopy,
            'min_loss_year': min_loss_year,
            'max_loss_year': max_loss_year,
            'has_gain': has_gain,
            'has_loss': has_loss
        }

        results = tile_search.search(criteria)
        results_df = results.to_dataframe()

        summary = f"Found {len(results_df)} matching tiles"

        return results_df.to_dict('records'), summary

    @app.callback(
        Output('globe-graph', 'figure'),
        [Input('geotiff-data', 'data'),
         Input('search-results-data', 'data')]
    )
    def update_graph(data, search_results):
        try:
            if data is None:
                return go.Figure()

            df = pd.DataFrame(data)
            search_df = pd.DataFrame(search_results) if search_results is not None else None

            return create_visualization(df, search_df)
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

    print("Data processing complete. Starting Dash server...")
    app.run_server(debug=False) # Optionally you can turn on debug, not recommended due to double load. caution adding a
    # host, make sure you know what running on a host does before proceeding in doing so


if __name__ == "__main__":
    main()
