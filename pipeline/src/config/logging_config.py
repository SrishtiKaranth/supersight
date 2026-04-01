import logging


def setup_logging(level=logging.INFO):
    fmt = "%(asctime)s [%(levelname)s] %(name)s — %(message)s"
    formatter = logging.Formatter(fmt)

    root = logging.getLogger()
    root.setLevel(level)

    console = logging.StreamHandler()
    console.setFormatter(formatter)
    root.addHandler(console)
