# CS221Bot

CS221Bot is a [Discord](https://discord.com/) [bot](https://discord.com/developers/docs/intro) using [Pycord](https://docs.pycord.dev/en/master/index.html) for managing the official [UBC CS221](https://www.ubc.ca/) class server.

## Installation

Clone the repo to your computer, and ensure your Discord Bot [Token](https://discord.com/developers/docs/intro) is set as a environmental variable named `CS221BOT_KEY`.

Additionally, you will need a Piazza email + password and a Canvas API key set as environment variables to use their respective commands.

## Dependencies

The bot requires the following pip packages:

- `beautifulsoup4`
- `binarytree`
- `cairosvg`
- `canvasapi`
- `chess`
- `piazza-api`
- `py-cord`
- `PyNaCl`
- `python-dateutil`
- `python-dotenv`
- `youtube-dl`

You can install all of them using `pip install -r requirements.txt`.

The bot also requires GraphViz, which can be installed with `conda install -c anaconda graphviz`

## Usage

Start the bot by using `python3 cs221bot.py`. View the list of commands by typing `!help` in a server where the bot is in.

The bot's Canvas module-tracking functionality only notifies you of new *published* modules by default. If you want the bot to notify you when it sees a new *unpublished* module, run the bot with the
`--cnu` flag, i.e. run `python3 cs221bot.py --cnu`. You need to have access to unpublished modules, though.
