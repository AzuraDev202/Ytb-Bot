"""Run the desktop application with python -m ytb_bot."""


def main():
    from ytb_bot.ui.desktop import YtbBotApp
    app = YtbBotApp()
    app.mainloop()


if __name__ == "__main__":
    main()
