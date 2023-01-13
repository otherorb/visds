from dagster import asset

@asset
def vis_raw_to_db():
    # This asset/op takes several parameters and pushes them where they 
    # need to be. 
    # First, we need to receive the raw_header from the job (vis_raw_processing) 
    # which is called by the Watcher callback function.
    # Second, we need to know how to connect to the postgres database and write to
    # the Raw_Products table.
    # The first is a dictionary object passed to the vis_raw_processing job.
    # The second is a set of environment variables that's configured in the .env
    # file stored at the root of the visdag directory structure. 
    # However, instead of reading this environment variable multiple times, I
    # want to materialize this as couple of assets. The first asset is called 
    # vis_db_config and it returns a dictionary called 'raw_db'
    print("This is the vis_raw_to_db asset")
