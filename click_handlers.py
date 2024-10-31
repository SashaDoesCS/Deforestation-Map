# created with the help of chatGPT 4o

import pandas as pd
from collections import deque


class LogNode:
    def __init__(self, data):
        self.data = data
        self.next = None


class LogLinkedList:
    def __init__(self, max_size=10):
        self.head = None
        self.size = 0
        self.max_size = max_size

    def append(self, data):
        new_node = LogNode(data)

        # If list is empty
        if not self.head:
            self.head = new_node
            self.size = 1
            return

        # If list is at max size, remove oldest entry (last node)
        if self.size >= self.max_size:
            new_node.next = self.head
            self.head = new_node
            current = self.head
            # Traverse to second-to-last node
            for _ in range(self.max_size - 2):
                current = current.next
            # Remove last node
            current.next = None
        else:
            # Add new node at beginning
            new_node.next = self.head
            self.head = new_node
            self.size += 1

    def get_all_logs(self):
        logs = []
        current = self.head
        while current:
            logs.append(current.data)
            current = current.next
        return logs


class PointAnalyzer:
    def analyze(self, data):
        raise NotImplementedError("Subclass must implement this method")


class GainAnalyzer(PointAnalyzer):
    def analyze(self, data):
        return "Gain detected" if data["gain"] == 1 else "No gain"


class LossAnalyzer(PointAnalyzer):
    def analyze(self, data):
        return f"Loss in year {2000 + data['loss_year']}" if data["loss"] == 1 else "No loss"


class ClickHandler:
    def __init__(self):
        self.click_queue = deque(maxlen=3)
        self.click_log = LogLinkedList(max_size=10)  # Initialize with max_size=10

    def analyze_area_changes(self, df, center_lat, center_lon, degree_range=5):
        """
        Analyze forest coverage changes in a 10x10 degree area around clicked point.
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
        if click_data is None:
            return self.get_empty_response()

        try:
            lat = click_data['points'][0]['lat']
            lon = click_data['points'][0]['lon']
            point_data = df[
                (df['lat'] == lat) &
                (df['lon'] == lon)
                ].iloc[0].to_dict() if not df.empty else None

            if point_data is None:
                return self.get_empty_response()

            area_analysis = self.analyze_area_changes(df, lat, lon)
            area_analysis_text = (
                f"10°x10° Area Analysis:\n"
                f"Forest Gain: {area_analysis['gain_points']} points ({area_analysis['gain_percentage']:.1f}%)\n"
                f"Forest Loss: {area_analysis['loss_points']} points ({area_analysis['loss_percentage']:.1f}%)\n"
                f"Total Data Points: {area_analysis['total_points']}\n"
                f"Overall Trend: {area_analysis['net_change']}"
            )

            self.click_queue.append((lat, lon, point_data))

            # Polymorphic handling for point status
            gain_analyzer = GainAnalyzer()
            loss_analyzer = LossAnalyzer()
            point_status = ", ".join([
                gain_analyzer.analyze(point_data),
                loss_analyzer.analyze(point_data)
            ])

            # Create and append log entry
            log_entry = (
                f"Lat {lat:.4f}, Lon {lon:.4f}: "
                f"Canopy {point_data['canopy_level']:.1f}%, {point_status} | "
                f"Area: {area_analysis['net_change']}"
            )
            self.click_log.append(log_entry)

            avg_canopy = self.calculate_average_canopy()

            return {
                'click_data': f"Clicked: Lat {lat:.4f}, Lon {lon:.4f}, "
                              f"Canopy Level: {point_data['canopy_level']:.1f}%, {point_status}",
                'area_analysis': area_analysis_text,
                'queue_display': self.format_queue_display(),
                'average_log': f"Average canopy of last {len(self.click_queue)} points: {avg_canopy:.2f}%",
                'full_log': "Recent History: " + " | ".join(self.click_log.get_all_logs())
            }

        except Exception as e:
            print(f"Error in click handler: {e}")
            return self.get_empty_response()

    def calculate_average_canopy(self):
        if not self.click_queue:
            return 0.0
        canopy_levels = [data['canopy_level'] for _, _, data in self.click_queue]
        return sum(canopy_levels) / len(canopy_levels)

    def format_queue_display(self):
        if not self.click_queue:
            return "Point queue: Empty"

        points = [
            f"({lat:.4f}, {lon:.4f}: {data['canopy_level']:.1f}%)"
            for lat, lon, data in self.click_queue
        ]
        return "Point queue: " + ", ".join(points)

    def get_empty_response(self):
        return {
            'click_data': "Click on a point to see canopy data",
            'area_analysis': "Click to see area analysis",
            'queue_display': "Point queue: Empty",
            'average_log': "Average canopy log: None",
            'full_log': "Full log: Empty"
        }