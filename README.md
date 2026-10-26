# Grid-cells-extraction-from-SeNorge
The code in file "**precipitation and temperature gridded.py**" requires a shapefile of a catchment in input (for example generated from NEVINA), generates a 1x1 km grid over the catchment, connects to the API of SeNorge NVE and extracts as average of all the grid cells: precipitation and temperature series, average catchment altitude. It exports results in .csv files and reports number of grid cells. 

The code in file "**PINEHBV input file generation.py**" creates an Excel file in the format required by PINEHBV software. The values for runoff are set to 0 (since the PINEHBV software will simulate and fill these values). The Excel file produced will contain the temperature and precipitation series previously generated. 
