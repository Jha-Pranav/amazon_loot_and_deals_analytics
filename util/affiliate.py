from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import requests
import time
from selenium.webdriver.firefox.options import Options

# Path to selenium driver
PATH = "OnlineLooters\\geckodriver.exe"
AMAZON_USERID = "******"
AMAZON_PASSWORD = "***********"
AMAZON_LOGIN_URL = "https://www.amazon.in/ap/signin?openid.pape.max_auth_age=0&openid.return_to=https%3A%2F%2Fwww.amazon.in%2F%3Fref_%3Dnav_signin&openid.identity=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0%2Fidentifier_select&openid.assoc_handle=inflex&openid.mode=checkid_setup&openid.claimed_id=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0%2Fidentifier_select&openid.ns=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0&/"


def signin(timeout):
    options = Options()
    options.headless = True
    print("Browser instance instantiated")
    driver = webdriver.Firefox(options=options, executable_path=PATH)
    # driver = webdriver.Firefox(executable_path = PATH)
    print("Opening amazon signin page")
    driver.get(AMAZON_LOGIN_URL)
    element_present = EC.presence_of_element_located((By.ID, "ap_email"))
    WebDriverWait(driver, timeout).until(element_present)
    time.sleep(timeout)
    email = driver.find_element_by_id("ap_email")
    email.send_keys(AMAZON_USERID)
    email.submit()
    print("User Id captured")
    element_present = EC.presence_of_element_located((By.ID, "ap_password"))
    WebDriverWait(driver, timeout).until(element_present)
    time.sleep(timeout)
    pswd = driver.find_element_by_id("ap_password")
    pswd.send_keys(AMAZON_PASSWORD)
    pswd.submit()
    print("Pasword Captured")
    element_present = EC.presence_of_element_located((By.ID, "nav-AssociateStripe"))
    WebDriverWait(driver, 600).until(element_present)
    time.sleep(timeout)
    print("Amazon home page successfull opened")
    return driver


async def get_affiliate_url(timeout, driver, url):
    # response = requests.get(url)
    # url = response.url
    driver.get(url)
    element_present = EC.presence_of_element_located(
        (By.CSS_SELECTOR, ".amzn-ss-wrap-content")
    )
    WebDriverWait(driver, timeout).until(element_present)
    time.sleep(timeout)
    driver.find_element_by_css_selector("#amzn-ss-text-link a").click()
    time.sleep(timeout)
    soup = BeautifulSoup(driver.page_source, features="lxml")
    affiliate_url = soup.find(id="amzn-ss-text-shortlink-textarea").text
    return affiliate_url, BeautifulSoup(driver.page_source, "lxml")


if __file__ == "__name__":
    pass
