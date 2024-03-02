<a name="readme-top"></a>
# CMEMS Downloader Toolbox for ArcGIS Pro 🧰🌎

 The CMEMS Downloader Toolbox is an ArcGIS Python Toolbox that enables automatic retrieval of marine data from the Copernicus Marine Service using a simple Feature Class input.

<!-- FEATURES -->
## Features
- **Download Marine Data**: Download wave data or sea level data from the Copernicus Marine Service based on the input feature's location.
- **Automatic Data Processing**: Automatically process the downloaded marine data, including reprojection and finding valid points.
- **User-friendly Interface**: Intuitive toolbox interface within ArcGIS Pro.

> [!IMPORTANT]
> **Attention:** This repository is intended exclusively for downloading wave and sea level data for the Iberian Peninsula. To customize the tool for other regions, please access the source code and modify the dataset IDs to be downloaded accordingly.

<!-- INSTALLATION -->
## Installation
1. Clone or download this repository to your local machine.
2. Open ArcGIS Pro.
3. Navigate to the ArcGIS Pro "Catalog" pane.
4. Right-click on "Toolboxes" and select "Add Toolbox".
5. Browse to the location where you saved the downloaded toolbox file (*CMEMS_Downloader.pyt*) and click "OK".

<!-- REQUIREMENTS -->
## Requirements
- ```ArcGIS Pro```
- ```Python 3.x```
- ```xarray```
- ```pyproj```
- ```numpy```
- ```arcpy (ArcGIS Python module)```
- ```copernicus_marine_client```

> [!WARNING]
> Note that you must clone the ArcGIS Pro default environment to install new libraries in the Anaconda environment.

<!-- CONTACT -->
## Contact

Albert Gallego Jiménez - [LinkedIn](https://www.linkedin.com/in/albert-gallego-jimenez) - agalleji8@gmail.com

Project Link: [https://github.com/AlbertGallegoJimenez/shoreline-evolution-tool](https://github.com/AlbertGallegoJimenez/shoreline-evolution-tool)

<p align="right">(<a href="#readme-top">back to top</a>)</p>
