import pandas as pd
from collections import deque


class ClickHandler:
    def __init__(self):
        # Queue to store recent points for analysis
        self.click_queue = deque(maxlen=3)
        # Log to store all click history
        self.click_log = []

    def analyze_area_changes(self, df, center_lat, center_lon, degree_range=5):
        """
        Analyze forest coverage changes in a 10x10 degree area around clicked point.

        Args:
            df: DataFrame with forest coverage data
            center_lat: Latitude of clicked point
            center_lon: Longitude of clicked point
            degree_range: Half the size of area to analyze (5 degrees = 10x10 degree area)
        """
        # Define area boundaries
        lat_min = center_lat - degree_range
        lat_max = center_lat + degree_range
        lon_min = center_lon - degree_range
        lon_max = center_lon + degree_range

        # Filter data for the area
        area_data = df[
            (df['lat'] >= lat_min) & (df['lat'] <= lat_max) &
            (df['lon'] >= lon_min) & (df['lon'] <= lon_max)
            ]

        if len(area_data) == 0:
            return {
                'gain_points': 0,
                'loss_points': 0,
                'total_points': 0,
                'net_change': 'No data',
                'gain_percentage': 0,
                'loss_percentage': 0
            }

        # Count gain and loss points
        gain_points = len(area_data[area_data['gain'] == 1])
        loss_points = len(area_data[area_data['loss'] == 1])
        total_points = len(area_data)

        # Calculate percentages
        gain_percentage = (gain_points / total_points) * 100
        loss_percentage = (loss_points / total_points) * 100

        # Calculate net change
        if gain_points > loss_points:
            net_change = 'Net Gain'
        elif loss_points > gain_points:
            net_change = 'Net Loss'
        else:
            net_change = 'Neutral'

        return {
            'gain_points': gain_points,
            'loss_points': loss_points,
            'total_points': total_points,
            'net_change': net_change,
            'gain_percentage': gain_percentage,
            'loss_percentage': loss_percentage
        }

    def handle_click(self, click_data, df):
        """
        Process click events and analyze forest coverage changes.

        Args:
            click_data: Click event data from Dash
            df: DataFrame containing forest coverage data
        """
        if click_data is None:
            return self.get_empty_response()

        try:
            lat = click_data['points'][0]['lat']
            lon = click_data['points'][0]['lon']

            # Get clicked point data
            point_data = df[
                (df['lat'] == lat) &
                (df['lon'] == lon)
                ].iloc[0].to_dict() if not df.empty else None

            if point_data is None:
                return self.get_empty_response()

            # Analyze area changes
            area_analysis = self.analyze_area_changes(df, lat, lon)

            # Format area analysis text
            area_analysis_text = (
                f"10°x10° Area Analysis:\n"
                f"Forest Gain: {area_analysis['gain_points']} points ({area_analysis['gain_percentage']:.1f}%)\n"
                f"Forest Loss: {area_analysis['loss_points']} points ({area_analysis['loss_percentage']:.1f}%)\n"
                f"Total Data Points: {area_analysis['total_points']}\n"
                f"Overall Trend: {area_analysis['net_change']}"
            )

            # Store point in queue
            self.click_queue.append((lat, lon, point_data))

            # Create point status
            point_status = self.get_point_status(point_data)

            # Add to click log with area analysis
            log_entry = (
                f"Lat {lat:.4f}, Lon {lon:.4f}: "
                f"Canopy {point_data['canopy_level']:.1f}%, {point_status} | "
                f"Area: {area_analysis['net_change']}"
            )
            self.click_log.append(log_entry)

            # Calculate average canopy for recent points
            avg_canopy = self.calculate_average_canopy()

            return {
                'click_data': f"Clicked: Lat {lat:.4f}, Lon {lon:.4f}, "
                              f"Canopy Level: {point_data['canopy_level']:.1f}%, {point_status}",
                'area_analysis': area_analysis_text,
                'queue_display': self.format_queue_display(),
                'average_log': f"Average canopy of last {len(self.click_queue)} points: {avg_canopy:.2f}%",
                'full_log': "Recent History: " + " | ".join(self.click_log[-5:])
            }

        except Exception as e:
            print(f"Error in click handler: {e}")
            return self.get_empty_response()

    def get_point_status(self, point_data):
        """Generate status string for a point"""
        status = []
        if point_data["gain"] == 1:
            status.append("Gain detected")
        if point_data["loss"] == 1:
            status.append(f"Loss in year {2000 + point_data['loss_year']}")
        return ", ".join(status) if status else "No change"

    def calculate_average_canopy(self):
        """Calculate average canopy level for points in queue"""
        if not self.click_queue:
            return 0.0
        canopy_levels = [data['canopy_level'] for _, _, data in self.click_queue]
        return sum(canopy_levels) / len(canopy_levels)

    def format_queue_display(self):
        """Format queue for display"""
        if not self.click_queue:
            return "Point queue: Empty"

        points = [
            f"({lat:.4f}, {lon:.4f}: {data['canopy_level']:.1f}%)"
            for lat, lon, data in self.click_queue
        ]
        return "Point queue: " + ", ".join(points)

    def get_empty_response(self):
        """Return empty response structure"""
        return {
            'click_data': "Click on a point to see canopy data",
            'area_analysis': "Click to see area analysis",
            'queue_display': "Point queue: Empty",
            'average_log': "Average canopy log: None",
            'full_log': "Full log: Empty"
        }