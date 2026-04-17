# Hacker News Threat-Intel RAG Pipeline

A custom Retrieval-Augmented Generation (RAG) architecture built to automate the tracking of zero-day vulnerabilities, security patches, and infosec news from Hacker News. 

As a cybersecurity advocate focused on digital privacy, I designed this system to run entirely locally. By scraping threat intelligence data and feeding it into a local Large Language Model (LLM), I can query the latest security trends without leaking search data to third-party AI providers.

## 🛡️ Infrastructure & Security Posture
This pipeline does not run on a standard desktop. It is deployed and hosted on a **custom-hardened Virtual Machine** running on a bare-metal hypervisor. 
* 🔗 **Note:** You can view the complete writeup and architecture of my secure VM and network segmentation in my [Hardened VM & Network Infrastructure Repo](INSERT_LINK_TO_YOUR_OTHER_REPO_HERE).

## 🛠️ Technical Architecture (Initial Build)
This repository contains the foundational data ingestion pipeline built from scratch:
* **Custom Scrapers:** Python scripts designed to parse Hacker News threads, extracting relevant discussions around CVEs, exploits, and tech news.
* **Data Splitters:** Custom chunking logic to break down large forum discussions into manageable token limits.
* **Embedding Engine:** Vectorizing the scraped text for semantic search capabilities.
* **Local LLM Integration:** Feeding the embedded context into a locally hosted model to generate accurate, context-aware answers regarding new vulnerabilities.

## 🚀 Purpose
The primary goal of this project is to create an isolated, private intelligence feed. Instead of manually parsing hundreds of HN threads for the latest penetration testing tools or security flaws, this RAG architecture allows me to ask direct questions (e.g., *"What are the details of the latest SSH vulnerability discussed today?"*) and get precise answers grounded in real-time data.
