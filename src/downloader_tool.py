import arcpy
import os
import numpy as np
import xarray as xr
from utils.download_cmems_data import DataDownloader, DatasetProcessor

class CMEMS_Downloader(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "CMEMS Downloader Toolbox"
        self.description = "The CMEMS Downloader Toolbox is an ArcGIS Python toolbox that enables automatic" \
            "retrieval of marine data from the Copernicus Marine Service using a simple Feature Class input."
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        # Input username parameter
        in_username = arcpy.Parameter(
            displayName="CMEMS Username",
            name="in_username",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        
        # Input password parameter
        in_password = arcpy.Parameter(
            displayName="CMEMS Password",
            name="in_password",
            datatype="GPStringHidden",
            parameterType="Required",
            direction="Input")
        
        # Input wave data parameter
        in_wave_data = arcpy.Parameter(
            displayName="Download WAVE data",
            name="in_waves_data",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input")
        
        # Input sealevel data parameter
        in_sealevel_data = arcpy.Parameter(
            displayName="Download SEA LEVEL data",
            name="in_sealevel_data",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input")
        
        # Input Features parameter
        in_features = arcpy.Parameter(
            displayName="Input Feature from which the nearest CMEMS data will be downloaded",
            name="in_features",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")
        
        params = [in_username, in_password, in_wave_data, in_sealevel_data, in_features]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        parameters[4].setWarningMessage(
            "The spatial reference of the feature must be in a UTM (projected) system.")
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""

        in_username = parameters[0].valueAsText
        in_password = parameters[1].valueAsText
        in_wave_data = parameters[2].valueAsText
        in_sealevel_data = parameters[2].valueAsText
        in_features = parameters[4].valueAsText
        
        # Get feature class EPSG
        fc_epsg = arcpy.Describe(in_features).spatialReference.factorycode
        
        # Calculate the longitude centroid of each feature
        arcpy.management.AddField(in_features, "lon_cent", "DOUBLE")
        arcpy.management.CalculateField(in_features, "lon_cent", "!SHAPE.CENTROID.X!")
        cursor = arcpy.da.SearchCursor(in_features, ["lon_cent"])
        feature_lons_centroid = [row[0] for row in cursor]
        feature_lon_utm = np.mean(feature_lons_centroid)
        
        # Calculate the latitude centroid of each feature
        arcpy.management.AddField(in_features, "lat_cent", "DOUBLE")
        arcpy.management.CalculateField(in_features, "lat_cent", "!SHAPE.CENTROID.Y!")
        cursor = arcpy.da.SearchCursor(in_features, ["lat_cent"])
        feature_lats_centroid = [row[0] for row in cursor]
        feature_lat_utm = np.mean(feature_lats_centroid)

        # Delete the fields created
        arcpy.management.DeleteField(in_features, ["lon_cent", "lat_cent"])

        # === PERFORM THE DOWNLOAD AND THE PROCESSING ===
        for data_type, databool in {"Waves":in_wave_data, "Sea Level":in_sealevel_data}.items():
            if databool == "true":
                arcpy.AddMessage("Downlading {} ...".format(data_type))
                # === DOWNLOAD THE DATA ===
                # Initialize the DataDownloader object
                downloader = DataDownloader(in_username, in_password, data_type)
                # Get the values of longitude and latitude in GCS
                feature_lon_gcs, feature_lat_gcs = downloader.reproject_UTM_to_GCS(feature_lon_utm, feature_lat_utm, fc_epsg)
                # Download the data and save it to a NetCDF file
                downloader.download_data(feature_lon_gcs, feature_lat_gcs)
                
                # === PROCESS THE DATASET ===
                # Get parameters from the downloader object
                variable = downloader.variables[0]
                out_dir = downloader.out_dir
                out_filename = downloader.output_filename
                cmems_GCS_EPSG = downloader.cmems_data_GCS_EPSG
                
                # Open the output file as a Xarray Dataset
                UTM_EPSG = arcpy.Describe('TORDERA_Transects').SpatialReference.factorycode
                ds = xr.open_dataset(os.path.join(out_dir, out_filename))
                # Initialize the DatasetProcessor object
                ds_processor = DatasetProcessor(ds, cmems_GCS_EPSG, UTM_EPSG)
                ds = ds_processor.reproject_GCS_to_UTM()
                # Find valid points based on a variable in the dataset
                ds_selected = ds_processor.find_valid_points(variable, feature_lon_utm, feature_lat_utm)
                # Rewrite the dataset to the output file
                ds_selected.to_netcdf(os.path.join(out_dir, out_filename))
                
                arcpy.AddMessage("Data downloaded in {} .".format(out_filename))
        return

    def postExecute(self, parameters):
        """This method takes place after outputs are processed and
        added to the display."""
        return