# CS221Bot

CS221Bot is a [Discord](discord.com/) [bot](https://discord.com/developers/docs/intro) using [Discord.py](https://discordpy.readthedocs.io/en/latest/) for managing the official [UBC CS221](https://www.ubc.ca/) class server.

## Installation

Clone the repo to your computer, and ensure your Discord Bot [Token](https://discord.com/developers/docs/intro) is set as a environmental variable named `CS221BOT_KEY`.

Additionally, you will need a Piazza email + password and a Canvas API key set as environment variables to use their respective commands.

## Dependencies

The bot requires the following pip packages: 
- `discord` 
- `requests` 
- `webcolors` 
- `googletrans`
- `beautifulsoup` 
- `python-dotenv`
- `python-dateutil`
- `canvasapi`
- `piazza-api`
- `pytz`
- `Pillow`
- `binarytree`

You can install all of them using `pip install -r requirements.txt`.

## Usage

Start the bot by using `python3 cs221bot.py`. 
View the list of commands by typing `!help` in a server where the bot is in.

If you are tracking non-public Canvas courses with the bot, you will need to set a Canvas-generated user token as
the environmental variable `CANVAS_API_KEY` in the `.env` file. When starting the bot, you need to use the `-t` flag,
i.e. run the command `python3 cs221bot.py -t`.