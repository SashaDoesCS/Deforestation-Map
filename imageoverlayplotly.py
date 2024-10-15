import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
import pandas as pd
import numpy as np
import os
import rasterio
import plotly.graph_objs as go
from tqdm import tqdm
import time
import dask.dataframe as dd
import dask.array as da
from sklearn.cluster import KMeans

# Path to the GeoTIFF folder
geotiff_folder = '70N_170W'

# GeoTIFF tile metadata
lat_start = 70.0
lon_start = -170.0
pixel_size = 0.00025

# Increase downsample factor for faster loading
DOWNSAMPLE_FACTOR = 100

# Number of clusters for K-means
N_CLUSTERS = 10000


def load_geotiffs_in_chunks(folder, downsample_factor):
    geotiff_data = []
    file_list = [f for f in os.listdir(folder) if f.endswith('.tif')]
    total_files = len(file_list)

    print(f"Found {total_files} GeoTIFF files. Loading with downsampling...")

    with tqdm(total=total_files, desc="Loading files", unit="file") as pbar:
        start_time = time.time()

        for filename in file_list:
            file_path = os.path.join(folder, filename)
            with rasterio.open(file_path) as dataset:
                data = dataset.read(1)[::downsample_factor, ::downsample_factor]
                geotiff_data.append(data)

            pbar.update(1)
            elapsed_time = time.time() - start_time
            remaining_time = (elapsed_time / (pbar.n + 1)) * (total_files - pbar.n)
            pbar.set_postfix({"ETA": f"{int(remaining_time)}s"})

    print("GeoTIFF files loaded successfully.")
    return geotiff_data


def process_geotiff_data(geotiff_data, downsample_factor):
    try:
        processed_data = []
        for data in geotiff_data:
            height, width = data.shape
            y_coords, x_coords = np.mgrid[0:height, 0:width]
            mask = data != 0

            lats = lat_start - (y_coords[mask] * pixel_size * downsample_factor)
            lons = lon_start + (x_coords[mask] * pixel_size * downsample_factor)
            risk_levels = data[mask]

            processed_data.extend(zip(lats, lons, risk_levels))

        df = pd.DataFrame(processed_data, columns=['lat', 'lon', 'risk_level'])
        return df
    except Exception as e:
        print(f"Error processing GeoTIFF data: {str(e)}")
        return None


def cluster_data(df, n_clusters):
    print("Clustering data...")
    kmeans = KMeans(n_clusters=n_clusters, random_state=42)
    df['cluster'] = kmeans.fit_predict(df[['lat', 'lon', 'risk_level']])

    clustered_df = df.groupby('cluster').agg({
        'lat': 'mean',
        'lon': 'mean',
        'risk_level': 'mean'
    }).reset_index()

    print("Clustering complete.")
    return clustered_df


def create_visualization(df):
    try:
        return {
            'data': [go.Scattergeo(
                lon=df['lon'],
                lat=df['lat'],
                text=df['risk_level'],
                mode='markers',
                marker=dict(
                    size=3,
                    opacity=0.8,
                    color=df['risk_level'],
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
                ),
                height=600,
                margin=dict(l=0, r=0, b=0, t=30)
            )
        }
    except Exception as e:
        print(f"Error creating visualization: {str(e)}")
        return None


def main():
    geotiff_data = load_geotiffs_in_chunks(geotiff_folder, DOWNSAMPLE_FACTOR)

    if not geotiff_data:
        print("Error: No GeoTIFF data loaded.")
        return

    df = process_geotiff_data(geotiff_data, DOWNSAMPLE_FACTOR)
    if df is None or df.empty:
        print("Error: Failed to process GeoTIFF data.")
        return

    # Cluster the data to reduce the number of points
    clustered_df = cluster_data(df, N_CLUSTERS)

    print("Data processing complete. Starting Dash server...")

    app = dash.Dash(__name__)
    app.layout = html.Div([
        html.H1("Deforestation Risk Visualization"),
        dcc.Graph(id='globe-graph'),
        html.Div(id='click-data', children="Click on a point to see data"),
        dcc.Store(id='clustered-data')
    ])

    @app.callback(
        Output('clustered-data', 'data'),
        Input('globe-graph', 'id')
    )
    def store_clustered_data(id):
        return clustered_df.to_dict('records')

    @app.callback(
        Output('globe-graph', 'figure'),
        Input('clustered-data', 'data')
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