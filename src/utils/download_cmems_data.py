import xarray as xr
import pyproj
import numpy as np
import os
import arcpy
import copernicus_marine_client as copernicusmarine

class DataDownloader():
    def __init__(self, username:str, password:str, data_type:str):
        
        # User name and password for the Copernicus Marine Service
        self.username = username
        self.password = password
        
        # Get the type of data the user has selected
        if data_type == "Waves":
            self.cmems_dataset_id = "cmems_mod_ibi_wav_my_0.027deg_PT1H-i"
            self.cmems_data_GCS_EPSG = 4326
            self.output_filename = "CMEMS_Waves.nc"
            self.variables = ["VHM0", "VTPK", "VMDR"] # Hs, Tp, Wave dir
        elif data_type == "Sea Level":
            self.cmems_dataset_id = "cmems_mod_ibi_phy_my_0.083deg-2D_PT1H-m"
            self.cmems_data_GCS_EPSG = 32662
            self.output_filename = "CMEMS_SeaLevel.nc"
            self.variables = ["zos"]
            
        # Create output directory for the downloaded data
        aprx = arcpy.mp.ArcGISProject('CURRENT')
        self.out_dir = os.path.join(aprx.homeFolder, "met-ocean data")
        if not os.path.exists(self.out_dir):
            os.mkdir(self.out_dir)
            
    def reproject_UTM_to_GCS(self, feature_lon:float, feature_lat:float, UTM_proj_EPSG:int):
    
        # Define the GCS and UTM coordinate systems
        gcs = pyproj.CRS(f"EPSG:4326")  # GCS
        utm = pyproj.CRS(f"EPSG:{UTM_proj_EPSG}")  # UTM

        # Create a transformer object to convert coordinates from GCS to UTM
        proj_transformer = pyproj.Transformer.from_crs(utm, gcs, always_xy=True)

        # Apply the transformation to the longitude and latitude coordinates
        return proj_transformer.transform(feature_lon, feature_lat)
        
    def download_data(self, feature_lon:float, feature_lat:float):
        # Download the data from the Copernicus Marine Service
        copernicusmarine.subset(
            dataset_id=self.cmems_dataset_id,
            username=self.username,
            password=self.password,
            variables=self.variables,
            minimum_longitude=feature_lon-0.1,
            maximum_longitude=feature_lon+0.1,
            minimum_latitude=feature_lat-0.1,
            maximum_latitude=feature_lat+0.1,
            start_datetime="1993-01-01T00:00:00",
            end_datetime="2023-01-31T23:59:59",
            minimum_depth=0,
            maximum_depth=0.5,
            output_filename = self.output_filename,
            output_directory = self.out_dir,
            force_download=True
            )
    

class DatasetProcessor():
    def __init__(self, ds:xr.Dataset, GCS_proj_EPSG:int, UTM_proj_EPSG:int):
        # Dataset containing marine data
        self.ds = ds
        # EPSG code of the GCS projection
        self.GCS_proj_EPSG = GCS_proj_EPSG
        # EPSG code for the UTM zone of interest
        self.UTM_proj_EPSG = UTM_proj_EPSG
        
    def reproject_GCS_to_UTM(self):
    
        # Define the GCS and UTM coordinate systems
        gcs = pyproj.CRS(f"EPSG:{self.GCS_proj_EPSG}")  # GCS
        utm = pyproj.CRS(f"EPSG:{self.UTM_proj_EPSG}")  # UTM

        # Create a transformer object to convert coordinates from GCS to UTM
        proj_transformer = pyproj.Transformer.from_crs(gcs, utm, always_xy=True)

        # Apply the transformation to the longitude and latitude coordinates
        self.ds['longitude'], self.ds['latitude'] = proj_transformer.transform(self.ds['longitude'],
                                                                               self.ds['latitude'])

        # Update the coordinate reference system of the dataset
        self.ds = self.ds.assign_coords({'longitude': self.ds['longitude'],
                                         'latitude': self.ds['latitude']})

        return self.ds
    
    def find_valid_points(self, variable:str, feature_lon:float, feature_lat:float):
        
        # Compute the distances between the selected point and each point in the Dataset
        abslon = (self.ds.longitude - feature_lon) ** 2
        abslat = (self.ds.latitude - feature_lat) ** 2
        da_dist = np.sqrt(abslon + abslat)
        
        # Sort the distances values from nearest to farthest
        dist_sorted = np.sort(np.ravel(da_dist.to_numpy()))
        
        for point in dist_sorted:
            # Get the 2D-index of the nearest point
            idx_point = np.where(da_dist == point)
            
            # Select the lon/lat coordinates from distances DataArray (i.e. da_dist)
            lon_point, lat_point = da_dist[idx_point].longitude.values, da_dist[idx_point].latitude.values
            
            # Filter the dataset by the selected nearest point
            ds_selection = self.ds.sel(longitude=lon_point,
                                       latitude=lat_point,
                                       method='nearest')
            
            # Keep the data if there are not many nan values (i.e. > 90% of the data is valid)
            if np.count_nonzero(~np.isnan(ds_selection[variable])) / len(ds_selection[variable]) > 0.9:
                break

        return ds_selection