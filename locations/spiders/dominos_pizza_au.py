import re

import scrapy

from locations.items import GeojsonPointItem


class DominosPizzaAUSpider(scrapy.Spider):
    name = "dominos_pizza_au"
    item_attributes = {"brand": "Domino's", "brand_wikidata": "Q839466"}
    allowed_domains = ["dominos.com.au"]

    start_urls = ("https://www.dominos.com.au/stores",)

    def parse(self, response):
        store_urls = response.xpath('//link[@rel="canonical"]/@href').extract()
        for store_url in store_urls:
            yield scrapy.Request(response.urljoin(store_url), callback=self.parse_region)

    def parse_region(self, response):
        regions = response.xpath('//ul[@id="region-links"]/li/a/@href').extract()
        for region in regions:
            yield scrapy.Request(response.urljoin(region), callback=self.parse_locality)

    def parse_locality(self, response):
        stores = response.xpath('//div[@class="store-information"]/h4/a/@href').extract()
        for store in stores:
            yield scrapy.Request(response.urljoin(store), callback=self.pares_store)

    def pares_store(self, response):
        ref = re.search(r".+-(.+?)/?(?:\.html|$)", response.url).group(1)
        country = re.search(r"com\.([a-z]{2})\/", response.url).group(1)
        address_data = response.xpath('//a[@id="open-map-address"]/text()').extract()
        address = " "
        addr_full = address.join(address_data)
        properties = {
            "ref": ref.strip("/"),
            "name": response.xpath('//div[@class="storetitle"]/text()').extract_first(),
            "addr_full": addr_full.strip(),
            "country": country,
            "lat": float(response.xpath('//div[@class="store-details-info"]/div[1]/input[1]/@value').extract_first()),
            "lon": float(response.xpath('//div[@class="store-details-info"]/div[1]/input[2]/@value').extract_first()),
            "website": response.url,
        }
        yield GeojsonPointItem(**properties)
