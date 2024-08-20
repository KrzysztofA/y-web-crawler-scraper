import asyncio
from asyncio import Queue

import aiofiles
import requests
from ruia import Item, TextField, AttrField
from WebCrawlerScraper import PhrasesMode, Link


class InfoItem(Item):
    info = TextField(css_select="div", many=True)


class UrlsItem(Item):
    urls = AttrField(css_select="a", attr="href", many=True)


class WebScraperAsync:
    def __init__(self):
        self.max_links_number = 0
        self.set = set()
        self.excluded_links_phrases = ["login"]
        self.accepted_content_type = ["text/html"]
        self.searched_phrases = ["*"]
        self.max_link_size = -1
        self.max_depth = -1
        self.element_types = ['div']
        self.link_types = ['a']
        self.results_name = "results.txt"
        self.save_links = True
        self.links_name = "links.txt"
        self.phrases_mode = PhrasesMode.AND
        self.queue = Queue()
        self.verbosity = 1
        self.__css_select_info = None
        self.__css_select_urls = None
        self.build_css_select()

    async def start_crawl_scrap(self, link):
        self.build_css_select()
        cors = []
        finish = False
        starting_link = Link(link, link, 0)
        await self.queue.put(starting_link)
        # Start main scrapping-indexing loop
        while not self.queue.empty() or not finish:
            if self.verbosity > 2:
                print("Queue Loop")
            cors.append(asyncio.ensure_future(self.start_request_from_link()))
            await asyncio.sleep(1)
            if self.queue.empty():
                if self.verbosity > 2:
                    print("Queue may be empty")
                await asyncio.gather(*cors)
                if self.queue.empty():
                    finish = True
        if self.verbosity > 0:
            print("Queue finished")
        await asyncio.gather(*cors)

    async def start_request_from_link(self):
        link = await self.queue.get()
        try:
            response = requests.head(link.link)
            if response.headers.get('content-type').split(';')[0] not in self.accepted_content_type:
                print(f"Link {link} incompatible content type")
                return
            res = requests.get(link.link)
            res = res.text
            cors = [self.get_information(res, link.link), self.get_links(res, link), self.write_link_to_file(link.link)]
            await asyncio.gather(*cors)
        except Exception as e:
            if self.verbosity > 0:
                print(f"Code couldn't execute with the following message: {e}")

    async def write_results_to_file(self, res, link):
        cors = [self.write_result_to_file(art, link) for art in res]
        await asyncio.gather(*cors)

    async def write_result_to_file(self, art, link):
        if not self.save_links:
            return
        async with aiofiles.open(self.results_name, "a+") as f:
            await f.write(f"From {link}:\n")
            await f.write(art)

    async def get_information(self, html, link):
        info = await InfoItem.get_item(html=html)
        info_data = [i for i in filter(lambda x: self.check_results_for_phrases(x), info.info)]
        await self.write_results_to_file(info_data, link)

    async def get_links(self, html, link):
        info = await UrlsItem.get_item(html=html)
        info = [i for i in filter(lambda x: not self.check_links_for_excluded_phrases(x), info.urls)]
        cors = [self.add_link_to_queue(i, link) for i in info]
        await asyncio.gather(*cors)

    async def write_links_to_file(self, links):
        cors = [self.write_link_to_file(link) for link in links]
        await asyncio.gather(*cors)

    async def write_link_to_file(self, link):
        async with aiofiles.open(self.links_name, mode='a+') as f:
            if self.verbosity > 1:
                print(f"Writing {link} to file")
            await f.write(f"{link},")

    async def add_link_to_queue(self, i, slink):
        link = slink.link
        base = slink.base
        depth = slink.depth
        if i.strip("/") in self.set or f"{base}{i}".strip("/") in self.set or len(i) > self.max_link_size or depth > self.max_depth:
            if self.verbosity > 2:
                print(f"Discarding site {i}")
            return
        if i[0] == "/" and len(i) > 1:
            if self.verbosity > 1:
                print(f"Getting Site {base}{i}")
            self.set.add(f"{base}{i}".strip("/"))
            await self.queue.put(Link(f"{base}{i}", f"{base}", depth + 1 if self.max_depth != -1 else 0))
        elif i[0] != '#' and len(i) > 1:
            if self.verbosity > 1:
                print(f"Getting URL {i}")

            self.set.add(i.strip("/"))
            await self.queue.put(Link(f"{i}", f"{i}", 0))

    def check_links_for_excluded_phrases(self, link):
        if type(link) is type(None):
            return True
        for i in self.excluded_links_phrases:
            if link.find(i) != -1:
                return True
        return False

    def check_results_for_phrases(self, res):
        if type(res) is type(None):
            return False
        if self.phrases_mode == PhrasesMode.AND:
            result = True
            for i in self.searched_phrases:
                result = result and res.lower().find(i.lower()) != -1
            return result
        elif self.phrases_mode == PhrasesMode.OR:
            for i in self.searched_phrases:
                if res.lower().find(i.lower()) != -1:
                    return True
        return False

    def build_css_select(self):
        self.__css_select_info = ", ".join(self.element_types) if self.element_types[0] != "*" else "*"
        self.__css_select_urls = ", ".join(self.link_types) if self.link_types[0] != "*" else "*"
