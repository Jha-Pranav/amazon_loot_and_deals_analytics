# Performing standard imports
import configparser

import json
import requests
import numpy as np
from bs4 import BeautifulSoup

config = configparser.RawConfigParser()


class CollectData:
    """
    doc
    """

    BASE_URL = "https://pricehistory.in/"
    SEARCH_BOX_URL = "https://pricehistory.in/livewire/message/pricehistory/"

    def __init__(self, config_file_path="config.ini"):
        self.path = config_file_path
        config.read(config_file_path)
        self.data = eval(config["PriceHistory"]["data"])
        

        self.headers = eval(config["PriceHistory"]["headers"])

    def get_cookies_and_csrf_token(self):
        response = requests.get(self.BASE_URL, headers=self.headers)
        if response.status_code == 200:
            cookie = "; ".join([x.name + "=" + x.value for x in response.cookies])
            soup = BeautifulSoup(response.text, "lxml")

            for i in soup.findAll("div"):
                fingerprint = i.get("wire:initial-data")
                if fingerprint:
                    self.data.update(json.loads(fingerprint))
            csrf_token = soup.select_one('meta[name="csrf-token"]')["content"]
            self.headers["x-csrf-token"] = csrf_token
            self.headers["cookie"] = cookie
            # Updating config file with updated values
            config.set("PriceHistory", "data", self.data)
            config.set("PriceHistory", "headers", self.headers)
            print("New Cookies and Csrf token captured")
            #  Writing our configuration file to 'example.ini'
            print("Update config file with the latest values")
            with open(self.path, "w") as configfile:
                config.write(configfile)
        else:
            print("Error occured while generating cookies or csrf_token")

    def translate2OriginalUrl(self,url):
        response = requests.get(url, headers=self.headers)
        if response.status_code != 200:
            print(
                "Error occured while fetching the data : " + str(response.status_code)
            )
            # let's try it one more time
            print("Token/cookie is not valid generating new")
            self.get_cookies_and_csrf_token()
            response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text,features="lxml")
            product_url_text = soup.findAll('div',{"wire:initial-data":True})[0]["wire:initial-data"]
            product_url_text = json.loads(product_url_text)
            product_url = product_url_text['serverMemo']['data']['url']
            return product_url
        else:
            print(
                "Error occured while fetching the data : " + str(response.status_code)
            )
        
    def collect(self,url):
        self.data["updates"][0]["payload"]["value"] = url
        response = requests.post(
            self.SEARCH_BOX_URL, headers=self.headers, data=json.dumps(self.data)
        )
        if response.status_code != 200:
            
            # let's try it one more time
            print("Token/cookie is not valid generating new")
            self.get_cookies_and_csrf_token()
            response = requests.post(
                self.SEARCH_BOX_URL, headers=self.headers, data=json.dumps(self.data)
            )
        if response.status_code == 200:
            response = response.json()
            
            response = response["effects"]["emits"][0]["params"][0]
            if isinstance(response, list):
                print(response[0])
                return None
            
            return {
                "response_id": response.get("id"),
                "response_title": response.get("title"),
                "store": response.get("store"),
                "data": np.array(eval(response.get("data"))),
                "product_image": response.get("image"),
                "price_drop_chances": response.get("drop_chance"),
                "product_rating": BeautifulSoup(response.get('rating'),features="lxml").find('div').text
            }
        else:
            print(
                "Error occured while fetching the data : " + str(response.status_code)
            )

            

if __file__=='__main__':
    pass
