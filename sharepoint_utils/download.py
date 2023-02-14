import json
import asyncio
import httpx
from tqdm import tqdm
from pathlib import Path

class Download:

    def __init__(
        self,
        flattened_json_path,
        fed_auth,
        output_dir,
        max_retries,
    ) -> None:
        with open(flattened_json_path, "r") as json_file:
            self.dirdump = json.load(json_file)
        self.output_dir = output_dir
        self.fed_auth = fed_auth
        self.max_retries = max_retries
        self.total_files = 0
        self.recurse_datadump_to_get_total(self.dirdump)
        self.pbar = tqdm("Downloading data", total=self.total_files)
    
    def recurse_datadump_to_get_total(self, parent):
        for item in parent["items"]:
            if item["is_folder"]:
                self.recurse_datadump_to_get_total(item)
            else:
                self.total_files += 1

    async def download_files(self, client, base_path, parent):
        for item in parent["items"]:
            name = item["name"]
            cur_path = f"{base_path}/{name}"
            if item["is_folder"]:
                Path(cur_path).mkdir(parents=True, exist_ok=True)
                await self.download_files(client, cur_path, item)
            else:
                resp = await client.get(item['url'], cookies={"FedAuth": self.fed_auth})
                with open(cur_path, "wb") as outfile:
                    outfile.write(resp.content)
                    self.pbar.update(1)

    def run(self):
        async def runner():
            async with httpx.AsyncClient() as client:
                await self.download_files(client=client, base_path=self.output_dir, parent=self.dirdump)
        loop = asyncio.get_event_loop()
        loop.run_until_complete(runner())
