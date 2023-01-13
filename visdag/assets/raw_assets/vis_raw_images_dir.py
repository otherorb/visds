import argparse
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
def vis_raw_images_dir():
    vis_raw_images_dir = {
            "vis_raw_images_dir" : os.getenv("RAW_DIRECTORY"),
            }
    
    return(vis_raw_images_dir)

if __name__ == "__main__":
    materialize([vis_raw_images_dir])
