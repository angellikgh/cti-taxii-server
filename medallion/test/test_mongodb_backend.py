import base64
import copy
import json
import time
import six
import unittest
import uuid

from medallion import application_instance, init_backend, set_config, register_blueprints
from medallion.test.data.initialize_mongodb import reset_db
from medallion.utils import common
from medallion.views import MEDIA_TYPE_STIX_V20, MEDIA_TYPE_TAXII_V20

API_OBJECTS_2 = {
    "id": "bundle--8fab937e-b694-11e3-b71c-0800271e87d2",
    "objects": [
        {
            "created": "2017-01-27T13:49:53.935Z",
            "id": "indicator--%s",
            "labels": [
                "url-watchlist"
            ],
            "modified": "2017-01-27T13:49:53.935Z",
            "name": "Malicious site hosting downloader",
            "pattern": "[url:value = 'http://x4z9arb.cn/5000']",
            "type": "indicator",
            "valid_from": "2017-01-27T13:49:53.935382Z"
        }
    ],
    "spec_version": "2.0",
    "type": "bundle"
}


class TestTAXIIServerWithMongoDBBackend(unittest.TestCase):

    def setUp(self):
        application_instance.testing = True
        register_blueprints(application_instance)
        reset_db()
        init_backend({"type": "mongodb", "url": "mongodb://localhost:27017/"})
        set_config({"users": {"admin": "Password0"}})
        self.app = application_instance.test_client()
        encoded_auth = 'Basic ' + base64.b64encode(b"admin:Password0").decode("ascii")
        self.auth = {'Authorization': encoded_auth}

    @staticmethod
    def load_json_response(response):
        return json.load(six.BytesIO(response))

    def test_server_discovery(self):
        r = self.app.get("/taxii/", headers=self.auth)

        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.content_type, MEDIA_TYPE_TAXII_V20)
        server_info = self.load_json_response(r.data)
        assert server_info["title"] == "Some TAXII Server"

    def test_get_api_root_information(self):
        r = self.app.get("/trustgroup1/", headers=self.auth)

        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.content_type, MEDIA_TYPE_TAXII_V20)
        api_root_metadata = self.load_json_response(r.data)
        assert api_root_metadata["title"] == "Malware Research Group"

    def test_get_collections(self):
        r = self.app.get("/trustgroup1/collections/", headers=self.auth)

        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.content_type, MEDIA_TYPE_TAXII_V20)
        collections_metadata = self.load_json_response(r.data)
        collections_metadata = sorted(collections_metadata["collections"], key=lambda x: x["id"])
        assert collections_metadata[0]["id"] == "52892447-4d7e-4f70-b94d-d7f22742ff63"
        assert collections_metadata[1]["id"] == "91a7b528-80eb-42ed-a74d-c6fbd5a26116"

    def test_get_collection(self):
        r = self.app.get(
            "/trustgroup1/collections/52892447-4d7e-4f70-b94d-d7f22742ff63/",
            headers=self.auth
        )

        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.content_type, MEDIA_TYPE_TAXII_V20)
        collections_metadata = self.load_json_response(r.data)
        assert collections_metadata["media_types"][0] == "application/vnd.oasis.stix+json; version=2.0"

    def test_get_object(self):
        r = self.app.get(
            "/trustgroup1/collections/91a7b528-80eb-42ed-a74d-c6fbd5a26116/objects/malware--fdd60b30-b67c-11e3-b0b9-f01faf20d111/",
            headers=self.auth
        )

        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.content_type, MEDIA_TYPE_STIX_V20)
        obj = self.load_json_response(r.data)
        assert obj["objects"][0]["id"] == "malware--fdd60b30-b67c-11e3-b0b9-f01faf20d111"

    def test_get_objects(self):
        r = self.app.get(
            "/trustgroup1/collections/91a7b528-80eb-42ed-a74d-c6fbd5a26116/objects/?match[type]=relationship",
            headers=self.auth
        )

        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.content_type, MEDIA_TYPE_STIX_V20)
        objs = self.load_json_response(r.data)
        assert any(obj["id"] == "relationship--2f9a9aa9-108a-4333-83e2-4fb25add0463" for obj in objs["objects"])

    def test_add_objects(self):
        new_bundle = copy.deepcopy(API_OBJECTS_2)
        new_id = "indicator--%s" % uuid.uuid4()
        new_bundle["objects"][0]["id"] = new_id

        # ------------- BEGIN: add object section ------------- #

        post_header = copy.deepcopy(self.auth)
        post_header["Content-Type"] = MEDIA_TYPE_STIX_V20
        post_header["Accept"] = MEDIA_TYPE_TAXII_V20

        r_post = self.app.post(
            "/trustgroup1/collections/91a7b528-80eb-42ed-a74d-c6fbd5a26116/objects/",
            data=json.dumps(new_bundle),
            headers=post_header
        )
        status_response = self.load_json_response(r_post.data)
        self.assertEqual(r_post.status_code, 202)
        self.assertEqual(r_post.content_type, MEDIA_TYPE_TAXII_V20)

        # ------------- END: add object section ------------- #
        # ------------- BEGIN: get object section ------------- #

        get_header = copy.deepcopy(self.auth)
        get_header["Accept"] = MEDIA_TYPE_STIX_V20

        r_get = self.app.get(
            "/trustgroup1/collections/91a7b528-80eb-42ed-a74d-c6fbd5a26116/objects/?match[id]=%s" % new_id,
            headers=get_header
        )
        self.assertEqual(r_get.status_code, 200)
        self.assertEqual(r_get.content_type, MEDIA_TYPE_STIX_V20)

        objs = self.load_json_response(r_get.data)
        assert objs["objects"][0]["id"] == new_id

        # ------------- END: get object section ------------- #
        # ------------- BEGIN: get status section ------------- #

        r_get = self.app.get(
            "/trustgroup1/status/%s/" % status_response["id"],
            headers=self.auth
        )
        self.assertEqual(r_get.status_code, 200)
        self.assertEqual(r_get.content_type, MEDIA_TYPE_TAXII_V20)

        status_response2 = self.load_json_response(r_get.data)
        assert status_response2["success_count"] == 1

        # ------------- END: get status section ------------- #
        # ------------- BEGIN: get manifest section ------------- #

        r_get = self.app.get(
            "/trustgroup1/collections/91a7b528-80eb-42ed-a74d-c6fbd5a26116/manifest/?match[id]=%s" % new_id,
            headers=self.auth
        )
        self.assertEqual(r_get.status_code, 200)
        self.assertEqual(r_get.content_type, MEDIA_TYPE_TAXII_V20)

        manifests = self.load_json_response(r_get.data)
        assert manifests["objects"][0]["id"] == new_id
        # ------------- BEGIN: end manifest section ------------- #

    def test_client_object_versioning(self):
        new_id = "indicator--%s" % uuid.uuid4()
        new_bundle = copy.deepcopy(API_OBJECTS_2)
        new_bundle["objects"][0]["id"] = new_id

        # ------------- BEGIN: add object section ------------- #

        post_header = copy.deepcopy(self.auth)
        post_header["Content-Type"] = MEDIA_TYPE_STIX_V20
        post_header["Accept"] = MEDIA_TYPE_TAXII_V20

        r_post = self.app.post(
            "/trustgroup1/collections/91a7b528-80eb-42ed-a74d-c6fbd5a26116/objects/",
            data=json.dumps(new_bundle),
            headers=post_header
        )
        status_response = self.load_json_response(r_post.data)
        self.assertEqual(r_post.status_code, 202)
        self.assertEqual(r_post.content_type, MEDIA_TYPE_TAXII_V20)

        for i in range(0, 5):
            new_bundle = copy.deepcopy(API_OBJECTS_2)
            new_bundle["objects"][0]["id"] = new_id
            new_bundle["objects"][0]["modified"] = common.format_datetime(common.get_timestamp())
            r_post = self.app.post(
                "/trustgroup1/collections/91a7b528-80eb-42ed-a74d-c6fbd5a26116/objects/",
                data=json.dumps(new_bundle),
                headers=post_header
            )
            status_response = self.load_json_response(r_post.data)
            self.assertEqual(r_post.status_code, 202)
            self.assertEqual(r_post.content_type, MEDIA_TYPE_TAXII_V20)
            time.sleep(1)

        # ------------- END: add object section ------------- #
        # ------------- BEGIN: get object section 1 ------------- #

        get_header = copy.deepcopy(self.auth)
        get_header["Accept"] = MEDIA_TYPE_STIX_V20

        r_get = self.app.get(
            "/trustgroup1/collections/91a7b528-80eb-42ed-a74d-c6fbd5a26116/objects/?match[id]=%s&match[version]=%s"
            % (new_id, "all"),
            headers=get_header
        )
        self.assertEqual(r_get.status_code, 200)
        self.assertEqual(r_get.content_type, MEDIA_TYPE_STIX_V20)

        objs = self.load_json_response(r_get.data)
        assert objs["objects"][0]["id"] == new_id
        assert objs["objects"][-1]["modified"] == new_bundle["objects"][0]["modified"]

        # ------------- END: get object section 1 ------------- #
        # ------------- BEGIN: get object section 2 ------------- #

        r_get = self.app.get(
            "/trustgroup1/collections/91a7b528-80eb-42ed-a74d-c6fbd5a26116/objects/?match[id]=%s&match[version]=%s"
            % (new_id, "first"),
            headers=get_header
        )
        self.assertEqual(r_get.status_code, 200)
        self.assertEqual(r_get.content_type, MEDIA_TYPE_STIX_V20)

        objs = self.load_json_response(r_get.data)
        assert objs["objects"][0]["id"] == new_id
        assert objs["objects"][0]["modified"] == "2017-01-27T13:49:53.935Z"

        # ------------- END: get object section 2 ------------- #
        # ------------- BEGIN: get object section 3 ------------- #

        r_get = self.app.get(
            "/trustgroup1/collections/91a7b528-80eb-42ed-a74d-c6fbd5a26116/objects/?match[id]=%s&match[version]=%s"
            % (new_id, "last"),
            headers=get_header
        )
        self.assertEqual(r_get.status_code, 200)
        self.assertEqual(r_get.content_type, MEDIA_TYPE_STIX_V20)

        objs = self.load_json_response(r_get.data)
        assert objs["objects"][0]["id"] == new_id
        assert objs["objects"][0]["modified"] == new_bundle["objects"][0]["modified"]

        # ------------- END: get object section 3 ------------- #
        # ------------- BEGIN: get object section 4 ------------- #

        r_get = self.app.get(
            "/trustgroup1/collections/91a7b528-80eb-42ed-a74d-c6fbd5a26116/objects/?match[id]=%s&match[version]=%s"
            % (new_id, "2017-01-27T13:49:53.935Z"),
            headers=get_header
        )
        self.assertEqual(r_get.status_code, 200)
        self.assertEqual(r_get.content_type, MEDIA_TYPE_STIX_V20)

        objs = self.load_json_response(r_get.data)
        assert objs["objects"][0]["id"] == new_id
        assert objs["objects"][0]["modified"] == "2017-01-27T13:49:53.935Z"

        # ------------- END: get object section 4 ------------- #
        # ------------- BEGIN: get status section ------------- #

        r_get = self.app.get(
            "/trustgroup1/status/%s/" % status_response["id"],
            headers=self.auth
        )
        self.assertEqual(r_get.status_code, 200)
        self.assertEqual(r_get.content_type, MEDIA_TYPE_TAXII_V20)

        status_response2 = self.load_json_response(r_get.data)
        assert status_response2["success_count"] == 1

        # ------------- END: get status section ------------- #
        # ------------- BEGIN: get manifest section ------------- #

        r_get = self.app.get(
            "/trustgroup1/collections/91a7b528-80eb-42ed-a74d-c6fbd5a26116/manifest/?match[id]=%s" % new_id,
            headers=self.auth
        )
        self.assertEqual(r_get.status_code, 200)
        self.assertEqual(r_get.content_type, MEDIA_TYPE_TAXII_V20)

        manifests = self.load_json_response(r_get.data)

        assert manifests["objects"][0]["id"] == new_id
        assert any(version == new_bundle["objects"][0]["modified"] for version in manifests["objects"][0]["versions"])
        # ------------- END: get manifest section ------------- #

    def test_added_after_filtering(self):
        get_header = copy.deepcopy(self.auth)
        get_header["Accept"] = MEDIA_TYPE_STIX_V20

        r_get = self.app.get(
            "/trustgroup1/collections/91a7b528-80eb-42ed-a74d-c6fbd5a26116/objects/?added_after=2016-11-01T03:04:05Z",
            headers=get_header
        )
        self.assertEqual(r_get.status_code, 200)
        self.assertEqual(r_get.content_type, MEDIA_TYPE_STIX_V20)
        bundle = self.load_json_response(r_get.data)

        assert any(obj["id"] == "malware--fdd60b30-b67c-11e3-b0b9-f01faf20d111" for obj in bundle["objects"])
