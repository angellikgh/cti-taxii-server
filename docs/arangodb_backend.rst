Design of the TAXII Server ArangoDB Schema for *medallion*
==========================================================

ArangoDB Community Edition can be used as a backend to medallion.

This backend was built by following the guidance in docs/custom_backend and is heavily inspired by the mongodb implementation referenced in docs/mongodb_schema.

For those new to ArangoDB there are a few concepts to be aware of that are used in this implementation:

* Databases
* Collections
	* Document Collections
	* Edge Collections
* Graphs

For clarity, the term Collection in ArangoDB is completely unrelated to Collections in the TAXII specification. I will use the phrase "TAXII Collection" in the following documentation to explitly refer to TAXII Collections, else I will be referring to ArangoDB Collections.

Authentication
----------------------

The default medallion implementation allows you to specify a list of user:password in plain text for authentication.

In this implentation users are managed in ArangoDB. This allows for control of access on a per Database (API Root) level. Users can also be easily create and managed through the ArangoDB Web UI.

Database design
----------------------

In TAXII there are 

* API Root: An API Root usually represents an organisaton. TAXII Collections usually represent an Organisaton.
* TAXII Collection: A TAXII Collection is used to provide grouping of STIX Objects. An API Root can have zero or more Collections. Collections have a 1-1 relationship with an API Root.
* STIX Objects: The representation of intelligence. STIX Objects are stored inside a collection. STIX Objects can have relationships.

Server Discovery
----------------------

GET `HOST/taxii2/` should return information about the TAXII Server e.g.

.. code-block:: json
{
  "title": "Signals Corps Demo TAXII Server",
  "description": "This TAXII Server is not real.",
  "contact": "noreply@signalscorps.com",
  "default": "https://MY_HOST/api/v1/group1",
  "api_roots": [
    "https://MY_HOST/api/v1/group1",
    "https://MY_HOST/api/v1/group2",
    "https://MY_HOST/api/v1/group3"
  ]
}

The `api_roots` returned are dynamic, based on the API Roots user is subscribed too. All other information is static.

HOW TO STORE IN ARANGO?


API Root information
----------------------

GET `HOST/<API_ROOT>/` returns information about each API Root. e.g. 

.. code-block:: json
{
  "title": "Group 1 Sharing Group",
  "description": "An intelligence sharing group",
  "versions": ["application/taxii+json;version=2.1"],
  "max_content_length": 104857600
}


HOW TO STORE IN ARANGO? Need _url and _name key in db?

Collection(s) information
----------------------

GET `HOST/<API_ROOT>/collections/` or HOST/<API_ROOT>/collections/<COLLECTION_ID>. returns information about each Collection inside an API Root. e.g.

.. code-block:: json
{
  "collections": [
    {
      "id": "91a7b528-80eb-42ed-a74d-c6fbd5a26116",
      "title": "High Value Indicator Collection",
      "description": "This data collection contains high value IOCs",
      "can_read": true,
      "can_write": false,
      "media_types": [
        "application/stix+json;version=2.1"
      ]
    },
    {
      "id": "52892447-4d7e-4f70-b94d-d7f22742ff63",
      "title": "Another Collection",
      "description": "This data collection is for collecting current IOCs",
      "can_read": true,
      "can_write": true,
      "media_types": [
        "application/stix+json;version=2.1"
      ]
    }
  ]
}

Collection metadata is static (`id`, `title`, `description`).

`can_read` and `can_write` are dynamic and based on wether an authenticated user has permission to GET TAXII Collection Objects (`can_read`) and/or POST/DELETE TAXII Collection Objects.

`media_types` is determined on the STIX Object versions that are inside the collection. The `media_types` can be found in the `spec_version` of a STIX Object.

HOW TO STORE IN ARANGO? As a database?

Object Data
----------------------

TAXII Returns Objects in three different ways;

1. Full STIX Objects
2. Manifests of Objects
3. Versions of Objects

Full STIX Object contain the entire Object via GET `HOST/<API_ROOT>/collections/<COLLECTION_ID>/objects/?<FILTERS>` or GET `HOST/<API_ROOT>/collections/<COLLECTION_ID>/objects/<OBJECT_ID>/?<FILTERS>`

.. code-block:: json

{
  "more": false,
  "next": 0,
  "objects": [
    {
        "type": "indicator",
        "spec_version": "2.1",
        "id": "indicator--ef0b28e1-308c-4a30-8770-9b4851b260a5",
        "created": "2016-11-04T10:29:06.000Z",
        "modified": "2016-11-04T10:29:06.000Z",
        "name": "Malicious site hosting downloader",
        "description": "This organized threat actor group operates to create profit from all types of crime.",
        "indicator_types": [
            "malicious-activity"
        ],
        "pattern": "[url:value = 'http://x4z9arb.cn/4712/']",
        "pattern_type": "stix",
        "valid_from": "2016-11-04T10:29:06.000Z"
    }

It is full STIX Objects that are accepted by the TAXII API endpoints POST `HOST/<API_ROOT>/collections/<COLLECTION_ID>/objects/`, with a JSON envelope payload in the body.

Note the STIX 2.1 Data Model is a network graph with edges and nodes. In ArangoDB STIX Objects are stored as different Collection type:

1. A Document Collection to store the SDOs and SCOs.
2. An Edge Collection to store the SROs and embedded relationships (e.g. object_refs).

[Please read this post for more on this implementation logic](https://www.signalscorps.com/blog/2021/storing-stix-2_1-objects-database/).

Manifests of Objects obtained via GET `HOST/<API_ROOT>/collections/<ID>/manifest/?<FILTERS>` contains a filtered list of STIX Object fields (`id`, `date_added`, `version`). It also contains a `media_type` property with is deterimined by the `spec_version` of the STIX.

.. code-block:: json

{
  "more": false,
  "next": 0,
  "objects": [
    {
      "id": "indicator--ef0b28e1-308c-4a30-8770-9b4851b260a5",
      "date_added": "2016-11-04T10:29:06.000Z",
      "version": "2016-11-04T10:29:06.000Z",
      "media_type": "application/stix+json;version=2.1"
    }

Versions of Objects returned by GET `HOST/<API_ROOT>/collections/<COLLECTION_ID>/objects/<OBJECT_ID>/versions/?<FILTERS>` contain a list of unique STIX `modified` properties for the Object

.. code-block:: json
{
  "more": false,
  "next": 0,
  "versions": [
  	"2016-11-04T10:29:06.000Z",
    "2017-01-22T00:00:00.000Z"
  ]
}



Initialization of data
----------------------

An instance of this schema can be populated ....

Utilities to initialize your own ArangoDB can be found in ...


Supporting Docs
----------------------

A lot of this implementation is the result of our learnings of STIX/TAXII. Here are some references you might find useful:


* [STIX 2.1 101: Objects](https://www.signalscorps.com/blog/2021/oasis-stix-2_1-101-objects/)
* [STIX 2.1 102: Relationships](https://www.signalscorps.com/blog/2021/oasis-stix-2_1-102-relationships/)
* [STIX 2.1 103: Patterns](https://www.signalscorps.com/blog/2021/oasis-stix-2_1-103-patterns/)
* [STIX 2.1 104: Customisation](https://www.signalscorps.com/blog/2021/oasis-stix-2_1-104-customisation/)
* [STIX 2.1 105: Versioning](https://www.signalscorps.com/blog/2021/oasis-stix_2_1-105-versioning/)
* [STIX 2.1 106: Bundling](https://www.signalscorps.com/blog/2021/oasis-stix-2_1-106-bundling/)
* [STIX 2.1 107: Tooling](https://www.signalscorps.com/blog/2021/oasis-stix-2_1-107-tooling/)
* [TAXII 2.1 101: TAXII Concepts](https://www.signalscorps.com/blog/2021/oasis-taxii-2_1-101-introduction/)
* [TAXII 2.1 102: Consuming Objects in Collections](https://www.signalscorps.com/blog/2021/oasis-taxii-2_1-102-consuming-collections/)
* [TAXII 2.1 103: Updating Objects in Collections](https://www.signalscorps.com/blog/2021/oasis-taxii-2_1-103-updating-collections/)
* [TAXII 2.1 104: Medallion TAXII Server](https://www.signalscorps.com/blog/2021/oasis-taxii-2_1-104-medallion-taxii-server/)
* [TAXII 2.1 105: TAXII Clients](https://www.signalscorps.com/blog/2021/oasis-taxii-2_1-105-taxii-clients/)
* [Storing and Retrieving STIX 2.1 Objects Efficiently in ArangoDB](https://www.signalscorps.com/blog/2021/storing-stix-2_1-objects-database/)