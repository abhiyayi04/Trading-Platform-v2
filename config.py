import os

DB_USERNAME = "admin"
DB_PASSWORD = "password"
DB_HOST = "stock-db.c8fkq4uecfai.us-east-1.rds.amazonaws.com" 
DB_PORT = "3306"
DB_NAME = "stock_trading_db2"

SQLALCHEMY_DATABASE_URI = (
    f"mysql+pymysql://{DB_USERNAME}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)
SQLALCHEMY_TRACK_MODIFICATIONS = False
