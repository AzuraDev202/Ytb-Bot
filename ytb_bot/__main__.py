"""Run the desktop application with python -m ytb_bot."""


def main():
    import sys
    if "--legacy" in sys.argv:
        from ytb_bot.ui.desktop import YtbBotApp
        app = YtbBotApp()
        app.mainloop()
    else:
        from ytb_bot.react_desktop import main as react_main
        react_main()


if __name__ == "__main__":
    main()
