import logging

def setup_logging(level: str = "INFO") -> None:
    numeric_level = getattr(logging, level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f"Invalid log level: {level}")
    logging.basicConfig(level=numeric_level, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
