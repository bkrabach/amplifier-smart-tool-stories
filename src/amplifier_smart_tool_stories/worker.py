import sys

from .lib import Stories

if __name__ == "__main__":
    api = Stories(sys.argv[1], model_env="--model-env" in sys.argv[3:])
    api.run_operation(sys.argv[2])
