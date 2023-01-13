import argparse
import dagster
from dagster import asset, materialize, op
import json
import os


@asset(config_schema={"inputs": list})
def vis_raw_image_header(context):
    """This is the asset that's materialized via the 
    config schema passed in from the yamcs subscription. I hope."""
    image_header = context.op_config["inputs"]
    context.log.info(f"My image header is {image_header}")
    return(image_header)


if __name__ == "__main__":
    materialize([vis_raw_image_header])
