import re
import time
import json
from tqdm import tqdm
from typing import Optional
from selenium import webdriver
from urllib.parse import urlparse
from dataclasses import dataclass, asdict
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

@dataclass
class ListItem:
    name: str
    url: str
    is_folder: bool
    expected_items: Optional[int]
    items: list
    depth: int

class Flatten:

    def __init__(
        self,
        start_url,
        fed_auth,
        debug,
        debug_path,
        output_path,
        wait_timeout,
        max_depth,
        height_based_scroll_time,
        item_based_scroll_time,
        scroll_delta,
    ) -> None:
        self.start_url = start_url
        self.debug = debug
        self.scheme = urlparse(start_url).scheme
        self.domain = urlparse(start_url).netloc
        self.debug_path = debug_path
        self.output_path = output_path
        self.height_based_scroll_time = height_based_scroll_time
        self.item_based_scroll_time = item_based_scroll_time
        self.wait_timeout = wait_timeout
        self.scroll_container_class = "od-ItemsScopeItemContent-list"
        self.max_depth = max_depth
        self.scroll_delta = scroll_delta

        chrome_options = Options()
        chrome_flags = [
            "--headless",
            "--window-size=1920x1080",
            "--no-sandbox",
            "--disable-infobars", # https://stackoverflow.com/a/43840128/1689770
            "--disable-dev-shm-usage", # https://stackoverflow.com/a/50725918/1689770
            "--disable-browser-side-navigation", # https://stackoverflow.com/a/49123152/1689770
            "--disable-gpu", # https://stackoverflow.com/questions/51959986/how-to-solve-selenium-chromedriver-timed-out-receiving-message-from-renderer-exc
            "--disable-features=VizDisplayCompositor", # https://stackoverflow.com/a/55371396/491553
        ]
        for flag in chrome_flags:
            chrome_options.add_argument(flag)
        driver = webdriver.Chrome(options=chrome_options)
        cookie = {
            "name": "FedAuth",
            "value": fed_auth,
            "domain": self.domain
        }
        driver.execute_cdp_cmd('Network.setCookie', cookie)
        self.driver = driver
        self.driver.maximize_window()
        self.waiter = WebDriverWait(self.driver, timeout=self.wait_timeout)

        
    def wait_for_element(self, xpath):
        self.waiter.until(EC.presence_of_element_located((By.XPATH, xpath)))
        
    def wait_for_class(self, class_name):
        self.waiter.until(EC.presence_of_element_located((By.CLASS_NAME, class_name)))
        
    def get_elements(self, xpath):
        self.wait_for_element(xpath)
        return self.driver.find_elements(By.XPATH, xpath)

    def get_elements_by_automationid(self, automationid):
        return self.get_elements(f"""//div[@data-automationid="{automationid}"]""")

    def get_element_by_classname(self, class_name):
        self.wait_for_class(class_name)
        return self.driver.find_element(By.CLASS_NAME, class_name)

    def is_folder(self, element):
            icon = element.find_element(By.XPATH, f""".//div[matches(@data-automation-key="fileTypeIconColumn_*"]//img""")
            icon_type = icon.get_attribute("alt")
            return icon_type == "Folder"
    
    def get_name(self, element):
        button = element.find_element(By.XPATH, f""".//div[@data-automation-key="FieldRenderer-name"]//button""")
        name = button.text
        return name
    
    def get_baseurl(self):
        url_items = json.loads(self.get_element_by_classname("ms-Breadcrumb-item").get_attribute('itemKey'))
        for path in reversed(url_items):
            if path is not None:
                base_url = f"{self.scheme}://{self.domain}/{path}"
                return base_url
        raise ValueError("No path items found")
    
    def collect_items_from_page(self, base_url, current_depth):
        folder_items = self.get_elements_by_automationid("DetailsRow")
        items = {}
        for item in folder_items:
            aria_label = item.get_attribute("aria-label")
            file_name, is_folder, expected_items = self.parse_aria_label(aria_label)
            url = f"{base_url}/{file_name}"
            items[url] = ListItem(name=file_name, url=url, is_folder=is_folder, expected_items=expected_items, items=[], depth=current_depth+1)
        return items
    
    def save_debug_info(self):
        if self.debug:
            self.driver.save_screenshot(self.debug_path)
            
    def add_items(self, base_url, previous_items, current_depth):
        new_items = self.collect_items_from_page(base_url, current_depth)
        return dict(new_items, **previous_items)
    
    def get_scroll_height(self):
        return self.driver.execute_script(f"""return document.querySelector(".{self.scroll_container_class}").scrollHeight""")

    def smooth_scroll_down(self):
        js_script = f"""
            function findAndScollParent(node) {{
                const overflowY = (node instanceof HTMLElement) && window.getComputedStyle(node).overflowY;
                const isScrollable = overflowY !== "visible" && overflowY !== "hidden";
                if (!node) {{
                    return null;
                }} else if (isScrollable && node.scrollHeight >= node.clientHeight) {{
                    return node;
                }}
                return findAndScollParent(node.parentNode) || document.body;
            }}
            const scrollParent = findAndScollParent(document.querySelector(".{self.scroll_container_class}"));
            scrollParent.scrollTo(0, scrollParent.scrollTop + {self.scroll_delta});
        """
        self.driver.execute_script(js_script)

    def scroll_based_on_expected_items(self, expected_items, current_depth):
        """A method for scrolling the page."""
        """ From https://stackoverflow.com/a/48851166 """
        items = {}
        current_items = len(items)
        self.wait_for_class(self.scroll_container_class)
        base_url = self.get_baseurl()
        pbar = tqdm(desc="Collecting items", total=expected_items, position=current_depth, leave=False)
        while current_items < expected_items:
            # Scroll down to the bottom.
            scroll_height = self.get_scroll_height()
            pbar.set_postfix({"Last height": scroll_height})
            self.smooth_scroll_down()
            # Wait to load the page.
            time.sleep(self.item_based_scroll_time)
            # Calculate new scroll height and compare with last scroll height.
            self.save_debug_info()
            items = self.add_items(base_url, items, current_depth)
            current_items = len(items)
            pbar.n = current_items
            pbar.refresh()
        return items.values()

    def scroll_based_on_height(self, current_depth):
        """A method for scrolling the page."""
        """This is slower as we wait five seconds after each scroll to accomodate slow pages"""
        """ From https://stackoverflow.com/a/48851166 """
        # Get scroll height.
        items = {}
        self.wait_for_class(self.scroll_container_class)
        base_url = self.get_baseurl()
        while True:
            # Scroll down to the bottom.
            last_height = self.get_scroll_height()
            self.smooth_scroll_down()
            # Wait to load the page.
            time.sleep(self.height_based_scroll_time)
            # Calculate new scroll height and compare with last scroll height.
            self.save_debug_info()
            items = self.add_items(base_url, items, current_depth)
            new_height = self.get_scroll_height()
            if new_height == last_height:
                break
            last_height = new_height
        return items.values()

    def collect_all_items(self, parent: ListItem) -> ListItem:
        """
            Scroll the entire page and ensure all items have been rendered
        """
        self.driver.get(parent.url)
        if parent.expected_items is not None:
            items = self.scroll_based_on_expected_items(parent.expected_items, parent.depth)
        else:
            items = self.scroll_based_on_height(parent.depth)
        parent.items = list(items)
        return parent

    def parse_aria_label(self, aria_label):
        parts = aria_label.split(",")
        file_name = parts[0].strip()
        file_type = parts[1].strip().lower()
        is_folder = file_type == "folder"
        expected_items = None
        if is_folder:
            expected_items = int(re.findall(r'Folder has (\d+) items', parts[2])[0])
        return file_name, is_folder, expected_items

    def collect_recursively(self, starting_url):
        base = ListItem(name="base", url=starting_url, is_folder=True, expected_items=None, items=[], depth=0)
        folders = [base]
        pbar = tqdm(desc="Flattening Sharepoint", position=0, total=1)
        current_index = 0
        while len(folders) > current_index:
            next_folder = folders[current_index]
            if next_folder.depth == self.max_depth:
                return base
            folder = self.collect_all_items(next_folder)
            for item in folder.items:
                if item.is_folder:
                    folders += [item]
            pbar.total = len(folders)
            pbar.update(1)
            pbar.refresh()
            current_index += 1

        return base

    def run(self):
        data = self.collect_recursively(self.start_url)
        with open(self.output_path, "w") as outfile:
            json.dump(asdict(data), outfile, indent=4)
        self.driver.quit()