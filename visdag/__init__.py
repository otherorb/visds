import os
from dagster import (
        asset,
        AssetsDefinition,
        AssetSelection,
        Definitions,
        define_asset_job,
        load_assets_from_package_module,
        )
from . import assets
from . import jobs


vis_raw_processing = define_asset_job(name="vis_raw_processing", selection="*")

defs = Definitions(
        assets=load_assets_from_package_module(assets),
        jobs = [vis_raw_processing,],
        )
