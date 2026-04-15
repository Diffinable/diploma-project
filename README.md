# 🏠 Residential Repair Information Support System

A full‑stack web application designed to automate repair cost estimation 
for small construction teams and their clients. 
This project was developed as a **Bachelor's Diploma Thesis** at Penza State University.

## Features

### For Clients
- **Instant Cost Estimation** – Enter room dimensions and choose required repair works to get a detailed cost breakdown.
- **User Registration & Authentication** – Securely create an account using JWT tokens.
- **Personal Cabinet** – Save estimates, view history, and track project status.
- **Responsive Web Interface** – Accessible from any modern browser.

### For Estimators / Administrators
- **Manage Work Types & Pricing** – Maintain a catalog of repair services with per‑unit labor costs.
- **Consistent Calculation Logic** – Algorithm automatically computes labor costs using `volume × labor_cost_per_unit × complexity_factor`.
- **Database‑Backed Persistence** – All estimates, clients, and premises are stored reliably.

## 🛠 Tech Stack

| Category            | Technology                                                                 |
|---------------------|-----------------------------------------------------------------------------|
| **Backend**         | Python 3.11, FastAPI (asynchronous REST API)                                |
| **Database**        | PostgreSQL, SQLAlchemy ORM, Alembic (migrations)                            |
| **Authentication**  | JWT (JSON Web Tokens), Bcrypt password hashing                              |
| **Frontend**        | HTML5, CSS3, JavaScript (vanilla), served as static files                   |
| **Containerization**| Docker, Dockerfile                                                          |
| **Testing**         | Pytest (API and unit tests)                                                 |
| **Documentation**   | Auto‑generated Swagger UI (`/docs`)                                         |
| **Version Control** | Git, GitHub                                                                 |

## Getting Started

Follow these steps to run the project locally.

### Prerequisites
- Python 3.11+
- PostgreSQL 15+ (or use Docker)
- Git

### 1. Clone the Repository
```bash
git clone https://github.com/Diffinable/diploma-project.git
cd diploma-project
