"""
Pyflakes checker to be used with API
"""

import compiler
from exceptions import SyntaxError
from pyflakes import checker 
from pygments import highlight
from pygments.lexers import PythonLexer
from pygments.formatters import HtmlFormatter, TerminalFormatter
from termcolor import colored
import sys, os, codecs
sys.stdout = codecs.getwriter('utf8')(sys.stdout)

def check_source(code_string, filename = "<string>"):
    """Checker function to be used in code"""
    
    try:
        compile(code_string, filename, "exec")
    except SyntaxError, value:
        msg = value.args[0]

        (lineno, offset, text) = value.lineno, value.offset, value.text
        
        if text is None:
            return [{"line": 0, "offset": 0, 
                "message": u"Problem decoding source"}]

        else:
            line = text.splitlines()[-1]

            if offset is not None:
                offset = offset - (len(text) - len(line))
            else:
                offset = 0

            return [{"line": lineno, "offset": offset, "message": msg}]

    else:
        tree = compiler.parse(code_string)
        w = checker.Checker(tree, filename)
        w.messages.sort(lambda a, b: cmp(a.lineno, b.lineno))
        return [{"line": warning.__dict__.get("lineno", 0), 
                        "offset": warning.__dict__.get("offset", 0),
                        "message": warning.message % warning.message_args
                    } for warning in w.messages]



class Flakement(object):
    """The main Flakement class."""
    def __init__(self, code_string, filename):
        
        self.code_string, self.filename = code_string, filename
        self.code_errors = check_source(code_string, filename)

    def _enumerated_code_lines(self):
        code_lines = self.code_string.splitlines(1)

        for k,v in enumerate(code_lines):
            code_lines[k] = "% 4s: %s"%(k + 1, v,)

        return code_lines

    def _adjusted_line_padding(self, line, line_pad):
        code_lines = self._enumerated_code_lines()

        line_pad_up = line - line_pad
        line_pad_down = line + line_pad
        
        if line_pad_up < 0: line_pad_up = 0
        if line_pad_down > len(code_lines): line_pad_down = len(code_lines)

        return line_pad_up, line_pad_down

    
    def terminal_output(self, line_pad = 3):
        
        if not self.code_errors == []:
            
            print (colored("File: %s"%(self.filename),
                    "white", "on_red"))
            code_lines = self._enumerated_code_lines()
        
            for ex in self.code_errors:
                line = ex["line"]
                message = ex["message"]
                offset = ex["offset"]
                        
                line_pad_up, line_pad_down = \
                    self._adjusted_line_padding(line, line_pad)

                sys.stdout.write(highlight(
                    "".join(code_lines[line_pad_up:line-1]),
                    PythonLexer(), TerminalFormatter()))
                print (colored(code_lines[line-1], "white", "on_red"))
                sys.stdout.write(highlight(
                    "".join(code_lines[line:line_pad_down]),
                    PythonLexer(), TerminalFormatter()))
                print "\n"
                print (colored("L-%s:C-%s %s"%(line, offset, message),
                    "white", "on_red"))
                print "\n\n"

    
    def terminal_full_output(self):
        
        if not self.code_errors == []:
        
            print (colored("File: %s"%(self.filename),
                    "white", "on_red"))
            code_lines = self._enumerated_code_lines()
        
            error_lines = [ex["line"] for ex in self.code_errors]

            for ln,cl in enumerate(code_lines):
                if ln + 1 not in error_lines:
                    sys.stdout.write(highlight(cl, PythonLexer(),
                        TerminalFormatter()))
                else:
                    print colored (cl, "white", "on_red")
            print "\n"
            for ex in self.code_errors:
                line = ex["line"]
                offset = ex["offset"]
                message = ex["message"]
                print (colored("L-%s:C-%s %s"%(line, offset, message),
                    "white", "on_red"))
            print "\n\n"

    
    def html_output(self, linenos = "table", hl_errors = True,
            lineanchors = "code-line"):
        """HTML Output for the Flakements class"""
        if hl_errors:
            hl_lines = [ex["line"] for ex in self.code_errors]
        return highlight(self.code_string, PythonLexer(), 
                HtmlFormatter(linenos = linenos, hl_lines = hl_lines, 
                    lineanchors = lineanchors)), self.code_errors
        
def main():
    args = sys.argv[1:]
    if args:
        for arg in args:
            if os.path.isdir(arg):
                for dirpath, dirnames, filenames in os.walk(arg):
                    for filename in filenames:
                        if filename.endswith('.py'):
                            flak = Flakement(
                                    codecs.open(
                                        os.path.join(dirpath, filename),
                                        "r","utf-8").read(), filename)
                            flak.terminal_full_output()
            else:
                flak = Flakement(codecs.open(arg, "r", "utf-8").read(), arg)
                flak.terminal_full_output()
    else:
        flak = Flakement(sys.stdin.read(), '<stdin>')
        flak.terminal_full_output()

    raise SystemExit(0)

if __name__ == "__main__":
    main()
