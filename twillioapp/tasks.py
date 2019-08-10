import bs4
import requests
from django.conf import settings


def get_alphanumeric_countries():
    country_data_filtered = dict()
    data = requests.get(settings.ALPHA_NUMERIC_COUNTRIES)
    soup = bs4.BeautifulSoup(data.content)
    alpha_countries = soup.find("div", {"class": "article-body markdown"}).find("table").findAll("tr")[1:]
    for alpha_country in alpha_countries:
        country_data = alpha_country.findAll("td")
        country_tmp = country_data[0].find("a")
        country = country_tmp.text if country_tmp else country_data[0].text
        access = country_data[1].text
        country_data_filtered[country] = True if "yes" in access.lower() else False
    return country_data_filtered

