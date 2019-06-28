import base64
import os
import unittest

from medallion import application_instance, register_blueprints, set_config
from medallion.test.data.initialize_mongodb import reset_db


class TaxiiTest(unittest.TestCase):
    type = None
    DATA_FILE = os.path.join(
        os.path.dirname(__file__), "data", "default_data.json",
    )
    API_OBJECTS_2 = {
        "id": "bundle--8fab937e-b694-11e3-b71c-0800271e87d2",
        "objects": [
            {
                "created": "2017-01-27T13:49:53.935Z",
                "id": "indicator--%s",
                "labels": [
                    "url-watchlist",
                ],
                "modified": "2017-01-27T13:49:53.935Z",
                "name": "Malicious site hosting downloader",
                "pattern": "[url:value = 'http://x4z9arb.cn/5000']",
                "type": "indicator",
                "valid_from": "2017-01-27T13:49:53.935382Z",
            },
        ],
        "spec_version": "2.0",
        "type": "bundle",
    }

    memory_config = {
        "backend": {
            "module": "medallion.backends.memory_backend",
            "module_class": "MemoryBackend",
            "filename": DATA_FILE,
        },
        "users": {
            "admin": "Password0",
        },
        "taxii": {
            "max_page_size": 20,
        },
    }

    mongodb_config = {
        "backend": {
            "module": "medallion.backends.mongodb_backend",
            "module_class": "MongoBackend",
            "uri": "mongodb://travis:test@localhost:27017/",
        },
        "users": {
            "admin": "Password0",
        },
        "taxii": {
            "max_page_size": 20,
        },
    }

    def setUp(self):
        self.app = application_instance
        self.app_context = application_instance.app_context()
        self.app_context.push()
        self.app.testing = True
        register_blueprints(self.app)
        if self.type == "mongo":
            reset_db(self.mongodb_config["backend"]["uri"])
            self.configuration = self.mongodb_config
        elif self.type == "memory":
            self.memory_config["backend"]["filename"] = self.DATA_FILE
            self.configuration = self.memory_config
        else:
            raise RuntimeError("Unknown backend!")
        set_config(self.app, "backend", self.configuration)
        set_config(self.app, "users", self.configuration)
        set_config(self.app, "taxii", self.configuration)
        self.client = application_instance.test_client()
        encoded_auth = "Basic " + \
            base64.b64encode(b"admin:Password0").decode("ascii")
        self.auth = {"Authorization": encoded_auth}

    def tearDown(self):
        self.app_context.pop()
