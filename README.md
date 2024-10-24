# Deforestation-Map

This 3D visualization shows the tree canopy of the world, allowing the user to interact with any point and log the coordinates, the canopy level in that area, and (currently unimplemented) whether the area has experienced a gain or loss during the time span of the data. 2000 - 2014, and will include the year that the most was loss for a loss tile.


Below is a list of all of the necessary files that can be copy and pasted into the command prompt, this program will not run without all of these. 
```
@echo off
echo Starting library installation...
echo.

pip install rasterio
echo.

pip install numpy
echo.

pip install pandas
echo.

pip install tqdm
echo.

pip install dash
echo.

pip install plotly
echo.

echo Installation complete.
pause
```
