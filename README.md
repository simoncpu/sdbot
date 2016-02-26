# SDBot 
### A [Slack](https://slack.com/) chatbot for [Server Density](https://www.serverdensity.com)

![](https://www.serverdensity.com/assets/images/slackbot/collaboration.gif)


## Installation

1. Clone the repo
2. [Create a bot user](https://my.slack.com/services/new/bot) if you don't have one yet, and copy the API Token
3. export SLACK_TOKEN="your-api-token"
4. export SD_AUTH_TOKEN="your-server-density-token"
5. export SD_ACCOUNT_NAME="server-density-account-name"
6. `make run` (or `make repl` for local testing)
7. Invite sdbot into any channels you want it in. Try typing `sdbot help` to test it out.

You could also install docker and use the docker file to run sdbot.

## Prerequisites
When you run `make run` it'll try to install matplotlib. Matplotlib depends on `libpng`, `pkg-config` and `freetype`. These needs to be installed before you can install matplotlib. 

## Get up to speed with SDBot
If you don't want to host SDBot yourself you can launch an SDBot with the help of BeepBoop. Just visit the [public page](https://beepboophq.com/bots/e41db5a7aa3a4b59bf7c6c8fb77d8e13), sign in and you'll be able to launch SDBot to your slack team in just seconds! If you don't yet have an account at Server Density and would like to enjoy the tremendous advantages of having an SDBot to support your slack team. Visit [Server Density](https://www.serverdensity.com) to sign up. Creating an SDBot for your team is the next step! 

If you are curious about what BeepBoop does you can always read their [documentation](https://beepboophq.com/docs)

If you have any questions at all, just send an email to hello@serverdensity.com

## Command Arguments

* --test, -t: Enter command line mode to enter a sdbot repl.
* --hook: Specify the hook to test. (Defaults to "message").
* -c: Run a single command.
* --database, -d: Where to store the sdbot tinydb database. Defaults to log.json.
* --pluginpath, -pp: The path where sdbot should look to find its plugins (defaults to /plugins).

## Environment Variables

* SD_AUTH_TOKEN: A Server Density Token. Required.
* SD_ACCOUNT_NAME: Your account name at Server Density. Recommended
* SLACK_TOKEN: Slack API token. Required.
* LIMBO_LOGLEVEL: The logging level. Defaults to INFO.
* LIMBO_LOGFILE: File to log info to. Defaults to none.
* LIMBO_LOGFORMAT: Format for log messages. Defaults to `%(asctime)s:%(levelname)s:%(name)s:%(message)s`.
* LIMBO_PLUGINS: Comma-delimited string of plugins to load. Defaults to loading all plugins in the plugins directory (which defaults to "/plugins")

## Commands

It's very easy to extend sdbot and add your own commands. Just create a python file in the plugins directory with an `on_message` function that returns a string.

You can use the `sdbot help` command to print out all available commands and a brief help message about them. 

---

## Contributors
A kind thank you to [Limbo](https://github.com/llimllib/limbo) and the persons who contributed to that. 

* [@fsalum](https://github.com/fsalum)
* [@rodvodka](https://github.com/rodvodka)
* [@mattfora](https://github.com/mattfora)
* [@dguido](https://github.com/dguido)
* [@JoeGermuska](https://github.com/JoeGermuska)
* [@MathyV](https://github.com/MathyV)
* [@stopspazzing](https://github.com/stopspazzing)
* [@noise](https://github.com/noise)
* [@drewp](https://github.com/drewp)
* [@TetraEtc](https://github.com/TetraEtc)
* [@LivingInSyn](https://github.com/LivingInSyn)
* [@reversegremlin](https://github.com/reversegremlin)
* [@adamghill](https://github.com/adamghill)
