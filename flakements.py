"""
Flakements wraps pyflakes and pep8, enchancing their output
with pygments. Can be used for output of code/errors or just
for in-source code checking. The helper functions check_source
and pep8_source, provide easy interface to pep8+pyflakes
and unify the output of those tools.

USAGE flakements.py filename
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
from optparse import OptionParser

#we need to make stdout utf-8
sys.stdout = codecs.getwriter('utf8')(sys.stdout)

FULL_TRIM = 2
SMALL_TRIM = 1
NO_TRIM = 0

def check_source(code_string, filename = "<string>"):
    """Checking code string with pyflakes.
        filename is optional as it is needed by
        the compiler.
        
        returns list"""
    
    try:
        #compile the code and check for syntax errors
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
        #no syntax errors, check it with pyflakes
        tree = compiler.parse(code_string)
        w = checker.Checker(tree, filename)
        w.messages.sort(lambda a, b: cmp(a.lineno, b.lineno))

        return [{"line": warning.__dict__.get("lineno", 0), 
                        "offset": warning.__dict__.get("offset", 0),
                        "message": warning.message % warning.message_args
                    } for warning in w.messages]


def pep8_source(code_string):
    """Check code string with pep8 script.
        
        returns list"""
    
    temp_filename = uuid.uuid4().hex + ".py"
    temp_file = open(temp_filename, "wb").write(
            codecs.BOM_UTF8 + code_string.encode("utf-8"))
    pep8_output = os.popen("pep8 %s"%temp_filename).read()
    os.remove(temp_filename)
    return _parse_pep8(pep8_output)


def _parse_pep8(pep8_output):
    """pep8 script doesn't provide api so I had to
        hack through this one.
        
        returns list"""

    if not pep8_output:
        return []
    
    pep8_lines = pep8_output.splitlines(1)
    return [{"line": int(pl.split(":")[1]), 
            "offset": int(pl.split(":")[2]), 
            "message": pl.split(":")[3].rstrip("\n")} for pl in pep8_lines]
        


class Flakement(object):
    """The main Flakement class. When instanciated, the class
        has the code checked and keeps 2 lists with errors, one
        with pep8 errors and 1 with pyflakes errors.
        
        Provides methods for output on terminal/html.
        Uses pygments"""

    def __init__(self, code_string, filename):
        
        self.code_string, self.filename = code_string, filename
        self.code_errors = check_source(code_string, filename)
        self.pep_errors = pep8_source(code_string)

    def _enumerated_code_lines(self):
        """Returns a list of enumerated, formated code lines"""

        code_lines = self.code_string.splitlines(1)

        for k,v in enumerate(code_lines):
            code_lines[k] = "% 4s: %s"%(k + 1, v,)

        return code_lines

    
    def terminal_full_output(self, trim_output = NO_TRIM):
        """Prints the code and errors in terminal.
            Output can be trimmed to show only the error lines + errors -
            FULL_TRIM, show from first to last line with error - SMALL_TRIM,
            or NO_TRIM- shows the whole code. PEP8 and pyflakes error lines
            have different colors. If two different errors happen on same
            line, the line gets third color"""
        
        if not self.code_errors == [] or not self.pep_errors == []:

            self.print_code_terminal(trim_output = trim_output)
            print "\n"
            self.print_errors_terminal()
    

    def print_code_terminal(self, trim_output):
        """Prints the code with highlighted lines in terminal"""

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
                    if ln + 1 in code_error_lines and \
                            ln + 1 in pep_error_lines:
                        print colored(cl.rstrip("\n"), 
                                "white", "on_magenta")
                    elif ln + 1 in code_error_lines:
                        print colored(cl.rstrip("\n"), 
                                "white", "on_red")
                    else:
                        print colored(cl.rstrip("\n"), 
                                "white", "on_blue")


    def print_errors_terminal(self):
        """Prints the errors in terminal
            PEP8 and pyflakes errors get different
            colors."""

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
        """Returns a tuple of HTML output of the code and errors
            args affect the HtmlFormatter."""

        if hl_errors:
            hl_lines = [ex["line"] 
                    for ex in self.code_errors + self.pep_errors]
        return highlight(self.code_string, PythonLexer(), 
                HtmlFormatter(linenos = linenos, hl_lines = hl_lines, 
                    lineanchors = lineanchors)), \
                            self.code_errors, self.pep_errors
        
def main():
    """Main method"""
    
    usage = "%prog [options] input ..."
    
    parser = OptionParser(usage)
    parser.add_option('-t', '--trim', action = 'store', 
            type = 'choice', dest = 'trim', choices = ["0", "1", "2"],
            default = 0)
    parser.add_option('-o', '--output', action = 'store', 
            type = 'choice', dest = 'output', 
            choices = ["T_FULL", "T_CODE",
                "T_ERR", "HTML"],
            default = "T_FULL")
    
    options, args = parser.parse_args()
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
            else:
                flak = Flakement(codecs.open(arg, "r", "utf-8").read(), arg)
    else:
        flak = Flakement(sys.stdin.read(), '<stdin>')
    
    if options.output == 'T_FULL':
        flak.terminal_full_output(trim_output = int(options.trim))
    elif options.output == 'T_CODE': 
        flak.print_code_terminal(trim_output = int(options.trim))
    elif options.output == 'T_ERR': 
        flak.print_errors_terminal()
    elif options.output == 'HTML':
        print flak.html_output()

if __name__ == "__main__":
    main() 
