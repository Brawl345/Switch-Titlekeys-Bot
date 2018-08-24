#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import html
import logging
import os
import sys
from configparser import ConfigParser
from json import loads

import telegram
from requests import get
from telegram.ext import Updater

# Logging
logging.basicConfig(
    format="%(asctime)s - %(levelname)s: %(message)s",
    datefmt="%d.%m.%Y %H:%M:%S",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot configuration
config = ConfigParser()
try:
    config.read_file(open("config.ini"))
except FileNotFoundError:
    logger.critical("config.ini not found!")
    sys.exit(1)

# Bot token
try:
    bot_token = config["DEFAULT"]["token"]
except KeyError:
    logger.error("No bot token, please check config.ini!")
    sys.exit(1)
if not bot_token:
    logger.error("No bot token, please check config.ini!")
    sys.exit(1)

# DB URL
try:
    db_url = config["DEFAULT"]["db_url"]
except KeyError:
    logger.error("No database URL, please check config.ini!")
    sys.exit(1)
if not db_url:
    logger.error("No database URL, please check config.ini!")
    sys.exit(1)
    
try:
    db_url_m = config["DEFAULT"]["db_url_m"]
except KeyError:
    db_url_m = None

# Channels
try:
    channels = loads(config["DEFAULT"]["channels"])
except KeyError:
    logger.error("No channel IDs, please check config.ini!")
    sys.exit(1)
if not channels:
    logger.error("No channel IDs, please check config.ini!")
    sys.exit(1)

for channel in channels:
    if not isinstance(channel, int):
        logger.error("Channel IDs must be integeres!")
        sys.exit(1)


def save_database(newdb):
    with open("titlekeys.txt", "w", encoding="utf8") as file:
        for line in newdb:
            if line.strip():
                file.write(line.strip() + "\n")
    logger.info("Database saved.")


def update_titlekeys(bot):
    # Download new database
    logger.info("Downloading new database...")
    req = get(db_url, allow_redirects=True)
    if req.status_code != 200:
        if db_url_m:
            logger.error("Database URL returned HTTP Error {0}, trying mirror...".format(req.status_code))
            req = get(db_url_m, allow_redirects=True)
            if req.status_code != 200:
                logger.error("Database Mirror URL returned HTTP Error {0}".format(req.status_code))
                return
        else:
            logger.error("Database URL returned HTTP Error {0}".format(req.status_code))
            return
    req.encoding = "utf-8"
    newdb = req.text.split("\n")
    if newdb[-1] == "":
        newdb = newdb[:-1]

    # If first download
    if not os.path.isfile("titlekeys.txt"):
        logger.info("First time downloading database...")
        save_database(newdb)
        return

    # If already downloaded
    with open("titlekeys.txt", encoding="utf8") as file:
        currdb = file.read().split("\n")
        if currdb[-1] == "":
            currdb = currdb[:-1]
        currdb = [x.strip() for x in currdb]
        text = ""
        counter = 0
        for line in newdb:
            if line.strip() not in currdb:
                if line.strip() != newdb[0].strip():
                    title = line.strip().split("|")
                    text += "<b>{0}</b>:\n<i>{1}</i>\n<code>{2}</code>\n\n".format(
                        html.escape(title[2]),
                        title[0],
                        title[1]
                    )
                    counter += 1
        if counter:
            logger.info("{0} new titlekeys.".format(counter))
            for channel in channels:
                try:
                    bot.sendMessage(
                        chat_id=channel,
                        text=text,
                        parse_mode=telegram.ParseMode.HTML
                    )
                except telegram.error.TimedOut:
                    pass
                except Exception as exception:
                    logger.error(exception)
            save_database(newdb)
        else:
            logger.info("No database updates.")


def run_job(bot, job):
    logger.info("================================")
    update_titlekeys(bot)


def onerror(bot, update, error):
    logger.error(error)


# Main function
def main():
    # Setup the updater and show bot info
    updater = Updater(token=bot_token)
    try:
        bot_info = updater.bot.getMe()
    except telegram.error.Unauthorized:
        logger.error("Login failed, wrong bot token?")
        sys.exit(1)

    logger.info("Welcome {0}, AKA @{1} ({2})".format(
        bot_info.first_name,
        bot_info.username,
        bot_info.id
    ))

    # Hide "Error while getting Updates" because it's not our fault
    updater.logger.addFilter((lambda log: not log.msg.startswith("Error while getting Updates:")))

    # Fix for Python <= 3.5
    updater.dispatcher.add_error_handler(onerror)
    updater.job_queue.run_repeating(
        run_job,
        interval=3600.0,  # 1 hour
        first=1.0
    )

    # Start this thing!
    updater.start_polling(
        bootstrap_retries=-1,
        allowed_updates=[""]
    )

    # Run Bot until CTRL+C is pressed or a SIGINIT,
    # SIGTERM or SIGABRT is sent.
    updater.idle()


if __name__ == "__main__":
    main()
