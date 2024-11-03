# Created with the help of ChatGPT 4o
# Creator notes: Timsort is the builtin sort function for Python, this program
# Uses it as in illustration of what the built-in function is, and will work using
# The built-in sort instead, to see this change, there is one line in the imports
# That is changed to switch between search_system.py and search_systemtimsort.py


from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from abc import ABC, abstractmethod
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


def insertion_sort(arr: List[TileData], left: int, right: int) -> None:
    """Insertion sort for small subarrays"""
    for i in range(left + 1, right + 1):
        temp = arr[i]
        j = i - 1
        while j >= left and arr[j].canopy_level > temp.canopy_level:
            arr[j + 1] = arr[j]
            j -= 1
        arr[j + 1] = temp


def merge(arr: List[TileData], l: int, m: int, r: int) -> None:
    """Merge two sorted subarrays"""
    left = arr[l:m + 1]
    right = arr[m + 1:r + 1]

    i = j = 0
    k = l

    while i < len(left) and j < len(right):
        if left[i].canopy_level <= right[j].canopy_level:
            arr[k] = left[i]
            i += 1
        else:
            arr[k] = right[j]
            j += 1
        k += 1

    while i < len(left):
        arr[k] = left[i]
        k += 1
        i += 1

    while j < len(right):
        arr[k] = right[j]
        k += 1
        j += 1


def timsort(arr: List[TileData]) -> None:
    """Implementation of Timsort algorithm"""
    min_run = 32
    n = len(arr)

    # Create runs of minimum size
    for start in range(0, n, min_run):
        end = min(start + min_run - 1, n - 1)
        insertion_sort(arr, start, end)

    # Merge runs
    size = min_run
    while size < n:
        for left in range(0, n, 2 * size):
            mid = min(n - 1, left + size - 1)
            right = min(left + 2 * size - 1, n - 1)
            if mid < right:
                merge(arr, left, mid, right)
        size *= 2


class TileSearch(ABC):
    @abstractmethod
    def search(self, criteria: Dict[str, Any]) -> SearchResultList:
        pass


class BinaryTileSearch(TileSearch):
    def __init__(self, df):
        # Convert DataFrame to list of TileData objects
        self.tiles = [
            TileData(
                row['lat'],
                row['lon'],
                row['canopy_level'],
                bool(row['gain']),
                bool(row['loss']),
                row['loss_year']
            )
            for _, row in df.iterrows()
        ]
        # Sort using Timsort instead of built-in sort
        timsort(self.tiles)

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