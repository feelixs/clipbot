## Twitch Clip Alert Discord Bot

## Instructions:

To run an instance of this bot, follow these steps to setup your `env.py` as well as setup a MySQL database before running `main.py`

Currently this repo only contains code for running a Clip Alerts instance. To set it up and run it, follow these steps:

1. Paste your Discord bot instance's token into `src/env.py` or add it as an OS environment variable as `CLYPPY_TOKEN`.
2. Similarly paste your ID and Secret of the Twitch API project you'd like to use into `env.py` (or enter them into your env variables).
3. Now we need to setup the database. Download [mysql community server](https://dev.mysql.com/downloads/mysql/) and run the setup. It will prompt you to create a password for the root account - make sure to save this as you'll need it in the next step.
4. Modify `src/env.py` with the password you created in the previous step, inserting it into the `DbCredentials -> passw` variable.
5. Run the cmd `sudo /usr/local/mysql/support-files/mysql.server start` (macOS) or `net start MySQL90` (or `MySQL[version]`) (Windows).
6. Now run `db_setup.py` - it should connect to the database you just installed and perform all necessary setup.
7. Finally run `main.py` to start the bot. You should now be able to interact with its commands after adding it to your server!