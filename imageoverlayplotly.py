import os
import rasterio
import numpy as np
import pandas as pd
from tqdm import tqdm
from dash import dcc, html, Dash
from dash.dependencies import Input, Output
import plotly.graph_objs as go

# Path to the processed GeoTIFF folder
processed_folder = 'compressed_processed'


def load_geotiffs_with_coordinates(folder):
    """
    Load GeoTIFF files from the processed folder and its subfolders,
    and calculate geographic coordinates for each pixel.
    """
    geotiff_data = []

    # Recursively search for all .tif files in the folder and subfolders
    file_list = []
    for root, dirs, files in os.walk(folder):
        for file in files:
            if file.endswith('.tif'):
                file_list.append(os.path.join(root, file))

    total_files = len(file_list)

    if total_files == 0:
        print(f"Found {total_files} GeoTIFF files. Please check the folder structure.")
        return None

    print(f"Found {total_files} GeoTIFF files. Loading without downsampling...")

    with tqdm(total=total_files, desc="Loading files", unit="file") as pbar:
        for file_path in file_list:
            with rasterio.open(file_path) as dataset:
                # Read the data (assume a single band for simplicity)
                data = dataset.read(1)

                # Get transform matrix to calculate geographic coordinates
                transform = dataset.transform

                # Create arrays of row and column indices
                rows, cols = np.indices(data.shape)

                # Convert row/col indices to geographic coordinates (latitude/longitude)
                lons, lats = rasterio.transform.xy(transform, rows, cols)

                # Flatten arrays and filter out masked (empty) data
                lats = np.array(lats).flatten()
                lons = np.array(lons).flatten()
                values = data.flatten()

                mask = values != 0  # Exclude no-data values
                lats = lats[mask]
                lons = lons[mask]
                values = values[mask]

                # Append the data for this file to the list
                geotiff_data.extend(zip(lats, lons, values))

            pbar.update(1)

    print("GeoTIFF files loaded successfully.")
    df = pd.DataFrame(geotiff_data, columns=['lat', 'lon', 'risk_level'])
    return df


def create_visualization(df):
    """
    Create a Plotly globe visualization for the given DataFrame.
    """
    try:
        # Limit the data to visualize for testing (e.g., 5000 points)
        df_sample = df.sample(n=5000) if len(df) > 5000 else df

        return {
            'data': [go.Scattergeo(
                lon=df_sample['lon'],
                lat=df_sample['lat'],
                text=df_sample['risk_level'],
                mode='markers',
                marker=dict(
                    size=2,
                    opacity=0.6,
                    color=df_sample['risk_level'],
                    colorscale='Viridis',
                    showscale=True,
                    colorbar=dict(title='Risk Level')
                )
            )],
            'layout': go.Layout(
                title='Deforestation Risk Visualization',
                geo=dict(
                    projection_type='orthographic',
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
        print(f"Error creating visualization: {str(e)}")
        return None


def main():
    # Load processed GeoTIFFs without downsampling from all subdirectories
    df = load_geotiffs_with_coordinates(processed_folder)
    if df is None or df.empty:
        print("Error: Failed to load GeoTIFF data.")
        return

    print("Data processing complete. Starting Dash server...")

    app = Dash(__name__)
    app.layout = html.Div([
        html.H1("Deforestation Risk Visualization"),
        dcc.Graph(id='globe-graph'),
        html.Div(id='click-data', children="Click on a point to see data"),
        dcc.Store(id='geotiff-data')
    ])

    @app.callback(
        Output('geotiff-data', 'data'),
        Input('globe-graph', 'id')
    )
    def store_geotiff_data(id):
        return df.to_dict('records')

    @app.callback(
        Output('globe-graph', 'figure'),
        Input('geotiff-data', 'data')
    )
    def update_graph(data):
        if data is None:
            return go.Figure()
        df = pd.DataFrame(data)
        return create_visualization(df)

    @app.callback(
        Output('click-data', 'children'),
        Input('globe-graph', 'clickData')
    )
    def display_click_data(clickData):
        if clickData is None:
            return "Click on a point to see data"
        point = clickData['points'][0]
        return f"Clicked on: Latitude {point['lat']:.4f}, Longitude {point['lon']:.4f}, Risk Level: {point['text']:.2f}"

    app.run_server(debug=True)


if __name__ == '__main__':
    main()
