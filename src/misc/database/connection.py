from src.env import DbCredentials
import aiomysql
import ssl
from datetime import datetime


POOL_SIZE = 6


class PooledConnection:
    def __init__(self,  creds: DbCredentials, logger, maxsize=None, pool_name=None):
        self.connected = False
        self.logger = logger
        self.USERNAME = creds.username
        self.PASSWORD = creds.passw
        self.HOST = creds.host
        self.DB = creds.dbname
        self.PORT = creds.port
        self.POOL_NAME = pool_name
        self.cnx = None
        self.pool = None
        #self.cerf_file = creds.ssl_ca
        self.SSL = None
        if maxsize is None:
            self.MAX_SIZE = POOL_SIZE
        else:
            self.MAX_SIZE = maxsize
        if self.POOL_NAME is None:
            self.POOL_NAME = "commands_pool"

    async def connect(self, loop) -> 'PooledConnection':
        """Create a pooled db connection, a collection of connection-spaces that are populated whenever we need a new connection"""
        #self.SSL = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        #self.SSL.check_hostname = False
        #self.SSL.load_verify_locations(cafile=self.cerf_file)
        self.pool = await aiomysql.create_pool(
            maxsize=self.MAX_SIZE,
            host=self.HOST,
            user=self.USERNAME,
            password=self.PASSWORD,
            db=self.DB,
            port=int(self.PORT),
            #ssl=self.SSL,
            autocommit=True,
            loop=loop)
        self.connected = True
        self.logger.info(f"{datetime.now()} - Database connected")
        return self

    async def execute_query(self, query: str, values=None, scaler=False):
        if not self.connected:
            return None
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                if values is None:
                    await cursor.execute(query)
                else:
                    await cursor.execute(query, values)
                if "show" in query.lower() or "select" in query.lower() or "describe" in query.lower():
                    """For queries that return data"""
                    data = await cursor.fetchall()  # use await here
                    if data and scaler:
                        return data[0][0]
                    elif data:
                        return data
                    else:
                        return None
                else:
                    """For queries that edit data"""
                    await conn.commit()
