# 🚌 LokBus: Bus Operations & Passenger Experience Analytics

> Turning passenger feedback and daily bus operations into actionable service insights.

## Overview

LokBus is a data-driven project for understanding bus-service quality at the level of routes, vehicles, drivers, conductors, and operating times. It combines synthetic passenger reviews generated with a language model with aggregated bus routes fetched from Chalo, which creates the foundation for sentiment analysis, issue tracking, and future transport dashboards.

## Key Features

- **Synthetic passenger reviews** — 6,000+ natural-language bus reviews were generated locally using Qwen 2.5 3B Instruct. They cover driving quality, disruptions, ticket handling, crowding, and bus maintenance, with positive, negative, and mixed passenger feedback and ratings.
- **Operational mapping** — Reviews are linked to service date, route, vehicle, timestamp, driver, and conductor information. Generated unique driver and conductor names and are associated with unique IDs for reliable downstream analysis.
- **Submit Reviews** - A platform for users to share their own Bus journey experiences.
- **Real-Time Updates** - Automated Route Fetching using Chalo APIs to ensure the data is always fresh.
- **Analysis-ready output** — Enriched CSV data can support dashboards, sentiment models, issue monitoring, and crowd-level comparisons.

## Review Categories

| Category | Examples of feedback captured |
| --- | --- |
| Driving | Smooth driving, abrupt braking, speeding, dangerous overtaking |
| Disruptions | Traffic delays, missed stops, diversions, late arrival |
| Ticket handling | Fare collection, ticket availability, conductor behaviour |
| Crowding | Overcrowded buses, standing space, boarding difficulty |
| Bus maintenance | Cleanliness, damaged seats, broken hangers, bus condition |

## Technology Stack

| Component | Technology | Purpose |
| --- | --- | --- |
| Programming language | Python, SQL | Data processing and maintaining queries |
| Language Model | Qwen 2.5, MLX | Review Generation across different categories |
| Frontend | HTML, CSS, JavaScript | Analytics Site and User Page |
| Backend | Flask, Docker | User Operations, login page, and DB initialization |
| Database | Postgres | Data Storage and Schema Management |
| Version control | Git & GitHub | Collaboration and project history |

## Project Structure

```bash
LokBus/
├── Docs/
├── analysis/                   # Code for Analysis dashboards
├── analytics_site/             # Code for Merchant system 
│   ├── static/
│   ├── templates/
│   └── app.py                  # Code to initialise the Merchant side web page
├── db/                         # Code for schemas and docker initialisation
├── frontend/                   # Code for User System
│   ├── static/
│   ├── templates/
│   └── app.py                  # Code to initialise the User side web page
├── routes/                     # Code for API calls of routes
├── requirements.txt
├── setup.sh                    # Script to run the project
├── LICENSE
├── .gitignore
└── README.md
```


## Getting Started

### Prerequisites

- Python 3.10 or newer
- Docker Application

### Set up the environment

```bash
git clone https://github.com/16AbhinavReddy/LokBus.git
cd LokBus

python3 -m venv .venv
source .venv/bin/activate
pip install pandas
```

## Contributors

| Name | Role | Email | GitHub |
| :--- | :--- | :--- | :--- |
| **Tarun** | Developer | <26M0800@iitb.ac.in> | [Tarun2025-dev](https://github.com/Tarun2025-dev) |
| **Abhinav** | Developer | <26M0801@iitb.ac.in> | [16AbhinavReddy](https://github.com/16AbhinavReddy) |
| **Yashwanth** | Developer | <26M0794@iitb.ac.in> | [yashwanthsudi10](https://github.com/yashwanthsudi10) |

