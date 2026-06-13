from qwshen.launcher import Launcher

def test_answer(questions: list[str], session_id: str):
    _, services = Launcher.start()
    for service, _ in services:
        print(f"Service: {service.get_name()} is serving ...")
        for question in questions:
            print(f"\n\nQuestion: {question}")
            for message in service.process(question, kwargs={"session_id": session_id}):
                print(message.content if message is not None else "\n", end="", flush=True)
