from scrapy.crawler import Crawler

from locations.items import GeojsonPointItem
from locations.pipelines import CountryCodeCleanUpPipeline
from locations.spiders.greggs_gb import GreggsGBSpider


def get_objects(spider_name):
    class Spider(object):
        pass

    spider = Spider()
    spider.name = spider_name
    spider.crawler = Crawler(GreggsGBSpider)
    return GeojsonPointItem(), CountryCodeCleanUpPipeline(), spider


def test_handle_empty():
    item, pipeline, spider = get_objects("meaningless")
    pipeline.process_item(item, spider)
    assert not item.get("country")


def test_country_from_spider_name():
    item, pipeline, spider = get_objects("greggs_gb")
    pipeline.process_item(item, spider)
    assert "GB" == item.get("country")
    assert 1 == spider.crawler.stats.get_value("atp/field/country/from_spider_name")


def test_country_from_website_url():
    item, pipeline, spider = get_objects("greggs")
    item["website"] = "https://www.greggs.co.uk/index.html"
    pipeline.process_item(item, spider)
    assert "GB" == item.get("country")
    assert 1 == spider.crawler.stats.get_value("atp/field/country/from_website_url")
