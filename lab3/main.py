import logging
from argparse import ArgumentParser
from application import Application


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    parser = ArgumentParser()
    parser.add_argument("path")
    
    args = parser.parse_args()
    app = Application(args.path)
    app.start()
