from setuptools import setup

setup(
    name="trading-game",
    version="0.1.0",
    py_modules=["trading_game_cli"],
    entry_points={
        "console_scripts": [
            "trading-game=trading_game_cli:main",
            "tg=trading_game_cli:main",
        ],
    },
)
