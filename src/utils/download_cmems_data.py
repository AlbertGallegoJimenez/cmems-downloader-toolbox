import xarray as xr
import pyproj
import numpy as np
import os
import arcpy
import copernicus_marine_client as copernicusmarine

class DataDownloader():
    """
    A class to download marine data from Copernicus Marine Service.

    Attributes:
        username (str): User name for the Copernicus Marine Service.
        password (str): Password for the Copernicus Marine Service.
        data_type (str): Type of marine data ("Waves" or "Sea Level").
        cmems_dataset_id (str): Identifier for the CMEMS dataset.
        cmems_data_GCS_EPSG (int): EPSG code for geographic coordinate system (GCS) of the data.
        output_filename (str): Name of the output NetCDF file.
        variables (list): List of variables to be downloaded.
        out_dir (str): Output directory for downloaded data.
    """

    def __init__(self, username:str, password:str, data_type:str):
        """
        Initialize DataDownloader with username, password, and data type.
        """

        self.username = username
        self.password = password
        
        if data_type == "Waves":
            self.cmems_dataset_id = "cmems_mod_ibi_wav_my_0.027deg_PT1H-i"
            self.cmems_data_GCS_EPSG = 4326
            self.output_filename = "CMEMS_Waves.nc"
            self.variables = ["VHM0", "VTPK", "VMDR"] # Significant wave height, Peak period, Wave direction
        elif data_type == "Sea Level":
            self.cmems_dataset_id = "cmems_mod_ibi_phy_my_0.083deg-2D_PT1H-m"
            self.cmems_data_GCS_EPSG = 32662
            self.output_filename = "CMEMS_SeaLevel.nc"
            self.variables = ["zos"]
            
        aprx = arcpy.mp.ArcGISProject('CURRENT')
        self.out_dir = os.path.join(aprx.homeFolder, "met-ocean data")
        if not os.path.exists(self.out_dir):
            os.mkdir(self.out_dir)
            
    def reproject_UTM_to_GCS(self, utm_feature_lon:float, utm_feature_lat:float, UTM_proj_EPSG:int):
        """
        Reproject coordinates from UTM to geographic coordinate system (GCS).

        Args:
            utm_feature_lon (float): Longitude of the feature in UTM coordinates.
            utm_feature_lat (float): Latitude of the feature in UTM coordinates.
            UTM_proj_EPSG (int): EPSG code for UTM projection.

        Returns:
            tuple: Transformed longitude and latitude.
        """
        utm = pyproj.CRS(f"EPSG:{UTM_proj_EPSG}")  # UTM
        gcs = pyproj.CRS(f"EPSG:{self.cmems_data_GCS_EPSG}")  # GCS

        proj_transformer = pyproj.Transformer.from_crs(utm, gcs, always_xy=True)

        return proj_transformer.transform(utm_feature_lon, utm_feature_lat)
        
    def download_data(self, gcs_feature_lon:float, gcs_feature_lat:float):
        """
        Download marine data from Copernicus Marine Service.

        Args:
            gcs_feature_lon (float): Longitude of the feature in GCS coordinates.
            gcs_feature_lat (float): Latitude of the feature in GCS coordinates.
        """
        copernicusmarine.subset(
            dataset_id=self.cmems_dataset_id,
            username=self.username,
            password=self.password,
            variables=self.variables,
            minimum_longitude=gcs_feature_lon-0.1,
            maximum_longitude=gcs_feature_lon+0.1,
            minimum_latitude=gcs_feature_lat-0.1,
            maximum_latitude=gcs_feature_lat+0.1,
            start_datetime="1993-01-01T00:00:00",
            end_datetime="2023-01-31T23:59:59",
            minimum_depth=0,
            maximum_depth=0.5,
            output_filename=self.output_filename,
            output_directory=self.out_dir,
            force_download=True
            )
    

class DatasetProcessor():
    """
    A class to process marine datasets.

    Attributes:
        ds (xr.Dataset): Dataset containing marine data.
        ds_proj (xr.Dataset): Copy of the dataset to be projected.
        GCS_proj_EPSG (int): EPSG code of the geographic coordinate system (GCS).
        UTM_proj_EPSG (int): EPSG code for the Universal Transverse Mercator (UTM) projection.
    """

    def __init__(self, ds:xr.Dataset, GCS_proj_EPSG:int, UTM_proj_EPSG:int):
        """
        Initialize DatasetProcessor with dataset and projection details.
        """

        self.ds = ds.copy(deep=True)
        self.ds_UTM = ds.copy(deep=True)
        self.GCS_proj_EPSG = GCS_proj_EPSG
        self.UTM_proj_EPSG = UTM_proj_EPSG
        
    def reproject_GCS_to_UTM(self):
        """
        Reproject dataset from GCS to UTM.

        Returns:
            ds_UTM: xr.Dataset reprojected to UTM coordinates.
        """
    
        gcs = pyproj.CRS(f"EPSG:{self.GCS_proj_EPSG}")  # GCS
        utm = pyproj.CRS(f"EPSG:{self.UTM_proj_EPSG}")  # UTM

        proj_transformer = pyproj.Transformer.from_crs(gcs, utm, always_xy=True)
        self.ds_UTM['longitude'], self.ds_UTM['latitude'] = proj_transformer.transform(self.ds_UTM['longitude'],
                                                                                         self.ds_UTM['latitude'])
        # Update the coordinate reference system of the dataset
        self.ds_UTM = self.ds_UTM.assign_coords({'longitude': self.ds_UTM['longitude'],
                                                 'latitude': self.ds_UTM['latitude']})

        return self.ds_UTM
    
    def find_valid_points(self, variable:str, feature_lon:float, feature_lat:float):
        """
        Find the nearest valid point in the dataset for a given feature.

        Args:
            variable (str): Variable for which the valid point is to be found.
            feature_lon (float): Longitude of the feature in UTM coordinates.
            feature_lat (float): Latitude of the feature in UTM coordinates.

        Returns:
            xr.Dataset: Dataset containing valid points.
        """
        
        # Compute the distances between the selected point and each point in the Dataset
        abslon = (self.ds_UTM.longitude - feature_lon) ** 2
        abslat = (self.ds_UTM.latitude - feature_lat) ** 2
        da_dist = np.sqrt(abslon + abslat)
        
        # Sort the distances values from nearest to farthest
        dist_sorted = np.sort(np.ravel(da_dist.to_numpy()))
        
        for point in dist_sorted:
            # Get the 2D-index of the nearest point
            idx_point = np.where(da_dist == point)
                        
            # Filter the dataset by the selected nearest point
            ds_selection = self.ds.isel(longitude=idx_point[0],
                                        latitude=idx_point[1])
            
            # Keep the data if there are not many nan values (i.e. > 90% of the data is valid)
            if np.count_nonzero(~np.isnan(ds_selection[variable])) / len(ds_selection[variable]) > 0.9:
                break

        return ds_selection