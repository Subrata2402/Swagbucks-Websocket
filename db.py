from pymongo import MongoClient

mongo_url = "" # Put mongo db url
data = MongoClient(mongo_url)
db = data.get_database("Swagbucks")
sb_details = db.sb_details
