from pygments.lexer import RegexLexer, bygroups
from pygments.token import *

from sphinx.highlighting import lexers

import re

__all__ = [ 'IdioLexer' ]

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
            # comments
            (r';.*$', Comment.Single),
            (r'#\*', Comment.Multiline, 'multiline-comment'),
            (r'#\|', Comment.Multiline, 'multiline-sl-comment'),
            (r'#;\s*\(', Comment, 'sexp-comment'),
            # ellipses -- used a lot in examples!
            (r'\.\.\..*?$', Comment),

            # whitespace is regular text
            (r'\s+', Text),

            # numbers
            (r'-?\d+\.\d+', Number.Float),
            (r'-?\d+', Number.Integer),
            (r'#d\d+', Number.Integer),
            (r'#o[0-7]+', Number.Integer),
            (r'#x[0-9a-fA-F]+', Number.Integer),

            # strings
            (r'"(\\\\|\\"|[^"])*"', String),
            (r"'" + valid_symbol, String.Symbol),

            # constants
            (r'(#n|#t|#f)', Name.Constant),

            # infix operators
            ('(%s)' % '|'.join (re.escape (entry) + ' ' for entry in infix_operators), Keyword),

            (r'\b([^\s]+)(\s+)(:=|:~|:*|:\$|=|and|or)\b', bygroups (Text, Operator, Text)),

            (r'.+?', Text)
        ],
        'multiline-comment': [
            (r'#\*', Comment.Multiline, '#push'),
            (r'\*#', Comment.Multiline, '#pop'),
            (r'#\|', Comment.Multiline, 'multiline-sl-comment'),
            (r'[^#*]+', Comment.Multiline),
            (r'[#*]', Comment.Multiline),
        ],
        'multiline-sl-comment': [
            (r'#\|', Comment.Multiline, '#push'),
            (r'\|#', Comment.Multiline, '#pop'),
            (r'#\*', Comment.Multiline, 'multiline-comment'),
            (r'[^#|]+', Comment.Multiline),
            (r'[#|]', Comment.Multiline),
        ],
        'sexp-comment': [
            (r'\(', Comment, '#push'),
            (r'\)', Comment, '#pop'),
            (r'[^()]+', Comment),
        ]
    }


def setup(app):
    lexers['idio'] = IdioLexer()
