# run this ONCE after creating your mysql database. It will create all the necessary tables & columns
from src.misc.database import Database
from src.env import DbCredentials
import asyncio
import mysql.connector

DB_PASS = "12345678"  # replace with the password of the root user
DB_HOST = "127.0.0.1"  # replace with your computer's IP
DB_NAME = "clyppydb"  # name the database anything you want


async def create_database_if_not_exists():
    cnx = mysql.connector.connect(user="root", password=DB_PASS, host=DB_HOST)
    cursor = cnx.cursor()
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME}")
    cursor.close()
    cnx.close()


async def main():
    await create_database_if_not_exists()
    creds = DbCredentials()
    creds.username = "root"
    creds.passw = DB_PASS
    creds.port = 3306
    creds.host = DB_HOST
    creds.dbname = DB_NAME
    d = Database(creds, maxsize=50, pool_name="CLYPPY_POOL")
    await d.connect(asyncio.get_running_loop())


asyncio.run(main())
