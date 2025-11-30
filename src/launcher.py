import argparse
from threading import Thread
from common.component import Runner
from definition.parse import Parser
from service.index import DocumentOperator
from service.service import ServiceOperator, ServiceRunner

class Launcher:
    @staticmethod
    def start() -> list[ServiceRunner, list[str]]:
        def_file, env_file = Launcher.__initialize_args()
        index_def, service_def = Parser(env_file=env_file).parse(def_file=def_file)

        if index_def is not None:
            indexers = DocumentOperator.setup(index_def)
            if len(indexers) > 0:
                def _run(runner: Runner) -> Thread:
                    thread = Thread(target=runner.run, name=runner.name)
                    thread.start()
                    return thread
                def _start():
                    for thread in [_run(runner) for runner in indexers]:
                       thread.join()
                Thread(target=_start, name="indexers").start()

        services = ServiceOperator.setup(service_def) if service_def is not None else []
        for service, _ in services:
            service.run()
        return services
    
    @staticmethod
    def __initialize_args():
        parser = argparse.ArgumentParser()
        parser.add_argument("-d", "--def", dest="def_file", help = "Please specify the definition file")
        parser.add_argument("-e", "--env", dest="env_file", help = "Please specify the environment file")
        args = parser.parse_args()

        if args.def_file is None:
            raise RuntimeError("Please provide definition file.")
        return args.def_file, args.env_file


def main():
    services = Launcher.start()
    for service, _ in services:
        print(f"Service: {service.get_name()} is started.")
        for messages in service.process("What is docker?", kwargs={"session_id": "test_session"}):
            print(messages)

        for messages in service.process("How to set up a docker container?", kwargs={"session_id": "test_session"}):
            print(messages)

if __name__ == "__main__":
    main()