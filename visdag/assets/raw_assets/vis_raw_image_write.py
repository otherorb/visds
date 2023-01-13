import dagster
from dagster import asset, materialize
import json
import os
from pathlib import Path
import sys
from time import sleep
from yamcs.client import YamcsClient
from visdag.db_con import get_postgres_db


@asset
def raw_images_dir():
    raw_images_dir = {
            "RAW_DIR" : os.getenv("RAW_DIRECTORY"),
            }
    
    return(raw_images_dir)

if __name__ == "__main__":
    materialize([raw_images_dir])
