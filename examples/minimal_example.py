import logging

from config_guard import Config, register_param

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    register_param(name="parameter_name")

    Config.update(**{"PARAMETER_NAME": 10.0}, reason="Initial set")
    print("Updated:", Config.get("parameter_name"))
