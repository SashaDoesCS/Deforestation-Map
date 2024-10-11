import os
import numpy as np
import pickle
from tqdm import tqdm
import json
import base64
from typing import List, Tuple, Optional

# Configuration
CACHE_DIR = 'C:/Users/s/Downloads/Deforestation Risk Application/cache/'
SAMPLE_RATE = 5  # Adjust this to control data density
OUTPUT_FILE = 'deforestation_map.html'


class DataProcessor:
    @staticmethod
    def load_cache_file(cache_file: str) -> Optional[np.ndarray]:
        try:
            with open(cache_file, 'rb') as f:
                data = pickle.load(f)
                if isinstance(data, np.ndarray):
                    return data[::SAMPLE_RATE]
                elif isinstance(data, list):
                    return np.array(data)[::SAMPLE_RATE]
                else:
                    print(f"Unexpected data type in {cache_file}: {type(data)}")
                    return None
        except Exception as e:
            print(f"Error loading file {cache_file}: {e}")
            return None

    @staticmethod
    def process_all_data() -> Tuple[List[float], List[float], List[float]]:
        cached_files = [os.path.join(CACHE_DIR, f) for f in os.listdir(CACHE_DIR)
                        if f.endswith(".pkl")]

        all_data = []
        with tqdm(total=len(cached_files), desc="Processing Data Files") as pbar:
            for cache_file in cached_files:
                data = DataProcessor.load_cache_file(cache_file)
                if data is not None and len(data) > 0:
                    all_data.append(data)
                pbar.update(1)

        if not all_data:
            return [], [], []

        # Combine all data
        combined_data = np.concatenate(all_data)

        # Extract coordinates and values
        lats = combined_data[:, 0].tolist()
        lons = combined_data[:, 1].tolist()
        values = combined_data[:, 2].tolist() if combined_data.shape[1] > 2 else [1.0] * len(lats)

        return lats, lons, values


def create_html_file(lats: List[float], lons: List[float], values: List[float]):
    html_template = '''
<!DOCTYPE html>
<html>
<head>
    <title>Deforestation Risk Map</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        body { margin: 0; padding: 20px; font-family: Arial, sans-serif; }
        #map { height: 90vh; width: 100%; }
        .loading { 
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: rgba(255, 255, 255, 0.9);
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 0 10px rgba(0,0,0,0.2);
            z-index: 1000;
        }
    </style>
</head>
<body>
    <h1 style="text-align: center; margin-bottom: 20px;">Deforestation Risk Map</h1>
    <div id="map"></div>
    <div id="loading" class="loading">Loading map data...</div>

    <script>
        // Data from Python
        const data = {
            lats: LATITUDE_DATA,
            lons: LONGITUDE_DATA,
            values: VALUES_DATA
        };

        // Create the base map
        const trace = {
            type: 'scattergeo',
            lon: [],
            lat: [],
            mode: 'markers',
            marker: {
                color: [],
                colorscale: 'Viridis',
                showscale: true,
                opacity: 0.8,
                size: 3,
                colorbar: {
                    title: 'Risk Level'
                }
            },
            hovertemplate:
                'Latitude: %{lat:.2f}°<br>' +
                'Longitude: %{lon:.2f}°<br>' +
                'Risk Level: %{marker.color:.2f}<br>' +
                '<extra></extra>'
        };

        const layout = {
            title: 'Deforestation Risk Map',
            geo: {
                projection: {
                    type: 'orthographic'
                },
                showcoastlines: true,
                coastlinecolor: 'Black',
                showland: true,
                landcolor: 'rgb(243, 243, 243)',
                showocean: true,
                oceancolor: 'rgb(204, 229, 255)',
                showcountries: true,
                countrycolor: 'rgb(150, 150, 150)',
                showframe: false,
                bgcolor: 'rgba(255, 255, 255, 0)',
                projection_scale: 1.3,
                center: {
                    lat: 0,
                    lon: 0
                }
            },
            paper_bgcolor: 'rgba(255, 255, 255, 0)',
            plot_bgcolor: 'rgba(255, 255, 255, 0)',
            showlegend: false,
            height: 800,
            margin: {r: 0, l: 0, t: 30, b: 0}
        };

        // Initialize the plot
        Plotly.newPlot('map', [trace], layout);

        // Function to add data points in batches
        async function addDataPoints() {
            const batchSize = 1000;
            const totalPoints = data.lats.length;
            let currentIndex = 0;

            while (currentIndex < totalPoints) {
                const endIndex = Math.min(currentIndex + batchSize, totalPoints);

                const update = {
                    lat: [data.lats.slice(0, endIndex)],
                    lon: [data.lons.slice(0, endIndex)],
                    'marker.color': [data.values.slice(0, endIndex)]
                };

                await Plotly.update('map', update, {});
                currentIndex = endIndex;

                // Small delay to allow UI updates
                await new Promise(resolve => setTimeout(resolve, 10));
            }

            // Remove loading indicator
            document.getElementById('loading').style.display = 'none';
        }

        // Start adding data points when the page loads
        window.addEventListener('load', addDataPoints);
    </script>
</body>
</html>
    '''

    # Convert data to JSON strings
    lat_json = json.dumps(lats)
    lon_json = json.dumps(lons)
    values_json = json.dumps(values)

    # Replace placeholders with actual data
    html_content = html_template.replace('LATITUDE_DATA', lat_json)
    html_content = html_content.replace('LONGITUDE_DATA', lon_json)
    html_content = html_content.replace('VALUES_DATA', values_json)

    # Write the file
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"Created {OUTPUT_FILE}")
    print(f"Total points: {len(lats)}")


def main():
    print("Processing data files...")
    lats, lons, values = DataProcessor.process_all_data()

    if not lats:
        print("No data was loaded!")
        return

    print("Creating HTML file...")
    create_html_file(lats, lons, values)
    print("Done! Open deforestation_map.html in your web browser to view the map.")


if __name__ == '__main__':
    main()