# Deforestation-Map

This 3D visualization shows the tree canopy of the world, allowing the user to interact with any point and log the coordinates, the canopy level in that area, and whether the 10 by 10 degree area around the click has experienced a gain or loss during the time span of the data, 2000 - 2014, and will include the year that the most was loss for a loss tile.

please follow instructions listed in the readme before runtime to prevent any potential errors with use.
# Creator notes: This program was created and tested on Windows 11 ONLY
On run there will be a loading bar via the terminal, allow about 10-20 seconds to load. Some latency is expected for rotating the globe. Make sure your target processed folder is listed correctly, double check names matching if an error occurs.

Below is a list of all the necessary libraries that can be copy and pasted into the command prompt, this program will not run without all of these. 

The map overlay on the globe does not capture every landmass unlike satelite data due to current limitations, some points will seem to be in the ocean but in reality are islands. Keep in mind as your proceeding.

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
