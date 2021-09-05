import configparser
import json
from matplotlib.markers import MarkerStyle
import requests
from telethon import TelegramClient, events
from telethon.client import messages
from telethon.errors import SessionPasswordNeededError

# import pandas.util.testing as tm
from bs4 import BeautifulSoup
from util.affiliate import signin, get_affiliate_url
from util.PriceHistory import CollectData

import matplotlib.ticker as mticker
import urllib.request
from PIL import Image
import pandas as pd
import time

from datetime import datetime
import numpy as np
import re
import matplotlib.pyplot as plt
from colorsys import rgb_to_hsv, hsv_to_rgb
from colorthief import ColorThief

# import logging
# logging.basicConfig(format='[%(levelname) 5s/%(a sctime)s] %(name)s: %(message)s',
#                     level=logging.WARNING)

VISITED_URL = []
VISITED_ASIN = []

rgb_mapping = {
    "black": (0, 0, 0),
    "white": (255, 255, 255),
    "red": (255, 0, 0),
    "lime": (0, 255, 0),
    "blue": (0, 0, 255),
    "yellow": (255, 255, 0),
    "cyan": (0, 255, 255),
    "magenta": (255, 0, 255),
    "silver": (192, 192, 192),
    "gray": (128, 128, 128),
    "maroon": (128, 0, 0),
    "olive": (128, 128, 0),
    "green": (0, 128, 0),
    "purple": (128, 0, 128),
    "navy": (0, 0, 128),
}

# import sys
# sys.stdout = open('output.txt','w',encoding='utf-8')

# Reading Configs
config = configparser.ConfigParser()
config.read("config.ini")

# Setting configuration values
api_id = config["Telegram"]["api_id"]
api_hash = config["Telegram"]["api_hash"]

phone = config["Telegram"]["phone"]
username = config["Telegram"]["username"]

client = TelegramClient(username, api_id, api_hash)

############### Image Processing #############
# sns.set_style("white")
# sns.set(rc={'figure.figsize':(5,5)})
plt.subplots_adjust(
    left=None, bottom=None, right=None, top=None, wspace=None, hspace=None
)
# plt.rcParams['title_fontsize'] = 16


def complementary(r, g, b):
    """returns RGB components of complementary color"""
    hsv = rgb_to_hsv(r, g, b)
    return hsv_to_rgb((hsv[0] + 0.5) % 1, hsv[1], hsv[2])


async def reduce_image_size(image_path, size=(288, 360)):
    img = Image.open(image_path)
    img = img.resize(size, Image.ANTIALIAS)
    img.save(image_path, quality=95)
    img.close()


async def take_screen_shots(file_name):
    print("Taking screenshot")
    element = DRIVER.find_element_by_css_selector("a-container")
    if element:
        element_png = element.screenshot_as_png
        with open(f"data\\{file_name}", "wb") as file:
            file.write(element_png)
        await reduce_image_size(f"data\\{file_name}")
        return True
    return False


async def download_image(data):
    image_url = data["product_image"]
    file_name = image_url.split("/")[-1]
    print("Downloading product image")
    try:
        urllib.request.urlretrieve(image_url, f"data\\{file_name}")
        print("Product image downloaded")
    except BaseException as e:
        print("Error occurred while downloading the image")
        print("Error : ", e)
        return file_name, None, None
    img = Image.open(f"data\\{file_name}")
    # img = img.resize((200, 220), Image.ANTIALIAS)print('Finding best contrast color')
    color_thief = ColorThief(f"data\\{file_name}")
    print("Get the most dominant color")
    dominant_color = color_thief.get_color(quality=1)
    # best_color = (255 - np.array(dominant_color))/255
    best_color = np.array(complementary(*dominant_color)) / 255

    return file_name, img, best_color


async def plot_graph(data_points, best_color):
    x_axis = data_points[:, 0]
    y_axis = data_points[:, 1]
    fig, ax = plt.subplots(tight_layout=True)
    ax.plot(data_points[-1, 0], data_points[-1, 1], "g*", markersize=20)
    ax.plot(x_axis, y_axis, c="m", linewidth=2.5)
    fig.suptitle("Pilfers", fontname="Comic Sans MS", fontsize=12, fontweight="bold")
    plt.title("Should i purchase now ?", loc="left")

    # ax.plot(x_axis, middle_bound, x_axis, lower_bound, x_axis, upper_bound)
    return fig, ax


async def image_processing(data):
    data_points = data["data"]
    data_points = data_points[data_points[:, 1] != 0]
    file_name, img, best_color = await download_image(data)
    if not img:
        return None
    fig, ax = await plot_graph(data_points, best_color)
    print("Transforming image to numpy array")
    map_img = np.asarray(img)
    xticks = [datetime.utcfromtimestamp(i) for i in ax.get_xticks() / 1000]
    # fig.xaxis.set_major_locator(mticker.FixedLocator(xticks))
    ax.set_xticklabels([i.strftime("%d %b %y") for i in xticks], rotation=30)
    ax.imshow(
        map_img,
        aspect=ax.get_aspect(),
        extent=ax.get_xlim() + ax.get_ylim(),
        zorder=1,
    )
    print("Saving updated image")
    ax.figure.savefig(f"data\\{file_name}")
    await reduce_image_size(f"data\\{file_name}")
    return file_name


regex = r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))"


async def data_analysis(data, current_price):
    data_points = data["data"]
    df = pd.DataFrame(data_points)
    df.columns = ["TimeStamp", "Price"]
    lowest_price = df["Price"].min()
    highest_price = df["Price"].max()
    regular_price = df["Price"].mode()[0]
    # discont %
    relative_percent = 0
    if (highest_price - lowest_price) > 0:
        relative_percent = (
            (highest_price - current_price) / (highest_price - lowest_price)
        ) * 100

    return regular_price, relative_percent


async def data_operation(current_price, data):
    regular_price, relative_percent = await data_analysis(data, current_price)
    print("Relative discount is : ", relative_percent)
    if (relative_percent < 40) or (current_price > regular_price):
        print("Relative discount is less than 40 percent droping this deal")
        return None, None, None, None
    # if regular_price <= current_price:
    #     regular_price = current_price
    print("Relative % : ", relative_percent)
    # Append current price to the data
    current_price_index = [int(time.time() * 1000), current_price]
    data["data"] = np.append(data["data"], [current_price_index], axis=0)
    print("Working on image processing")
    file_name = await image_processing(data)
    print("Image has been processed successfully.")
    rating = float(data.get("product_rating"))
    price_drop_chances = data.get("price_drop_chances")
    return regular_price, file_name, rating, price_drop_chances


async def send_messages(file_name, msg):
    if msg:
        if file_name:
            print("Sending msg with image")
            await client.send_file(
                "Online Looters: One-Stop shop for every deal",
                f"data\\{file_name}",
                caption=msg,
                link_preview=False,
            )
        else:
            print("Sending msg without image")
            await client.send_message(
                "Online Looters: One-Stop shop for every deal", msg, link_preview=False
            )
    else:
        print("Empty message can not be send")


async def amazon_store(url):
    ASIN = re.findall(r"(?:[/dp/]|$)([A-Z0-9]{10})", url)
    print("ASIN id is : ", ASIN)
    if not ASIN:
        print("Collecting affiliate url")
        short_url, page_source = await get_affiliate_url(3, DRIVER, url)
        DRIVER.refresh()
        if not short_url:
            short_url, page_source = await get_affiliate_url(3, DRIVER, url)

        if not short_url:
            return False, None

        print(">>", short_url)
        page_title = page_source.find(
            "div", {"class": lambda x: x and x.endswith("page-title")}
        )
        if page_title:
            page_title = page_title.text.split("\n")[0]
        else:
            page_title = ""

        category = (
            page_source.find(attrs={"selected": "selected"})["value"]
            .split("=")[-1]
            .upper()
        )
        msg = f"#{category} [Amazon]\n{page_title}\n🔗 {short_url}"
        image_file_name = short_url.split("/")[-1] + ".png"
        is_ss_taken = await take_screen_shots(file_name=image_file_name)
        if is_ss_taken:
            await send_messages(image_file_name, msg)
        else:
            await send_messages(False, msg)
        return False, msg
    else:
        ASIN = ASIN[0]
        if ASIN in VISITED_ASIN:
            return False, None
        else:
            VISITED_ASIN.append(ASIN)
        print("Collecting affilate url")
        short_url, page_source = await get_affiliate_url(3, DRIVER, url)
        print(">>?>", short_url)

        if not short_url:
            # Try it one more time
            short_url, page_source = await get_affiliate_url(3, DRIVER, url)
        if not short_url:
            VISITED_ASIN.remove(ASIN)
            return False, None
        category = (
            page_source.find(attrs={"selected": "selected"})["value"]
            .split("=")[-1]
            .upper()
        )
        print("category : ", category)
        coupon = page_source.find(id=lambda value: value and value.endswith("Coupon"))
        if coupon:
            coupon = coupon.text.strip().split("\n")[0]
        else:
            coupon = ""
        print("coupon : ", coupon)
        product_rank = page_source.select_one(
            "#productDetails_detailBullets_sections1 tr:nth-child(3) td"
        )
        if product_rank:
            product_rank = product_rank.text
            product_rank = re.findall(
                r"#\d+",
                "\n\n#228 in Computers & Accessories (See Top 100 in Computers & Accessories)\n\n#3 in Tablets\n\n\n",
            )[-1]
            product_rank = int(re.findall(r"\d+", product_rank)[0])
        else:
            product_rank = ""
        print("Rank : ", product_rank)
        current_price = page_source.find(
            id=lambda value: value
            and value.startswith("priceblock")
            and value.endswith("price")
        )
        if current_price:
            current_price = current_price.text.replace(",", "")
            current_price = float(re.findall("\d+\.\d+", current_price)[0])
        else:
            return False, None
        print("Current prie : ", current_price)

        title = page_source.find(id="productTitle")
        if title:
            title = title.text.strip()
            if len(title) > 80:
                title = title[:75] + "..."
        print("Title : ", title)
        additional_offers = page_source.find(id="sopp_feature_div")
        if additional_offers:
            additional_offers = additional_offers.text
            additional_offers = " | ".join(
                set(
                    re.findall(
                        r"No Cost EMI|Exchange Offer|Bank Offer", additional_offers
                    )
                )
            )
        else:
            additional_offers = ""
        print("Additional Offers : ", additional_offers)
        data = price_history.collect(url)
        if data:
            regular_price, file_name, rating, price_drop_chances = await data_operation(
                current_price, data
            )

            # worthiness = (rating * relative_percent)/np.log2(product_rank)

            msg = f"#{category} [Amazon]\n```{title}```\n"
            if coupon or additional_offers:
                msg += f"👌 **{coupon} {additional_offers}** \n"
            msg += f'📌 **₹ {current_price}**{" " *10}⚠️~~ ₹ {regular_price} ~~\n'
            msg += f'\n🔗 {short_url}\n\n⭐Rating: **{rating}{" " *5}** Product Rank: **{product_rank}** \n📉Drop Chances: **{price_drop_chances}%**'
            if (1 - (current_price / regular_price)) > 0.75:
                await client.send_message("My Dear", msg, link_preview=False)
            await send_messages(file_name, msg)
            return file_name, msg
        else:
            msg = f"#{category} [Amazon]\n```{title}```\n"
            if coupon or additional_offers:
                msg += f"👌 **{coupon}** {additional_offers}\n"
            msg += f"📌Current Price: ** {current_price}**\n"
            msg += f"\n🔗 {short_url}\nProduct Rank: **{product_rank}**"
            print("???", msg)
            await send_messages(False, msg)
            return False, msg


async def handler(event):
    start = datetime.now()
    print(f"Operation started for : {event.chat_id}")
    text = event.text
    print("***" * 20)
    url_list = [i for matches in re.findall(regex, text) for i in matches]
    print("Translate url to original product urls : ", url_list)
    ## bit.ly
    url_list += [requests.get(link).url for link in url_list if "bit" in link]
    ## Price History
    url_list += [
        price_history.translate2OriginalUrl(i) for i in url_list if "pricehistory" in i
    ]
    amzn_url_list = [
        requests.get(i).url for i in url_list if ("amzn" in i or "amazon" in i)
    ]

    # Incase of incorrect url it will redirect to homepage
    amzn_url_list = [i for i in amzn_url_list if i != "https://www.amazon.com/"]
    amzn_url_list = set(amzn_url_list).difference(VISITED_URL)

    VISITED_URL.extend(amzn_url_list)

    if amzn_url_list:
        [await amazon_store(url) for url in amzn_url_list]
    else:
        print("Message can not be send because one of the following reasons")
        print(">>", "We are not affiliated to this website yet")
        print(">>", "Url is not valid")
        print(">>", "This message has alredy been sent in this session")
    print(
        f"The operation completed for {event.chat_id}",
        "Time elapse : ",
        (datetime.now() - start).seconds,
    )


if __name__ == "__main__":
    DRIVER = signin(10)
    price_history = CollectData()
    try:

        @client.on(events.NewMessage(func=lambda e: e.is_channel))
        async def main(event):
            await handler(event)

        with client:
            client.run_until_disconnected()
    except BaseException as e:
        print("Error occurred : ")
        print(e)
    finally:
        DRIVER.close()
