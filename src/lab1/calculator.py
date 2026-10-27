"""
Simplest possible calculator
"""

if __name__ == "__main__":
    print("print exit to quit, otherwise - free ride")
    s = input()
    while s != "exit":
        try:
            print("=", end="")
            print(eval(s))
        except SyntaxError as se:
            print("SYNTAX_ERROR: write better next time")
        except NameError as ne:
            print("NAME_ERROR: didn't address the variable properly, ig")
        except TypeError as te:
            print("TYPE_ERROR: adding strings and ints, are we fr :sob:")
        except Exception as e:
            print("EXCEPTION: something went wrong, couldn't tell you :(")
        finally:
            s = input()

    print("bye-bye")
