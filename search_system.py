# File 1: search_system.py (new file)
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from abc import ABC, abstractmethod
import plotly.graph_objs as go
import pandas as pd


@dataclass
class TileData:
    lat: float
    lon: float
    canopy_level: float
    gain: bool
    loss: bool
    loss_year: int

    def matches_criteria(self, criteria: Dict[str, Any]) -> bool:
        """Check if tile matches all given criteria"""
        for key, value in criteria.items():
            if value is None:
                continue
            if key == 'min_canopy':
                if self.canopy_level < value:
                    return False
            elif key == 'max_canopy':
                if self.canopy_level > value:
                    return False
            elif key == 'min_loss_year':
                if not self.loss or (2000 + self.loss_year) < value:
                    return False
            elif key == 'max_loss_year':
                if not self.loss or (2000 + self.loss_year) > value:
                    return False
            elif key == 'has_gain':
                if bool(self.gain) != value:
                    return False
            elif key == 'has_loss':
                if bool(self.loss) != value:
                    return False
        return True


class Node:
    def __init__(self, data: TileData):
        self.data = data
        self.next: Optional[Node] = None


class SearchResultList:
    def __init__(self):
        self.head: Optional[Node] = None
        self.size = 0

    def append(self, tile: TileData):
        new_node = Node(tile)
        if not self.head:
            self.head = new_node
        else:
            current = self.head
            while current.next:
                current = current.next
            current.next = new_node
        self.size += 1

    def to_list(self) -> List[TileData]:
        result = []
        current = self.head
        while current:
            result.append(current.data)
            current = current.next
        return result

    def to_dataframe(self) -> pd.DataFrame:
        """Convert search results to DataFrame for visualization"""
        data = []
        current = self.head
        while current:
            data.append({
                'lat': current.data.lat,
                'lon': current.data.lon,
                'canopy_level': current.data.canopy_level,
                'gain': current.data.gain,
                'loss': current.data.loss,
                'loss_year': current.data.loss_year
            })
            current = current.next
        return pd.DataFrame(data)


class TileSearch(ABC):
    @abstractmethod
    def search(self, criteria: Dict[str, Any]) -> SearchResultList:
        pass


class BinaryTileSearch(TileSearch):
    def __init__(self, df):
        self.df = df.sort_values('canopy_level')
        self.tiles = [
            TileData(
                row['lat'],
                row['lon'],
                row['canopy_level'],
                bool(row['gain']),
                bool(row['loss']),
                row['loss_year']
            )
            for _, row in self.df.iterrows()
        ]

    def search(self, criteria: Dict[str, Any]) -> SearchResultList:
        results = SearchResultList()
        start_idx = 0
        end_idx = len(self.tiles)

        # Use binary search for canopy level bounds
        if criteria.get('min_canopy') is not None:
            start_idx = self._binary_search_min_canopy(criteria['min_canopy'])
            if start_idx is None:
                return results

        if criteria.get('max_canopy') is not None:
            temp_end = self._binary_search_max_canopy(criteria['max_canopy'])
            if temp_end is not None:
                end_idx = temp_end + 1

        # Check remaining criteria linearly
        self._collect_matching_results(start_idx, end_idx, criteria, results)
        return results

    def _binary_search_min_canopy(self, min_canopy: float) -> Optional[int]:
        left, right = 0, len(self.tiles) - 1
        result = None

        while left <= right:
            mid = (left + right) // 2
            if self.tiles[mid].canopy_level >= min_canopy:
                result = mid
                right = mid - 1
            else:
                left = mid + 1

        return result

    def _binary_search_max_canopy(self, max_canopy: float) -> Optional[int]:
        left, right = 0, len(self.tiles) - 1
        result = None

        while left <= right:
            mid = (left + right) // 2
            if self.tiles[mid].canopy_level <= max_canopy:
                result = mid
                left = mid + 1
            else:
                right = mid - 1

        return result

    def _collect_matching_results(self, start: int, end: int, criteria: Dict[str, Any],
                                  results: SearchResultList):
        for i in range(start, end):
            if self.tiles[i].matches_criteria(criteria):
                results.append(self.tiles[i])
