import os
from dotenv import load_dotenv


def check_env_for_dev_flag() -> bool:
    """
    Checks the .env for the MONITOR flag. Used for monitoring events in the program, that doesn't need
    to be presented to the end user.
    """
    load_dotenv()
    monitor = os.getenv("MONITOR")
    if monitor == "TRUE":
        return True
    else:
        return False
