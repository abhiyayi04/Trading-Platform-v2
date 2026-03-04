# Trading-Platform

## Overview
This project is a **full-stack stock trading platform** built using a **Flask backend API and React frontend** that simulates real-world stock trading functionality.  
It supports **user authentication, role-based access (admin & customer), portfolio management, order execution, transaction tracking**, and **market schedule controls**.

The system demonstrates experience building **REST APIs, modern frontend applications, and database-driven systems**, along with **cloud deployment on AWS**.

---

## Tech Stack
- **Frontend:** React, JavaScript, HTML, CSS, Vite
- **Backend:** Flask, SQLAlchemy, Python
- **Authentication:** Flask-Login, Flask-Bcrypt
- **Database:** MySQL
- **Dev Tools:** Node.js, npm
- **Deployment:** AWS

---

## Key Features

### Authentication & Authorization
- Secure login and registration
- Password hashing with **Flask-Bcrypt**
- Session management with **Flask-Login**
- Role-based access:
  - **Customers:** trade stocks, manage portfolio, view transactions
  - **Admins:** manage stocks and market settings

---

### Trading System
- Buy and sell stock orders
- Order lifecycle tracking
- Simulated stock price updates
- Market open / closed trading restrictions

---

### Portfolio & Funds
- Track owned stocks and portfolio value
- Deposit and withdraw funds (simulation)
- View transaction history

---

### Admin Controls
- Create and delete stocks
- Configure market open / close hours
- Set closed trading dates
- Admin override to force market open or closed

---
