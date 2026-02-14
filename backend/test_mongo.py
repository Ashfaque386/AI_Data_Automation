from pymongo import MongoClient
import sys

uri = "mongodb+srv://Ashfaque386:Mongodb0491@cluster0.opvyyxu.mongodb.net/"
try:
    print(f"Connecting to {uri}...")
    client = MongoClient(uri, serverSelectionTimeoutMS=5000)
    print("Listing databases...")
    dbs = client.list_database_names()
    print("Databases:", dbs)
except Exception as e:
    print(f"Error: {e}")
