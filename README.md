## Clyppy Discord Bot (Public Release)

## Instructions:

To run an instance of this bot, you'll need to run the `main.py` as well as a MySQL database.

Currently this repo only contains code for running a Clip Alerts instance. To set it up and run it, follow these steps:

1. Paste your Discord bot instance's token into `src/env.py` or add it as an OS environment variable as `CLYPPY_TOKEN`
2. Similarly paste your ID and Secret of the Twitch API project you'd like to use into `env.py` (or enter them into your env variables)
3. Now we need to setup the database. Download [mysql community server](https://dev.mysql.com/downloads/mysql/) and run the setup. It will prompt you to create a password for the root account - make sure to save this as you'll need it in the next step
4. Modify `db_setup.py` with the password you created in the previous step, inserting it into the DB_PASS variable.
5. Run the cmd `sudo /usr/local/mysql/support-files/mysql.server start` (macOS) or `net start MySQL` (Windows)
6. Now run `db_setup.py`
7. 