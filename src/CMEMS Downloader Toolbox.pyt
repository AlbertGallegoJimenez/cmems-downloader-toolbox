import arcpy
from downloader_tool import CMEMS_Downloader

class Toolbox(object):
    def __init__(self):

        # List of tool classes associated with this toolbox
        self.tools = [CMEMS_Downloader]
