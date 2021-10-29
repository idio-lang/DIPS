.. include:: ../global.rst
.. include:: <isonum.txt>

***********
Unix Shells
***********

The word *shell* itself was coined by `Louis Pouzin
<https://en.wikipedia.org/wiki/Louis_Pouzin>`_ after implementing
`RUNCOM <https://en.wikipedia.org/wiki/Run_commands>`_ (from which we
get the fossil term/suffix *rc*) at MIT in the early-mid 1960s for its
:abbr:`CTSS (Compatible Time-Sharing System)`.  He wrote a paper on
how to implement it for `Multics
<https://en.wikipedia.org/wiki/Multics>`_ before returning to his
native France.  `Glenda Schroeder
<https://en.wikipedia.org/wiki/Glenda_Schroeder>`_ subsequently
implemented the Multics shell the predecessor of the Unix shell today.

There are a few Unix shells out there.  I've used :lname:`Bash` since,
it feels like, forever and so it'll be :lname:`Bash` that I'll be
using for examples.

I'm by no means an expert in :lname:`Bash`, I think we all settle into
our favoured idioms and every time I read the man page I came away
with something new.

.. aside:: A quick shout-out, here, to :ref-author:`Chet Ramey`, one
           of the silent heroes of FOSS_.  He's been quietly
           maintaining :lname:`Bash` for a quarter of a century --
           since the original author, :ref-author:`Brian Fox` was laid
           off by the FSF_.

GNU_'s Bash_ (first released in 1989), the "Bourne Again shell" is, of
course, a nod to :ref-author:`Stephen Bourne`'s `Bourne shell`_ (first
released in 1979) created as a free software alternative and picking
up a few features from elsewhere.  You used to get a Bourne shell when
you logged in on a (proprietary!) Unix box.  The Bourne shell was a
replacement for :ref-author:`Ken Thompson`'s `Thompson shell`_
(introduced in the first version of Unix in 1971) which gave us our
basic command orchestration syntax:

.. code-block:: sh

   < in-file command1 | command2 > out-file

I can't help but think that that original choice of the ``<``, ``>``
and ``|`` symbols creating the visually pleasing ``< | >`` structure
is a work of genius.  Or a stroke of luck.  Hard to say.  Still, well
done, Ken.  His name rings ma bell, mind, has he done anything else?

You can read his 1976 paper on `The Unix Command Language
<https://susam.github.io/tucl/the-unix-command-language.pdf>`_ and its
key notion of "I/O streaming and interconnection of utility program.".

The Bourne shell subsequently added features like:

- command substitution using backquotes
- here documents
- ``for`` loops
- ``case`` statements

and, perhaps most intriguingly, the use of file descriptor 2 for error
messages.

I can't deny having had :ref-author:`Bill Joy`'s `C shell`_ (first
released in 1978) as my default shell for a while as a youth -- never
forget :ref-author:`Tom Christiansen`'s 1995 `Csh Programming
Considered Harmful`_.  :ref-author:`Ken Greer`'s tsch_ (first released
in 1981) added Tenex-style file name completion to the C shell which
:lname:`Bash` subsequently re-imagined.

I wrote a lot of code in :ref-author:`David Korn`'s KornShell_ (first
released in 1983) when it was the most reliably-available shell across
various development, test and production systems and through several
substantial operating system upgrades.

I've barely touched either of :ref-author:`Kenneth Almquist`'s Ash_
(first released in 1989 again as a free software alternative to the
Bourne shell) or its derivative, :ref-author:`Herbert Xu`'s Debian
Almquist shell, Dash_ (first released in 1997) which appears in many
embedded systems through Busybox_ and more recently as ``/bin/sh`` in
Ubuntu_ and Debian_ systems.

I've not used :ref-author:`Paul Falstad`'s Zsh_ (first released
in 1990) -- although I see Mac OS X is encouraging me to switch, *No,
Mac OS X, no!* -- and so neither its popular "Oh My Zsh" collection of
plugins and themes.

.. rst-class:: center

---

There's a bit of a theme, there, though.  Original proprietary Unix
shells written in the late 70s or so and a suite of free software
replacements written in the late 80s.  Does that mean there's been no
new shell for thirty years?

No, of course not.  What we haven't had is any major distribution
changing their default interactive shell or default shell
alternatives.

.. sidebox:: This is by no means a remotely comprehensive list but
             rather a reflection that at some point I realised I ought
             to write some of these down.

	     As you can see, work continues on the shell.

:ref-author:`Axel Liljencrantz`'s friendly interactive shell, fish_
(first released in 2005) is focused on usability and interactive use.

:ref-author:`Andy Chu`'s Oil_ shell (first released in 2017) is trying
to be a better POSIX shell for programmers.

:ref-author:`Laurence Morgan`'s Murex_ shell (official release
pending) is designed for DevOps productivity.

:ref-author:`Ilya Sher`'s Next Generation Shell NGS_ (from 2013) where
he's looking at the same annoyances as I do (poor data structures in
the shell and a lack of system administration focus in general purpose
languages).

:ref-author:`Alessandro Nadalin`'s ABS_ programming language
(from 2018) "bringing back the joy of shell scripting".

There are a slew of shells featuring the idea of passing structured
data through pipelines -- something made most famous by Microsoft's
PowerShell_.

* :ref-author:`Andrew Chambers`' Janetsh_ is an interactive shell and
  scripting tool based on the Janet_ programming language (which has a
  Lisp-ish notation).

* :ref-author:`Qi Xiao`'s elvish_ (first released in 2017) is an
  interactive shell and programming language.

* :ref-author:`Matt Russell`'s Mash_ (2016 - 2017?) is another
  object-passing shell.

* :ref-author:`Jonathan Turner`'s Nushell_ (first released in 2019) is
  another structured data pipelining shell.

* :ref-author:`Jack Orenstein`'s Marcel_ (the name appears to be from
  the video short, :ref-title:`Marcel the Shell with Shoes On`,
  enjoy!) (from 2020?)

Stepping away from regular shells, :ref-author:`Olin Shivers`' Scsh_
(first released in 1994 although development may have stalled in 2006)
is a shell embedded in :lname:`Scheme` together with a syscall library
for systems programming.

There are even papers being written about `The Once and Future Shell
<https://angelhof.github.io/files/papers/shell-2021-hotos.pdf>`_.

The Interactive Shell
=====================

The shell can be described as two quite different things.  On the one
hand there is a (textual) *user interface* where users input shell
commands at a prompt, a form of :abbr:`REPL
(Read-Evaluate-Print-Loop)`.  There's a huge opportunity here for
customising the look and feel of an interactive shell from the prompt
through command editing, command and argument completion and onto
history replay.

On the other hand, when a shell is not interactive, it'll be reading
commands from a script and isn't concerned about prompts, history or
completion.

I'll state quite clearly that we're not here for the interactive/user
interface functionality of the shell.  We're looking at shell
scripting and if we can make better shell *programs*.  :lname:`Bash`,
:lname:`Zsh` and :lname:`fish` and any number of others have more than
we need for "|uarr| :kbd:`RETURN`" or whatever fancy interaction with
the shell you care to name.

.. aside::

   On a related note, read a little about the `tty
   <http://www.linusakesson.net/programming/tty/index.php>`_.

This is partly because we're unlikely to do a better job but mostly
because it's *hard*.  It's *really hard*.  I can't find a reference
for it any more but one of the man pages for terminal-related
functionality (termio?) used to note that figuring out the terminal is
probably the hardest thing a user had to do which was unfortunate
because it was one of the first things a user had to do.

The guys who are making the use interaction more pleasant are still
discovering bugs in decades-old terminal drivers behaving badly
requiring all sorts of artistic solutions -- look at `Zsh and Fish’s
simple but clever trick for highlighting missing linefeeds`_ and the
follow-up commentary in https://news.ycombinator.com/item?id=23520240.
The problem revolves around the nicety of handling a program that
doesn't complete its output with a newline:

.. code-block:: bash

   % echo hello
   hello
   % echo -n hello
   hello% 

Notice that my prompt, :samp:`% \ `, appears at the end of the second
command's output, in column 5, in this case, not on a clear(ed) line
like the others.

You, the shell, don't know what the program printed so, broadly, the
trick is to *always* print a "missing newline" glyph (:rev:`%`, ¶, ⏎
or something) then some terminal subtleties: print $COLUMN-1 spaces;
carriage return and *then* print out the prompt (and a
clear-to-end-of-line to flush the remaining spaces).

* If the program emitted a trailing newline then the above will have
  printed the glyph in column 0 and spaces up to the end of line and
  then the carriage return will have brought you back on top of the
  glyph.  The shell's prompt will over-write the glyph and everyone is
  happy.

* If the program didn't print a trailing newline then the output will
  have been followed by the glyph and enough spaces to take you onto
  the next line of the terminal.  The carriage return takes you back
  to column 0 *of this next line* and the shell prints its prompt
  leaving the impression of the glyph at the end of the text:

.. code-block:: bash

   % echo hello
   hello
   % echo -n hello
   hello⏎
   % 

That is the least of it, though, as the real problems come when
asserting what any given terminal will do when you print a character
(here, one of those spaces) in the last column of the line.  The
cursor goes in "the next" column, right?  Which, given that we've just
printed something in the last column means we wrap round onto the next
line (with an implied newline).  Er, nope.  You've obviously missed
out on the joys of clanking away on an electro-mechanical teletype or
one of its :term:`VDU` successors.  There are terminal capabilities
that describe various end-of-line behaviours and then there's bugs in
the terminal's behaviour.

We don't need to go there so let's not.  That's not to say we'll do
nothing with the terminal -- we are *required* for job control to mess
around a little bit with terminals -- but there's enough to do as it
is.  Let's not get distracted.

*Meh!* Except we might want to get distracted, eventually.  In an
ideal world I suspect we'll have incorporated a table-driven
:term:`reader` by then which would (probably) make life a lot easier.
In the meanwhile, we haven't got one of them and dealing with the
terminal sounds like it'll be a pain.

Oh but we could really do with something, mind you, as I keep typing
:kbd:`Ctrl-P` and feeling like I've fallen into ``vi-mode``.  It
is... *challenging* ...to have no editing options at the prompt.  We
can't readily incorporate (our men) :ref-author:`Chet Ramey` (after
:ref-author:`Brian Fox`)'s Readline_ library thanks to our slightly
pedagogical stance of not incorporating things we can't explain.  No
black boxes.

(You can run :program:`rlwrap`, of course.)


.. include:: ../commit.rst

