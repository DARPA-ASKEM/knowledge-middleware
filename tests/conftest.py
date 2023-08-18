import os

##############################
###### Setup Environment #####
##############################


os.environ["LIVE"] = "FALSE"
os.environ["TA1_UNIFIED_URL"] = "https://ta1:5"
os.environ["MIT_TR_URL"] = "http://mit:10"
os.environ["TDS_URL"] = "http://tds:15"
os.environ["LOG_LEVEL"] = "INFO"


##############################
######## Setup Logging #######
##############################

import logging

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
numeric_level = getattr(logging, LOG_LEVEL, None)
if not isinstance(numeric_level, int):
    raise ValueError(f"Invalid log level: {LOG_LEVEL}")

logger = logging.getLogger(__name__)
logger.setLevel(numeric_level)
handler = logging.StreamHandler()
formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - [%(lineno)d] - %(message)s"
)
handler.setFormatter(formatter)
logger.addHandler(handler)
