#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import concurrent.futures
import json
import logging
from pathlib import Path
from time import sleep
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from yamcs.client import YamcsClient

import os
sys.path.insert(1, os.path.join(sys.path[0],'/users/moses/Documents/Development/VIPER/vipersci/src'))
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


class Watcher(list):

    def on_data(self, data):
        for parameter in data.parameters:
            print(f"{parameter.generation_time} - {parameter.name}")
            self.append(
                (
                    parameter.name,
                    parameter.generation_time.isoformat(),
                    parameter.eng_value['imageHeader']
                )
            )
            if not len(self) % 4:
                raise ValueError("Every fourth exception.")


def arg_parser():
    parser = argparse.ArgumentParser(
        description=__doc__,
        parents=[util.parent_parser()]
    )
    parser.add_argument(
        "-y", "--yamcsclient",
        default="localhost:8090/yamcs",
    )
    parser.add_argument(
        "-d", "--dburl",
        help="Something like postgresql://postgres:NotTheDefault@localhost/visdb"
    )
    parser.add_argument(
        "-j", "--json",
        help="If neither -d or -o are given, a JSON file of the Yamcs "
             "parameters will be written."
    )
    parser.add_argument(
        "-o", "--outdir",
        type=Path,
        help="Output directory."
    )

    return parser


def main():
    parser = arg_parser()
    args = parser.parse_args()
    util.set_logger(args.verbose)

    client = YamcsClient(args.yamcsclient)
    processor = client.get_processor("viper", "realtime")

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


    if args.dburl is not None:
        engine = create_engine(args.dburl)
        session_maker = sessionmaker(engine, future=True)

        creator = Creator(
            outdir=args.outdir,
            session=session_maker
        )

        subscription = processor.create_parameter_subscription(
            parameters + slog_parms,
            on_data=creator.from_yamcs_parameters
        )

        wait_loop(subscription)

    elif args.outdir is not None:

        creator = Creator(
            outdir=args.outdir,
        )

        subscription = processor.create_parameter_subscription(
            parameters + slog_parms,
            on_data=creator.from_yamcs_parameters
        )

        wait_loop(subscription)

    elif args.json is not None:
        watched = Watcher()

        subscription = processor.create_parameter_subscription(
            parameters + slog_parms,
            on_data=watched.on_data
        )

        wait_loop(subscription)

        # while subscription.running():
        #     # With just pass, we only get two images, and then:
        #     #   WebSocket error: Connection closed
        #     #   Not running
        #     #   <class 'yamcs.core.exceptions.ConnectionFailure'>
        #     #   Connection closed
        #     # pass

        #     # With sleep(5) four images come through, and the ValueError
        #     # bubbles out of the WebSocketSubscriptionManager to 
        #     # stdout, but there is enough time for the ValueError 
        #     # to somehow be passed up to the subscription, so that
        #     # subscription.result() yields the ValueError, and we get:
        #     #   Problem while processing message. Closing connection
        #     #   Problem while processing message. Closing connection
        #     #     File "/Users/rbeyer/.anaconda3/envs/vipersci/lib/python3.7/site-packages/yamcs/core/subscriptions.py", line 148, in _on_websocket_message
        #     #       self._callback(data)
        #     #     File "/Users/rbeyer/.anaconda3/envs/vipersci/lib/python3.7/site-packages/yamcs/tmtc/client.py", line 62, in _wrap_callback_parse_parameter_data
        #     #       on_data(parameter_data)
        #     #     File "./watch_cam.py", line 68, in on_data
        #     #       raise ValueError("Every fourth exception.")
        #     #   ValueError: Every fourth exception.
        #     #   Not running
        #     #   <class 'ValueError'>
        #     #   Every fourth exception.
        #     sleep(5)
        # else:
        #     print("Subscription stopped running.")

        #     try:
        #         print(subscription.result())
        #     except Exception as err:
        #         print(type(err))
        #         print(err)

        # This attempt to use concurrent.futures.wait fails.
        # Even though the subscription has resulted in an error in the
        # WebSocketSubscriptionManager and is now carrying that exception,
        # the concurrent.futures.wait() function doesn't ever return.
        # I'd need to completely understand how concurrent.futures.wait()
        # works, but it looks complicated and the above "while 
        # subscripttion.running()" approach seems workable.
        #   print("Entering concurrent.futures.wait")
        #   done, not_done = concurrent.futures.wait(
        #       (subscription, ),
        #       return_when=concurrent.futures.FIRST_EXCEPTION
        #   )
        #   print("Exited concurrent.futures.wait")

        #   print("This should halt excution.")
        #   for fs in done:
        #       print(fs)

        #   for fs in not_done:
        #       print(fs)


        with open(args.json, "w") as f:
            json.dump(watched, f, indent=2, sort_keys=True)

    else:
        parser.print_usage()


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
