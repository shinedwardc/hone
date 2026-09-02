import sys

# Every branch that fails to get an answer says the same thing: assume, and say so.
FALL_BACK = (
    "Proceed with the best assumption you can defend, and state that assumption "
    "in your answer."
)

schema_ask_user = {
    "type": "function",
    "function": {
        "name": "ask_user",
        "description": (
            "Ask the user which behaviour they consider wrong, when the task never "
            "said, and wait for their reply. This is only for what is in their head: "
            "which of the things this program does is the one they want changed. It is "
            "never for anything you can work out yourself — how the code behaves, what "
            "a convention or definition says, what the answer is by the stated rules. "
            "The test: if your question names the standard that would answer it "
            "(\"what should the precedence be, in standard mathematical order of "
            "operations?\"), you have just answered it, and asking is quizzing the "
            "user on your own job. This must be your first action in the run or not at "
            "all, because a task that never said what to fix is something you can see "
            "from the task alone; once you have started looking, the diagnosis is "
            "yours. You get one question, and a run with nobody watching cannot answer "
            "at all, so be ready to continue on an assumption you state out loud."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": (
                        "One specific question, answerable in a sentence. Give the case "
                        "you ran and the output you got, so the user only has to supply "
                        "the missing expectation, e.g. 'main.py \"widget:10\" prints a "
                        "total of 27.0 and tests.py passes; what should the total be?'"
                    ),
                },
            },
            "required": ["question"],
        },
    },
}


def ask_user(question: str) -> str:
    question = question.strip()
    if not question:
        return "Error: ask_user needs a non-empty question."

    if not sys.stdin.isatty():
        return f"Error: this run is not interactive, so nobody can answer. {FALL_BACK}"

    print(f"\nThe agent is asking:\n  {question}")
    try:
        answer = input("Your answer (blank to skip): ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return f"Error: the question went unanswered. {FALL_BACK}"

    if not answer:
        return f"Error: the user skipped the question. {FALL_BACK}"

    return f"The user answered: {answer}"
