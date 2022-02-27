# Maubot Pocket

A [maubot](https://github.com/maubot/maubot) plugin that integrates with Pocket.

![demo](/maubot-pocket.gif)

Features:
* Authenticate with Pocket
* Fetch random article
* Archive article via reactions

If you don't want to host your own instance you can use `@maubot:basshero.org`. NOTE! This will grant 
the author of this plugin API access to your Pocket account. 

## Usage

Invite the bot (your own or `@maubot:basshero.org`) to your room.

First you need to authenticate.

`!pocket login`

Click the link, login to Pocket if needed and grant access to your account. You will be redirected
to a page that hopefully shows you have authenticated correctly.

Going back to the chat room, you can now use the `!pocket` command (without any parameters) to receive
a random article from your list.

To archive the article, react to the article with `✅` or `👎`. You can also open the article in Pocket by 
cicking the provided link, for example to add tags.

Should you want a new article you can also react to a previously posted article message with either
`➕` or `👍`.

If you want to disconnect the bot from Pocket, use the command `!pocket logout`. This will destroy
the access token from the bots database.

## Setup

### I already have a Maubot instance

Go to releases and download the latest plugin `.mbp` file. Upload it to your Maubot instance as per normal.

Create a Pocket plugin instance. Go to [Pocket developer pages](https://getpocket.com/developer/apps/) 
and create a Pocket application. Minimum required permissions are `retrieve`, `modify` - though `add` 
makes also sense since that functionality will soon be added to this bot.

Note down the "consumer key", go back to your Maubot manager and save it as the `api_key` in the Pocket plugin
instance config.

Follow above to login.

### I don't have a Maubot instance

First [install Maubot](https://docs.mau.fi/maubot/usage/setup/index.html) and then see above!

Ansible and Docker your thing? See [ansible-maubot](https://github.com/jaywink/ansible-maubot) for an Ansible role
that maintains Maubot using Docker.

## Author

Jason Robinson / https://jasonrobinson.me / `@jaywink:federator.dev`

## License

MIT
