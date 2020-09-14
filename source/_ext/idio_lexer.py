from pygments.lexer import RegexLexer, bygroups
from pygments.token import *

from sphinx.highlighting import lexers

import re

class IdioLexer(RegexLexer):
    name = 'idio'
    filenames = ['*.diff']

    # following in the style of lisp.py and shell.py
    
    keywords = (
        'function', 'define', 'if', 'cond', 'and', 'or', 'not', 'case'
    )

    builtins = (
        '+', '-', '*', '/',
        'lt', 'le', 'ge', 'gt',
        'pair', 'ph', 'pt'
    )

    infix_operators = (
        ':=', ':~', ':*', ':$', '='
    )

    valid_symbol = r'[\w!$%*+/:<=>?@^~-]+'
    
    tokens = {
        'root': [
            # ellipses -- used a lot in examples!
            (r'\.\.\..*?', Comment),
            # whitespace is regular text
            (r'\s+', Text),

            # numbers
            (r'-?\d+\.\d+', Number.Float),
            (r'-?\d+', Number.Integer),

            # strings
            (r'"(\\\\|\\"|[^"])*"', String),
            (r"'" + valid_symbol, String.Symbol),

            # constants
            (r'(#n|#t|#f)', Name.Constant),

            # infix operators
            ('(%s)' % '|'.join (re.escape (entry) + ' ' for entry in infix_operators), Keyword),

            (r'\b([^\s]+)(\s+)(:=|:~|:*|:\$|=|and|or)\b', bygroups (Text, Text, Operator)),
            (r'.+?', Text)
        ]
    }


def setup(app):
    lexers['idio'] = IdioLexer()
