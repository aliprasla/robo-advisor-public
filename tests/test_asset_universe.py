from threading import local
import unittest
import json
from marshmallow import Schema, fields



"""
Next two classes are Marshmallow Schemas define the ground truth structure of the "data/asset_universe.json" file.

"""



class TestAssetUniverseConfigFile(unittest.TestCase):
    """
    Validates the structure & data validity of the data/asset_universe.json
    """
    file_path = "config/asset_universe.json"

    def setUp(self):
        # load config file into object
        self.data = open(self.file_path,'r')
        
        # parse as dictionary object
        self.data = json.loads(self.data.read())

    def test_data_structure(self):
        AssetUniverseGroundTruthSchema().load(data = self.data)

        
        
class AssetClassItemSchema(Schema):
    # name is a string 
    name = fields.Str()

    # tickers is a list of strings
    tickers = fields.List(fields.Str())

    
class AssetUniverseGroundTruthSchema(Schema):
    version = fields.Str()
    description = fields.Str()
    data = fields.List(fields.Nested(AssetClassItemSchema))



if __name__ == "__main__":
    unittest.main()