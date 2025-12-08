# Trading-Platform

## Overview
This project is a **full-stack trading platform** built using **Flask** that simulates real-world stock trading functionality.  
It supports **user authentication, role-based access (admin & customer), portfolio management, order execution, transaction tracking**, and **market hour controls**.

The application was **deployed on AWS**, demonstrating experience with cloud deployment and production-ready backend systems.

---

## Key Features

### Authentication & Authorization
- Secure user authentication using **Flask-Login**
- Password hashing with **Flask-Bcrypt**
- Role-based access control:
  - **Customers**: trade, manage portfolio, view transactions
  - **Admins**: manage stocks and market settings

---

### Trading Engine
- Buy & Sell stock orders
- Pending → Executed / Canceled order lifecycle
- Simulated real-time stock price updates
- Market hours enforcement (open / closed logic)
- Admin override for market control

---

### Portfolio & Funds Management
- User portfolio tracking
- Deposit and withdrawal simulation
- Transaction history ledger
- Payment method management (simulated)

---

### Market Logic
- Configurable market open/close times
- Closed trading days (holidays)
- Automatic price updates using background scheduler

---

## Tech Stack
- **Backend:** Flask, SQLAlchemy
- **Authentication:** Flask-Login, Flask-Bcrypt
- **Database:** MySQL=
- **Frontend:** Jinja2, HTML, CSS, Bootstrap
- **Deployment:** AWS


Logo icon: Money icons created by Smashicons - Flaticon  
https://www.flaticon.com/free-icons/money
