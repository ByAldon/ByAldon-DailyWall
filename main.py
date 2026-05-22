import sys

from wallpaper.app_core import run_dailywall


def main():
    try:
        run_dailywall(logger=print)
    except Exception as error:
        print("Something went wrong:")
        print(error)
        sys.exit(1)


if __name__ == "__main__":
    main()
