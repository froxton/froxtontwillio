import bs4
import requests
from django.conf import settings
from .models import AlphaNumericCountries


def get_alphanumeric_countries():
    data = requests.get(settings.ALPHA_NUMERIC_COUNTRIES)
    soup = bs4.BeautifulSoup(data.content)
    alpha_countries = soup.find("div", {"class": "article-body markdown"}).find("table").findAll("tr")[1:]
    countries = []
    for alpha_country in alpha_countries:
        country_data = alpha_country.findAll("td")
        country_tmp = country_data[0].find("a", href=True)
        country = country_tmp.text if country_tmp else country_data[0].text
        alpha = True if "yes" in country_data[1].text.lower() else False
        href = country_tmp.get("href") if country_tmp else None

        if href:
            alpha_country_data = requests.get(href)
            new_soup = bs4.BeautifulSoup(alpha_country_data.content)
            data = new_soup.find("table", {"class": "table country-table"})
            if data:
                tbody = data.find("tbody")
                if tbody:
                    th = tbody .find("th", text="Dialing code")
                    if th:
                        dial_code = th.parent.find("td").text
                        countries.append(AlphaNumericCountries(country=country, code=dial_code, is_alpha=alpha))
                        print(country)

    AlphaNumericCountries.objects.bulk_create(countries)
    print("DONE")
