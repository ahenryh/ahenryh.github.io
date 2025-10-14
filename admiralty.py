import json
import pandas
import pprint
url_to_read = "http://data.portic.fr/api/ports/?param=&shortenfields=false&both_to=false&date=1787"
import requests
resp = requests.get(url_to_read)
#pretty_json = json.dumps(resp.json(), indent=1)
data = pandas.DataFrame(resp.json())
print(data)
data.admiralty
admiralty = [item for item in data.admiralty if item is not None]
for item in admiralty:
    if item not in set(admiralty):
        set(admiralty).add(item)
print(set(admiralty))
print(len(set(admiralty)))