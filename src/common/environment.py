from dotenv import load_dotenv
import os

# This is to setup the environment variables defined in an application-env file.
def setup(env_file: str):
    # all custom settings
    if not load_dotenv(env_file):
        raise RuntimeError(f"The config-file for setting up environment variables could't be found - {env_file}")
    # set user-agent
    os.environ['USER_AGENT'] = 'RAGUserAgent'
    