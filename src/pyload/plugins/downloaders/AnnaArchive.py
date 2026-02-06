
import re
import requests

from pyload.core.utils import parse

from ..base.simple_downloader import SimpleDownloader
from ..helpers import search_pattern



class AnnaArchive(SimpleDownloader):
    __name__ = "AnnaArchive_Welib"
    __type__ = "downloader"
    __version__ = "0.01"
    __status__ = "testing"

    __pattern__ = r"(?i)https?://(?:fr\.)?(annas-archive|welib)\.(org|se|li)/.*"
    __config__ = [
        ("enabled", "enabled", "Activated", True),
        ("use_premium", "bool", "Use premium account if available", False),
        ("fallback", "bool", "Fallback to free download if premium fails", True),
        ("chunk_limit", "int", "Default number of chunk", 1),
        ("resume_download", "bool", "Option to resume download in case of issue", True),
        ("flaresolverr_url", "string", "flaresolverr url for cloudflare bypass", "http://127.0.0.1:8191/v1"),
        ("flaresolverr_max_timeout", "int", "Max timeout for cloudflare challenge (in seconde)", 60),
        ("extension_regexp", "string", "", "pdf|epub|zip|mobi|fb2|cbr|djvu|cbz|doc|rtf|rar|docx|tar|7z|gz|cb7")

    ]

    __description__ = """Plugin for AnnaArchive / Welib (need flaresolverr)"""
    __license__ = "GPLv3"
    __authors__ = [("Flov91", "flov91@GITHUB")]


    INFO_PATTERN = (
        r'<div class="text-sm text-gray-500">.*?,\s*'       # Skip language
        r'.*?,\s*'                                          # Skip extension
        r'.*?,\s*'                                          # Skip path
        r'(?P<S>[\d.]+)\s*(?P<U>[KMGT]?B),\s*'              # File size & unit
        r'.*?,\s*'                                          # Skip category
        r'(?P<N>[^<]+?)'                                    # File name (until </div>)
        r'</div>'
    )

    # NAME_PATTERN = (
    #     r'<div class="text-sm text-gray-500">.*?,\s*'   # skip language
    #     r'.*?,\s*'                                      # skip extension
    #     r'.*?,\s*'                                      # skip path
    #     r'[\d.]+\s*[KMGT]?B,\s*'                        # skip size
    #     r'.*?,\s*'                                      # skip category
    #     r'(?P<N>[^<]+?)'                                # capture filename
    #     r'</div>'
    # )

    # SIZE_PATTERN = (
    #     r'<div class="text-sm text-gray-500">.*?,\s*'   # skip language
    #     r'.*?,\s*'                                      # skip extension
    #     r'.*?,\s*'                                      # skip path
    #     r'(?P<S>[\d.]+)\s*(?P<U>[KMGT]?B)'              # capture size + unit
    # )

    OFFLINE_PATTERN = r'File Not Found'
    LINK_FREE_PATTERN = r"(/slow_download/.*?)['|\"]"
    URL_FREE_PATTERN = r"(/slow_download/)"
    LINK_PREMIUM_PATTERN = r"(/fast_download/.*?)['|\"]"
    DL_LIMIT_PATTERN = r' slow down '

    def setup(self):
        self.multi_dl = False
        self.FINAL_LINK_PATTERN = rf"(https://.*?\.(?:{self.config.get("extension_regexp")}))['|\"]"
        self.chunk_limit = self.config.get("chunk_limit") # 1
        self.resume_download = self.config.get("resume_download") # True
        self.flaresolverr_url = self.config.get("flaresolverr_url")
        self.flaresolverr_max_timeout = self.config.get("flaresolverr_max_timeout")


    def flaresolverr_request(self, url, waitInSeconds=0):
            payload = {
                "cmd": "request.get",
                "url": url,
                "maxTimeout": ((self.flaresolverr_max_timeout + waitInSeconds) * 1000),
                "waitInSeconds": waitInSeconds
            }
            try:
                response = requests.post(self.flaresolverr_url, json=payload)
                response.raise_for_status()
                data = response.json()
                if data.get("status") == "ok":
                    return data["solution"]["response"]
                else:
                    self.log_error("FlareSolverr error: {}".format(data.get("message")))
                    return None
            except Exception as e:
                self.log_error("FlareSolverr request failed: {}".format(e))
                return None

    def handle_direct(self, pyfile):
        print(self.link)
        print(pyfile.url)
        print('#############################################################################"')
        if search_pattern(self.URL_FREE_PATTERN, pyfile.url):
            cloud_url = self.flaresolverr_request(pyfile.url, 70)
            if cloud_url:
                m = re.search(self.FINAL_LINK_PATTERN, cloud_url.replace('\\n', '').replace('\\"', '"'))
                if m:
                    link = self.isresource(m.group(1))
                    if link:
                        pyfile.name = parse.name(link)
                        self.link = m.group(1)
                    else:
                        self.link = None
                else:
                    self.link = None
                #     self.error(self._("Free download link not found on final page"))
            else:
               self.error(self._("Issue with flaresollverr")) 
        else:
            self.link = None

    def handle_free(self, pyfile):
        if not self.LINK_FREE_PATTERN:
            self.fail(self._("Free download not implemented"))

        m = search_pattern(self.LINK_FREE_PATTERN, self.data)
        if m:            
            self.base_url = re.search(r"^(https?://[^/]+)", pyfile.url).group(1)
            slow_url = self.base_url + m.group(1)
            self.log_info(f"Free download inter link found '{slow_url}' going to flaresolverr")
            slow_page = self.flaresolverr_request(slow_url, 70).replace('\\n', '').replace('\\"', '"')
            m = re.search(self.FINAL_LINK_PATTERN, slow_page)
            if m:
                self.link = m.group(1)
            # else:
            #     self.error(self._("Free download link not found on final page"))
        # else:
        #     self.error(self._("Free download link not found"))


    def handle_premium(self, pyfile):
        self.log_warning(self._("Premium download not implemented yet"))
        self.restart(premium=False)
