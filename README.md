# Taiga Bot

_By JadenLabs & Community_

The official Taiga bot, from the [Taiga supremacy](https://discord.gg/9F5npU4Jya) Discord server

---

### Setup

**Prerequisites**

-   Git
-   Python
-   Pip

1. Clone the repo
    ```bash
    git clone https://github.com/JadenLabs/Taiga.git
    ```
2. Change directories into the code
    ```bash
    cd Taiga
    ```
3. Install dependencies
    ```bash
    pip install -r requirements.txt
    ```
4. Open [example.env](./example.env) and put your bot's values in there, then rename it to `.env` or anything with the prefix `.env` (ie: `.env.dev`). If you use a name other than `.env`, you will need to use the `-e <env file>` flag. 
5. Open [config.toml](./config.toml) and adjust it to your needs. Like the .env, if you use a name other than `config.toml` for the config, use the `-c <config file>` flag.
6. Run the bot
    ```bash
    python [-O] main.py
    ```
    `-O` sets `__debug__` to `False`, disabling cogwatch. 

### Usage

```md
usage: main.py [-h] [-e ENV] [-c CONFIG]

options:
-h, --help show this help message and exit
-e ENV, --env ENV The env file to use
-c CONFIG, --config CONFIG The config file to use
```
