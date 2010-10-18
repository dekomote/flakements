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
import uuid

sys.stdout = codecs.getwriter('utf8')(sys.stdout)

FULL_TRIM = 2
SMALL_TRIM = 1
NO_TRIM = 0

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


def pep8_source(code_string):
    """docstring for pep8_source"""
    
    temp_filename = uuid.uuid4().hex + ".py"
    temp_file = open(temp_filename, "wb").write(codecs.BOM_UTF8 + code_string.encode("utf-8"))
    pep8_output = os.popen("pep8 %s"%temp_filename).read()
    os.remove(temp_filename)
    return _parse_pep8(pep8_output)


def _parse_pep8(pep8_output):
    """docstring for _parse_pep8"""
    if not pep8_output:
        return []
    
    pep8_lines = pep8_output.splitlines(1)
    return [{"line": int(pl.split(":")[1]), "offset": int(pl.split(":")[2]), "message": pl.split(":")[3].rstrip("\n")} for pl in pep8_lines]
        


class Flakement(object):
    """The main Flakement class."""
    def __init__(self, code_string, filename):
        
        self.code_string, self.filename = code_string, filename
        self.code_errors = check_source(code_string, filename)
        self.pep_errors = pep8_source(code_string)

    def _enumerated_code_lines(self):
        code_lines = self.code_string.splitlines(1)

        for k,v in enumerate(code_lines):
            code_lines[k] = "% 4s: %s"%(k + 1, v,)

        return code_lines

    
    def terminal_full_output(self, trim_output = NO_TRIM):
        
        if not self.code_errors == []:
        
            print (colored("File: %s"%(self.filename),
                    "cyan"))
            code_lines = self._enumerated_code_lines()
            code_error_lines =  [ex["line"] for ex in self.code_errors]
            pep_error_lines =  [ex["line"] for ex in self.pep_errors]
            error_lines = code_error_lines + pep_error_lines 
            
            if trim_output == SMALL_TRIM:
                low_line = min(error_lines)
                high_line = max(error_lines)
            else:
                low_line = 0
                high_line = len(code_lines)

            for ln,cl in enumerate(code_lines): 
                if ln >= low_line and ln <= high_line:
                    if ln + 1 not in error_lines:
                        if not trim_output == FULL_TRIM:
                            sys.stdout.write(highlight(cl, PythonLexer(),
                                TerminalFormatter()))
                    else:
                        if ln + 1 in code_error_lines and ln + 1 in pep_error_lines:
                            print colored(cl.rstrip("\n"), "white", "on_magenta")
                        elif ln + 1 in code_error_lines:
                            print colored(cl.rstrip("\n"), "white", "on_red")
                        else:
                            print colored(cl.rstrip("\n"), "white", "on_blue")

            print "\n"
            self.print_errors_terminal()

    def print_errors_terminal(self):
        for ex in self.code_errors:
            line = ex["line"]
            offset = ex["offset"]
            message = ex["message"]
            print (colored("L-%s:C-%s %s"%(line, offset, message),
                "white", "on_red"))
        for ex in self.pep_errors:
            line = ex["line"]
            offset = ex["offset"]
            message = ex["message"]
            print (colored("L-%s:C-%s %s"%(line, offset, message),
                 "white", "on_blue"))
        print "\n\n" 

    
    def html_output(self, linenos = "table", hl_errors = True,
            lineanchors = "code-line"):
        """HTML Output for the Flakements class"""
        if hl_errors:
            hl_lines = [ex["line"] for ex in self.code_errors + self.pep_errors]
        return highlight(self.code_string, PythonLexer(), 
                HtmlFormatter(linenos = linenos, hl_lines = hl_lines, 
                    lineanchors = lineanchors)), self.code_errors, self.pep_errors
        
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
                            print flak.terminal_full_output()
            else:
                flak = Flakement(codecs.open(arg, "r", "utf-8").read(), arg)
                print flak.terminal_full_output()                
    else:
        flak = Flakement(sys.stdin.read(), '<stdin>')
        flak.terminal_full_output()

    raise SystemExit(0)

if __name__ == "__main__":
    main() 
