# Hacker News Threat-Intel RAG Pipeline

A custom Retrieval-Augmented Generation (RAG) architecture built to automate the tracking of zero-day vulnerabilities, security patches, and infosec news from Hacker News. 

As a cybersecurity advocate focused on digital privacy, I designed this system to run entirely locally. By scraping threat intelligence data and feeding it into a local Large Language Model (LLM), I can query the latest security trends without leaking search data to third-party AI providers.

## 🛡️ Infrastructure & Security Posture
This pipeline does not run on a standard desktop. It is deployed and hosted on a **custom-hardened Virtual Machine** running on a bare-metal hypervisor. The environment is heavily restricted to ensure the integrity of the LLM and the scraped data.
* 🔗 **Note:** You can view the complete writeup and architecture of my secure VM and firewall configurations in my [Hardened VM & Network Infrastructure Repo](INSERT_LINK_TO_YOUR_OTHER_REPO_HERE).

## 🧠 Development Process & Pipeline Optimization
Building a reliable data ingestion pipeline for web scraping is notoriously difficult due to edge cases. 

I initially built the data ingestion pipeline (scrapers, splitters, embedders) entirely from scratch. However, I quickly ran into edge cases with dynamic HTML parsing on Hacker News and chunk overlaps that corrupted the vector embeddings. 

Rather than spending weeks reinventing the wheel and fighting regex errors, **I leveraged LLM code assistants to aggressively refactor my initial logic**, optimize the error handling, and stabilize the ingestion flow. 

This strategic use of AI allowed me to focus my engineering time on the actual core challenges:
1. **Configuring and securing the host VM.**
2. **Deploying and optimizing the local LLM.**
3. **Tuning the RAG retrieval mechanism to accurately fetch cybersecurity intelligence.**

## 🛠️ Current Tech Stack
* **Ingestion:** Python, `aiohttp`, `BeautifulSoup` (AI-optimized for edge cases)
* **Processing:** Semantic chunking and vector embeddings
* **Deployment:** Hardened Local VM (Proxmox/Linux)
* **Application:** Threat Intelligence querying and vulnerability tracking

## 🚀 Usage
This tool serves as my personal intelligence feed. By querying the local LLM, I can instantly extract technical details about new CVEs or penetration testing techniques discussed by the community, fully isolating my research from public internet trackers.
