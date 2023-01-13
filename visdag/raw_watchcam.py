#!/usr/bin/env python
# -*- coding: utf-8 -*-

import concurrent.futures
from dagster_graphql import DagsterGraphQLClient, DagsterGraphQLClientError
from dagster import DagsterRunStatus
import json
import logging
from pathlib import Path
from time import sleep
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from yamcs.client import YamcsClient

import os
from vipersci.vis.pds.create_raw import Creator
import vipersci.util as util


parameters = [
    "/ViperGround/Images/ImageData/Navcam_left_icer",
    "/ViperGround/Images/ImageData/Navcam_left_jpeg",
    "/ViperGround/Images/ImageData/Navcam_right_icer",
    "/ViperGround/Images/ImageData/Navcam_right_jpeg",
    "/ViperGround/Images/ImageData/Aftcam_left_icer",
    "/ViperGround/Images/ImageData/Aftcam_left_jpeg",
    "/ViperGround/Images/ImageData/Aftcam_right_icer",
    "/ViperGround/Images/ImageData/Aftcam_right_jpeg",
    "/ViperGround/Images/ImageData/Hazcam_front_left_icer",
    "/ViperGround/Images/ImageData/Hazcam_front_left_jpeg",
    "/ViperGround/Images/ImageData/Hazcam_front_right_icer",
    "/ViperGround/Images/ImageData/Hazcam_front_right_jpeg",
    "/ViperGround/Images/ImageData/Hazcam_back_left_icer",
    "/ViperGround/Images/ImageData/Hazcam_back_left_jpeg",
    "/ViperGround/Images/ImageData/Hazcam_back_right_icer",
    "/ViperGround/Images/ImageData/Hazcam_back_right_jpeg",
]
# The structure for adding SLoG images to the database is not complete,
# because I don't know if we have to worry about it, so it hasn't been
# built out.  Which is why these are separate.  If, indeed, SLoG images
# could come down from the rover, then a variety of code changes are needed
# in raw_products.py and create_raw.py
slog_parms = [
    "/ViperGround/Images/ImageData/Navcam_left_slog",
    "/ViperGround/Images/ImageData/Navcam_right_slog",
    "/ViperGround/Images/ImageData/Aftcam_left_slog",
    "/ViperGround/Images/ImageData/Aftcam_right_slog",
    "/ViperGround/Images/ImageData/Hazcam_front_left_slog",
    "/ViperGround/Images/ImageData/Hazcam_front_right_slog",
    "/ViperGround/Images/ImageData/Hazcam_back_left_slog",
    "/ViperGround/Images/ImageData/Hazcam_back_right_slog",
]

def get_image_header(data):
    dag_client = DagsterGraphQLClient("localhost", port_number=3000)
    image_header = []
    # on_data is the callback function used to take the data
    # received from yamcs and send it to the dagster job.
    for parameter in data.parameters:
        print(f"{parameter.generation_time} - {parameter.name}")
        image_header.append(
            (
                parameter.name,
                parameter.generation_time.isoformat(),
                parameter.eng_value['imageHeader']
            )
        )

    print("************************************************************")
    print(image_header)
    print("************************************************************")

    try:
        raw_run_id: str = dag_client.submit_job_execution(
                "vis_raw_processing",
                run_config={
                    "ops": {
                        "vis_raw_image_header": {
                            "config": {
                                "inputs": image_header
                            }
                        }
                    }
                }
        )
        print(raw_run_id)
    except DagsterGraphQLClientError as exc:
        raise exc

def main():
    yamcsclient="localhost:8090/yamcs"

    client = YamcsClient(yamcsclient)
    processor = client.get_processor("viper", "realtime")

    #Check to see if dagster is running.
    dagster_client = DagsterGraphQLClient("localhost", port_number=3000)
    print(dagster_client)


    # Grabbing the yamcs-client logger, and then having it be handled
    # by a StreamHandler that is set to only emit CRITICAL messages
    # suppresses the writing of the 
    # "Problem while processing message. Closing connection"
    # plus traceback message to STDOUT.
    # of course, if you suppress this, then you had better log 
    # subscription.exception() like we now do down in wait_loop().

    ylogger = logging.getLogger("yamcs-client")
    ch = logging.StreamHandler()
    # # This suppresses the exception messsage and stacktrace STDOUT printing.
    ch.setLevel(logging.CRITICAL)  # Change to ERROR or less to get again
    ch.setFormatter(logging.Formatter("%(name)s - %(levelname)s: %(message)s"))
    ylogger.addHandler(ch)

    # 

    subscription = processor.create_parameter_subscription(
            parameters + slog_parms,
            on_data=get_image_header
            )
    print(subscription)

    wait_loop(subscription)

def wait_loop(subscription):
    print("Press Ctrl-C to stop watching.")
    try:
        while subscription.running():
            sleep(5)
        else:
            print("Subscription stopped running.")

            # This proves that the subscription got an exception,
            # but isn't really how we want to handle this.
            # try:
            #     print(subscription.result())
            # except Exception as err:
            #     print(type(err))
            #     print(err)

            print(f"Done: {subscription.done()}")
            print(f"Cancelled: {subscription.cancelled()}")
            if not subscription.cancelled():
                # This cleans up the websocket and shuts down the
                # background thread.  In this simple watch_cam program
                # we're just going to exit, so it doesn't matter but if
                # you wanted to try and re-establish a new subscription,
                # this should probably be done, so just testing.
                subscription.cancel()
                print(f"Now cancelled: {subscription.cancelled()}")

            err = subscription.exception()
            if err is not None:
                print(type(err))
                print(err)

    except KeyboardInterrupt:
        print("Stopped watching.")


if __name__ == "__main__":
    sys.exit(main())
