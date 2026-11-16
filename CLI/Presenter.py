class Console:

    @staticmethod
    def console_log(message: str) -> None:
        print(message)

    @staticmethod
    def get_str(message: str) -> str:
        return rf"{input(f'{message} ')}" 
    
    @staticmethod
    def get_int(message: str) -> int:
        msg = message 
        
        while True:
            try:
                answer = input(msg)
                return int(answer)
            except ValueError:
                msg = "Please, enter a valid integer: "


