import logging


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    logging.getLogger().handlers[0].setLevel(logging.INFO)
    logging.getLogger().setLevel(logging.INFO)

    for logger_name in logging.root.manager.loggerDict:
        if not logger_name.startswith("RAG"):
            logging.getLogger(logger_name).setLevel(logging.WARNING)
