from .ScraperUtils import Link, PhrasesMode
from queue import Queue

import requests
from bs4 import BeautifulSoup


class WebScraper:
    def __init__(self):
        self.max_links_number = 0
        self.__current_links_number = 0
        self.set = set()
        self.excluded_links_phrases = ["login"]
        self.accepted_content_type = ["text/html"]
        self.searched_phrases = ["*"]
        self.max_link_size = -1
        self.max_depth = -1
        self.element_types = ['p']
        self.results_name = "results.txt"
        self.save_links = True
        self.links_name = "links.txt"
        self.phrases_mode = PhrasesMode.AND
        self.queue = Queue()

    def read_crawl_site_queue(self, start):

        self.queue.put_nowait(Link(start, start, 0))

        while not self.queue.empty():
            try:
                [link, base, depth] = self.queue.get_nowait().get()
                if self.max_link_size != -1 and len(link) > self.max_link_size:
                    continue
                if self.max_depth != -1 and depth > self.max_depth:
                    continue
                response = requests.head(link)
                if response.headers.get('content-type').split(';')[0] not in self.accepted_content_type:
                    print(f"Link {link} incompatible content type")
                    continue

                if self.max_links_number > 0:
                    if self.__current_links_number > self.max_links_number:
                        return
                    self.__current_links_number += 1

                site = requests.get(link).text
                if self.save_links:
                    with open(self.links_name, "a+") as f:
                        f.write(f"{link},")
                soup = BeautifulSoup(site, "lxml")
                articles = []
                for i in self.element_types:
                    articles.extend([i.text for i in soup.find_all(i)])

                if self.searched_phrases == ["*"]:
                    for i in articles:
                        with open(self.results_name, "a+") as f:
                            f.write(f"From {link}:\n")
                            f.write(i)
                elif not self.searched_phrases:
                    for i in articles:
                        print(i)
                else:
                    for i in articles:
                        if self.check_for_phrases(i):
                            with open(self.results_name, "a+") as f:
                                f.write(f"From {link}:\n")
                                f.write(f"{i}\n")
                links = [i.attrs['href'] for i in soup.find_all('a')]

                for i in links:
                    if i.strip("/") in self.set or f"{base}{i}".strip("/") in self.set or self.check_for_excluded_phrases(f"{i}"):
                        continue
                    if i[0] == "/" and len(i) > 1:
                        print(f"Getting Site {base}{i}")
                        self.set.add(f"{base}{i}".strip("/"))
                        self.queue.put_nowait(Link(f"{base}{i}", f"{base}", depth + 1 if self.max_depth != -1 else 0))
                    elif i[0] != '#' and len(i) > 1:
                        print(f"Getting URL {i}")
                        self.set.add(i.strip("/"))
                        self.queue.put_nowait(Link(f"{i}", f"{i}", 0))
            except Exception as e:
                print(f"Code couldn't execute with the following message: {e}")
                continue

    def read_crawl_site_recursive(self, base, link, depth=0):
        try:
            if self.max_link_size != -1 and len(link) > self.max_link_size:
                return
            if self.max_depth != -1 and depth > self.max_depth:
                return
            response = requests.head(link)
            if response.headers.get('content-type').split(';')[0] not in self.accepted_content_type:
                print(f"Link {link} incompatible content type")
                return

            site = requests.get(link).text
            if self.save_links:
                with open(self.links_name, "a+") as f:
                    f.write(f"{link}")
            soup = BeautifulSoup(site, "lxml")
            articles = []
            for i in self.element_types:
                articles.extend([i.text for i in soup.find_all(i)])

            if self.searched_phrases == ["*"]:
                for i in articles:
                    with open(self.results_name, "a+") as f:
                        f.write(f"From {link}:\n")
                        f.write(i)
            elif not self.searched_phrases:
                for i in articles:
                    print(i)
            else:
                for i in articles:
                    if self.check_for_phrases(i):
                        with open(self.results_name, "a+") as f:
                            f.write(f"From {link}:\n")
                            f.write(i)
            links = [i.attrs['href'] for i in soup.find_all('a')]

            for i in links:
                if i.strip("/") in self.set or f"{base}{i}".strip("/") in self.set or self.check_for_excluded_phrases(f"{i}"):
                    continue
                if i[0] == "/" and len(i) > 1:
                    print(f"Getting Site {base}{i}")
                    self.set.add(f"{base}{i}".strip("/"))
                    self.read_crawl_site_recursive(f"{base}", f"{base}{i}", depth + 1 if self.max_depth != -1 else 0)
                elif i[0] != '#' and len(i) > 1:
                    print(f"Getting URL {i}")
                    self.set.add(i.strip("/"))
                    self.read_crawl_site_recursive(f"{i}", f"{i}")
        except Exception as e:
            print(f"Code couldn't execute with the following message: {e}")
            return

    def check_for_excluded_phrases(self, link):
        for i in self.excluded_links_phrases:
            if link.find(i) != -1:
                return True
        return False

    def check_for_phrases(self, article):
        if self.phrases_mode == PhrasesMode.AND:
            result = True
            for i in self.searched_phrases:
                result = result and article.lower().find(i.lower()) != -1
            return result
        elif self.phrases_mode == PhrasesMode.OR:
            for i in self.searched_phrases:
                if article.lower().find(i.lower()) != -1:
                    return True
        return False

    def read_links(self):
        try:
            with open(self.links_name, "r") as f:
                links = f.read()
                [self.set.add(i) for i in links.split(",")[:-1]]
        except FileNotFoundError as e:
            return
