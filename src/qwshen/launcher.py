import argparse
import time
from threading import Thread
from functools import reduce

from qwshen.common.component import Runner
from qwshen.definition.parse import Parser
from qwshen.service.index import DocumentOperator
from qwshen.service.service import ServiceOperator, ServiceRunner

class Launcher:
    @staticmethod
    def start() -> list[ServiceRunner, list[str]]:
        def_file, env_file = Launcher.__initialize_args()
        index_def, service_def = Parser(env_file=env_file).parse(def_file=def_file)

        indexers = []
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
        return indexers, services
    
    @staticmethod
    def __initialize_args():
        parser = argparse.ArgumentParser()
        parser.add_argument("-d", "--def", dest="def_file", help = "Please specify the definition file")
        parser.add_argument("-e", "--env", dest="env_file", help = "Please specify the environment file")
        args = parser.parse_args()

        if args.def_file is None:
            raise RuntimeError("Please provide definition file.")
        return args.def_file, args.env_file


def test_index():
    indexers, _ = Launcher.start()
    if reduce(lambda x, y: x or y, [indexer.index_scheduled() for indexer in indexers], False):
        try:
            print("Indexing scheduled. Press Ctrl+C to exit.")
            while True:
                time.sleep(30)
        except (KeyboardInterrupt, SystemExit):
            pass

def test_answer(questions: list[str], session_id: str):
    _, services = Launcher.start()
    for service, _ in services:
        print(f"Service: {service.get_name()} is serving ...")
        for question in questions:
            print(f"\n\nQuestion: {question}")
            for message in service.process(question, kwargs={"session_id": session_id}):
                print(message.content if message is not None else "\n", end="", flush=True)
