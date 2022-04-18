# -*- coding: utf-8 -*-
import datetime
import json
import re
import urllib.parse

import scrapy

from locations.items import GeojsonPointItem
from locations.hours import OpeningHours

day_mapping = {
    "MON": "Mo",
    "TUE": "Tu",
    "WED": "We",
    "THU": "Th",
    "FRI": "Fr",
    "SAT": "Sa",
    "SUN": "Su",
}


def convert_24hour(time):
    """
    Takes 12 hour time as a string and converts it to 24 hour time.
    """

    if len(time[:-2].split(":")) < 2:
        hour = time[:-2]
        minute = "00"
    else:
        hour, minute = time[:-2].split(":")

    if time[-2:] == "AM":
        time_formatted = hour + ":" + minute
    elif time[-2:] == "PM":
        time_formatted = str(int(hour) + 12) + ":" + minute

    if time_formatted in ["24:00", "0:00", "00:00"]:
        time_formatted = "23:59"

    return time_formatted


class PetSmartSpider(scrapy.Spider):
    name = "petsmart"
    item_attributes = {"brand": "Petsmart", "brand_wikidata": "Q3307147"}
    allowed_domains = ["petsmart.com", "petsmart.ca"]
    start_urls = (
        "https://www.petsmart.com/store-locator/all/",
        "https://www.petsmart.ca/store-locator/all/",
    )

    def parse(self, response):
        state_urls = response.xpath(
            '//li[@class="col-sm-12 col-md-4"]/a/@href'
        ).extract()
        is_store_details_urls = response.xpath(
            '//a[@class="store-details-link"]/@href'
        ).extract()

        if not state_urls and is_store_details_urls:
            for url in is_store_details_urls:
                yield scrapy.Request(response.urljoin(url), callback=self.parse_store)
        else:
            for url in state_urls:
                yield scrapy.Request(response.urljoin(url))

    def parse_store(self, response):
        if "petsmart.ca" in response.url:
            country = "CA"
        elif "petsmart.com" in response.url:
            country = "US"

        addr_lines = [
            s.strip()
            for s in response.xpath(
                '//p[@class="store-page-details-address"]//text()'
            ).extract()
        ]

        addr_full, city_state_postcode = [s for s in addr_lines if s]
        # n.b. spaces in canadian postcodes
        city, state_postcode = city_state_postcode.split(", ", 1)
        state, postcode = state_postcode.split(" ", 1)

        map_url = response.xpath('//img/@src[contains(.,"staticmap")]').extract_first()
        [lat_lon] = urllib.parse.parse_qs(urllib.parse.urlparse(map_url).query)[
            "center"
        ]
        lat, lon = map(float, lat_lon.split(","))

        properties = {
            "name": urllib.parse.unquote(
                response.xpath("//@data-storename").extract_first()
            ),
            "addr_full": addr_full,
            "city": city,
            "state": state,
            "postcode": postcode,
            "lat": lat,
            "lon": lon,
            "phone": response.xpath(
                'normalize-space(//p[@class="store-page-details-phone"])'
            ).extract_first(),
            "country": country,
            "ref": response.xpath("//@data-storenumber").extract_first(),
            "website": response.url,
        }

        hours = self.parse_hours(
            response.xpath('//*[@itemprop="OpeningHoursSpecification"]')
        )

        if hours:
            properties["opening_hours"] = hours

        yield GeojsonPointItem(**properties)

    def parse_hours(self, elements):
        opening_hours = OpeningHours()

        days = elements.xpath('.//span[@itemprop="dayOfWeek"]/text()').extract()
        today = (set(day_mapping) - set(days)).pop()
        days.remove("TODAY")
        days.insert(0, today)
        open_hours = elements.xpath('.//time[@itemprop="opens"]/@content').extract()
        close_hours = elements.xpath('.//time[@itemprop="closes"]/@content').extract()

        store_hours = dict(
            (z[0], list(z[1:])) for z in zip(days, open_hours, close_hours)
        )

        for day, hours in store_hours.items():
            if "CLOSED" in hours:
                continue
            opening_hours.add_range(
                day=day_mapping[day],
                open_time=convert_24hour(hours[0]),
                close_time=convert_24hour(hours[1]),
            )
        return opening_hours.as_opening_hours()
