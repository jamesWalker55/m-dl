import logging

log = logging.getLogger("m_dl")


def setup_logging():
    # make the logger show DEBUG logs
    log.setLevel(logging.DEBUG)

    # output to stderr, and show DEBUG logs
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.DEBUG)
    stream_handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    )
    log.addHandler(stream_handler)
