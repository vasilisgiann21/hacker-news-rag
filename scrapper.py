import asyncio
import aiohttp
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlsplit, urlunsplit
import aiofiles
import json
import argparse
import random

async def disk_writer(writer_queue, filename):
    async with aiofiles.open(filename, mode = 'a', encoding="utf-8") as f:
        while True:
            content = await writer_queue.get()
            try:
                new_content = json.dumps(content) + "\n"
                await f.write(new_content)
            except Exception as e:
                print(f"Scribe Error : {e}")
            finally:
                writer_queue.task_done()

              
def extract_intel(html, url, base):
 
    soup = BeautifulSoup(html, "html.parser")
    extracted_text = None
    container = soup.find("div", class_="mainbox")
    if container:
        extracted_text = container.get_text(separator="\n", strip=True)
    
    links = []
    for a_tag in soup.find_all('a'):
        href = a_tag.get("href")
        if href:
            new_link = urljoin(base, href)
            parsed = urlsplit(new_link)
            new_link = urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))
            
            if base in new_link:
                links.append(new_link)
                
    return {
        "url": url,
        "content": extracted_text,
        "links": links
    }

async def fetch_data(url_queue, writer_queue, session, visited, base):
    
    while True:
        url = await url_queue.get()
        headers = {
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/119.0"
        }
        
        try:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    html = await response.text()
                    
                    result_dict = await asyncio.to_thread(extract_intel, html, url, base)
                    
                    if result_dict.get("content"):
                        print(f"[+] Payload Exfiltrated: {url}")
                        await writer_queue.put({
                            "url": result_dict["url"], 
                            "content": result_dict["content"]
                        })
                    else:
                        print(f"[-] Scanned (No Payload): {url}")
                        
                    if len(visited) < 10000:
                        for new_link in result_dict.get("links", []):
                            if new_link not in visited:
                                visited.add(new_link)
                                await url_queue.put(new_link)
                else:
                    print(f"[!] Access Denied (HTTP {response.status}): {url}")
                    
        except Exception as e:
            print(f"[x] Connection dropped on {url} - {e}")
            
        finally:
            url_queue.task_done()


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scrape", required = True, help = "The target url")
    parser.add_argument("--output", required = False,default = "file.jsonl", help = "The name of the file created")
    args = parser.parse_args()
    base = args.scrape
    writer_queue = asyncio.Queue()
    url_queue = asyncio.Queue()
    visited = set()
    visited.add(base)
    tasks = []
    async with aiohttp.ClientSession() as session:
            await url_queue.put(base)
            scribe_task = asyncio.create_task(disk_writer(writer_queue,args.output))
            for i in range(50):
                task = asyncio.create_task(fetch_data(url_queue, writer_queue, session, visited, base))
                tasks.append(task)
                await asyncio.sleep(0.5)

            await url_queue.join()
            await writer_queue.join()
            for task in tasks:
                task.cancel()
            scribe_task.cancel()

if __name__ == "__main__":
    asyncio.run(main())



                
        
 