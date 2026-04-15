from scrapling.spiders import Spider, Response, Request
from src.utils.string_transform import transform_to_markdown
from scrapling.fetchers import AsyncDynamicSession, FetcherSession

IMAGE_FORMATS = ["jpg", "jpeg", "png", "gif", "bmp", "tiff", "tif", "webp", "svg", "ico", "heic", "heif", "avif"]

class BaseSpider(Spider):
    name = ""
    start_urls = []
    allowed_domains = []
    log_file = ""

    def __init__(self, spider_name, urls, log_file, **kwargs):

        self.log_file = log_file
        self.name = spider_name
        self.set_urls(urls)
        super().__init__(**kwargs)

    def configure_sessions(self, manager):
        manager.add("default", FetcherSession())

    async def parse(self, response: Response):
        # Extract items from the current page
        if not self.is_login(response.url):
            yield {
                "content": transform_to_markdown(response.get_all_text()),
                "url": response.url,
            }

        # Follow the "next page" link
        next_page = response.xpath("//a[contains(@href, '')]")

        if next_page:
            for page in next_page:
                try:
                    url = page.attrib["href"]
                except KeyError:
                    continue
                if self.is_extension(url):
                    yield response.follow(url, callback=self.parse)

    def set_urls(self, url):
        if len(self.start_urls) > 1:
            self.start_urls.pop(0)
            self.start_urls.append(url)
        else:
            self.start_urls.append(url)
        if len(self.allowed_domains) > 1:
            self.allowed_domains.pop(0)
            self.allowed_domains.append(url.replace("/", "").replace("https:", ""))
        else:
            self.allowed_domains.append(url.replace("/", "").replace("https:", ""))

    @staticmethod
    def is_extension(url):
        """Retorna True se a extensão do arquivo NÃO estiver na lista de formatos."""
        # Extrai a parte após o último ponto (case insensitive)
        if '.' in url:
            extensao = url.split('.')[-1].lower()
            if extensao in IMAGE_FORMATS:
                return False
        return True

    @staticmethod
    def is_login(url):
        login = ["login"]
        if url.split('/')[-1].lower() in login:
            return True
        return False
