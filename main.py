import sys

import CLI.Commands as Commands

import Infra.Display.textWorker as textWorker
import Infra.Display.characterWorker as characterWorker

from CLI.Presenter import Console
from Infra.Data import DataManager
from Infra.WebApi.WebWorker import WebWorker

def parse_arguments(tokens):

    args: list[str] = []
    opts: dict[str, str | bool] = {}

    i = 0
    while i < len(tokens):
        arg = tokens[i]
        if arg.startswith("-"):
            if i + 1 < len(tokens) and not tokens[i + 1].startswith("-"):
                opts[arg] = tokens[i + 1]
                i += 1
            else:
                opts[arg] = True
        else:
            args.append(arg)
        i += 1

    return args, opts

def main():

    tokens = parse_arguments(sys.argv[1:])

    args, quargs = tokens

    mode = args[0] if args else None

    while True:
        if mode == "game":  
            worker = characterWorker.CharacterShell
            break
        elif mode == "text":
            worker = textWorker.DocumentShell 
            break
        else:
            mode = input("please choose an operating mode: <game/text>")

    s = Commands.shell(worker, Console(), DataManager(), WebWorker(), mode)
    s.run()

           
if __name__ == "__main__":
    main()