.. include:: ../global.rst
.. include:: <isonum.txt>

**************************
A Review of Shell Features
**************************

:socrates:`What's to like about the shell?`

Now, just to be clear, we're not asking if the ability to join two
commands together in a pipeline is something to be admired -- I like
to think that we can stumble through the :manpage:`pipe(2)`,
:manpage:`fork(2)` and :manpage:`execve(2)` man pages with qualified
success -- but rather whether the syntactic abstraction the shell
uses, here, ``command | command``, or something closely resembling it,
is what we want in our shell.

If it is then we need to start thinking about how we are going to
implement it.  Many of these abstractions are *infix*, arithmetic is
another example, ``1 + 2``.  I, for one, don't read this as ``add (1,
1)`` or ``pipe ("zcat file.tgz", "tar tf -")``, I'm reading it as a
*sequence* of operations, one I know I can arbitrarily extend.

We can add more arithmetic, ``1 + 2 * 3`` (let's hope we agree on
operator precedence!), or more filtering, ``zcat file.tgz | tar tf - |
grep foo``, casually.  It's more complicated with function calls:

.. code-block:: c

   add (1,
	mul (2, 3));

   pipe ("zcat file.tgz",
	 pipe ("tar xf -",
	       "grep foo"));

They look less straightforward and elegant and instead clumsy and
forced.  We can't see the wood for the trees.

Before we casually toss the problem of inline operators at
:program:`yacc`/:program:`bison` or go for it with ANTLR_ we need to
know if we are even going to *use* everyone's favourite language
parsers.  Hint: no.  *Not because they are easy but because they are
hard.*

Syntactic Structure
===================

Without getting lost in the detail the syntactic structure of shell
commands is very clean:

.. code-block:: bash

   ls -al *.txt

There's no pre-amble, superfluous syntactic clutter and no trailing
end-of-statement marker, the end of the line terminates the statement
(usually).  In fact, that last point, that the shell is, by and large,
*line-oriented* is something I'm quite keen to keep -- although it has
some unpleasant side-effects.

The first *word* is the name of the command to run and the remaining
words, separated by one or more whitespace characters are the
command's arguments.

Compare that with most languages which, for example, in :lname:`C`:

.. code-block:: c

   func (val1, val2);

Here we have the same word ordering (command then arguments) but also
have parenthesis separating the function name from the arguments and,
indeed, commas separating the arguments.  Now it doesn't take long to
realise why there's all that punctuation as languages like :lname:`C`
allow you to recursively call other functions in place of arguments:

.. code-block:: c

   func (sub1 (a1, a2), sub2 (b1, b2));

Which now has an impressive 10 pieces of punctuation and is getting
hard to read.  I, depending on whim, might have rewritten it as:

.. code-block:: c

   func (sub1 (a1, a2),
	 sub2 (b1, b2));

.. sidebox:: I suggest a strongly worded letter to the Editor,
             preferably hand-written in green ink.

	     Yours, *outraged* of Bileford.

(which is either more pleasant or is a calculated affront to public
decency and has you caused spontaneous apoplectic rage.  Such is the
modern way.)

Of interest, :lname:`Scheme` with its notorious superfluity of
parenthesis, looks like:

.. code-block:: scheme

   (func (sub1 a1 a2)
	 (sub2 b1 b2))

Go figure.

You can do the subroutine calling of a sorts with the shell's
:ref:`command substitution <command substitution>` operator ``$()``:

.. code-block:: bash

   ls -al $(generate_txt_file_names)

but you can't do that multiple times and distinguish the results:

.. code-block:: bash

   func $(sub1 $a1 $a2) $(sub2 $b1 $b2)

.. sidebox:: I know :lname:`C` doesn't return multiple values but you
             know what I mean, :lname:`C` retains the separation of
             results from function calls and the shell doesn't.

Here, ``func`` is going to see one long list of arguments, not two
(sets of arguments) as in :lname:`C`.


Variables Syntax
================

If I was going to drop one thing from shell syntax it would be its use
of *sigils*.  For the shell, just the one, ``$``, used to introduce
variables.

I think it's visual clutter and we should be more :lname:`C`- or
:lname:`Python`-like:

.. code-block:: c

   a = func (b, c);

rather than the mish-mash of:

.. code-block:: bash

   a=${b[i]}
   func $b $c

When do I use a sigil and when not?  Get rid of the lot.

(Except when we need them.)

Having said that, in the shell it is very common to use a variable
embedded in the assignment of another or in a string (string
interpolation).

So we might do:

.. code-block:: bash

   PATH=/usr/local/bin:$PATH

   echo "PATH=$PATH"

Both of those are very convenient, I have to say.  Are they
*required*, though?  What would we do elsewhere?  Actually, for the
former, I'm sure I'm not the only one who wrote a bunch of shell
functions to manipulate Unix paths (:envvar:`PATH`,
:envvar:`LD_LIBRARY_PATH`, :envvar:`PERL5LIB` etc.) resulting in
something like:

.. code-block:: bash

   path_prepend PATH /usr/local/bin

and you can imagine variants for modifying multiple related paths
simultaneously and various path normalisation functions (removing
duplicates etc.).  The style is more programming language-like, in
:lname:`Python` you might say:

.. code-block:: python

   sys.path.append ("/usr/local/lib/python")

As for string interpolation, I'm less sure I'd miss it in the above
for as I might use a format string of some kind as in :lname:`Perl`:

.. code-block:: perl

   printf "PATH=%s\n", $ENV{PATH};

or :lname:`Python`

.. code-block:: python

   print ("PATH={0}\n".format (os.environ['PATH']))

.. sidebox:: I often find myself visually scanning swathes of output
             to find the thing of interest.  Pattern matching by eye
             is much easier if columns line up.

Clearly, there's a lot more syntactic clutter, which I'm nominally
against, but I usually end up trying to control the output anyway.

.. _shell-here-document:

Here-document
-------------

There's another embedded-variable situation which I use often enough
where I'm generating a block of output (often a usage statement) or a
code-snippet for another language.  I'll be using a *here-document* (a
terrific bit of left-field thinking):

.. code-block:: bash

   perl << EOF
   printf "PATH=$PATH\n";
   EOF

where I'm ostensibly creating a (multi-line) string but substituting
in some variables.

You can get quite quickly annoyed, though, when :lname:`Bash`'s sigil,
``$``, conflicts with, in this case, one of :lname:`Perl`'s sigils
leaving you to judiciously escape some of them:

.. code-block:: bash

   perl << EOF
   my \$path = "$PATH";
   printf "PATH=%s\n", \$path;
   EOF

Here-documents in general, and code-snippets for other languages, in
particular, look at though they need a bit more thought.  It seems
like the here-document is some sort of template in which we perform
variable substitution when we see a ``$`` sigil introduce a variable,
``$var``.

The "other languages" variant is also crying out for some means to
choose the sigil itself.  Wouldn't it be great if we could have
written that as:

.. code-block:: bash

   perl << EOF
   my $path = "!PATH";
   printf "PATH=%s\n", $path;
   EOF

where ``!`` -- or some other sigil that *you* get to choose, something
appropriate to your template -- means we can write
as-native-as-possible :lname:`Perl`, in this case, with considerably
less hassle?

I have a cunning plan.

Environment Variables
---------------------

Another simple yet clever trick the shell plays is that all
*environment* variables are exposed as shell variables.  We don't need
to call ``getenv`` and ``putenv``/``setenv`` or indirect through a
named hash table like :lname:`Perl`'s ``$ENV{}`` or :lname:`Python`'s
``os.environ[]``.  They're right there as primary variables in the
script.

I like that.  Remember, we're operating at the level of orchestrating
programs and it seems right that we should have direct access to those
things we manipulate often.

Clearly there's a little bit of magic floating about as some shell
variables are marked for export and some not.

.. _`shell command`:

Shell Commands
==============

:lname:`Bash`, at least, has *simple commands*, *pipelines*, *lists*,
*compound commands*, *coprocesses* and *function definitions*. Let's
take a look at those.

.. _`shell simple command`:

Simple Commands
---------------

From :manpage:`bash(1)`:

    A simple command is a sequence of optional variable assignments
    followed by blank-separated words and redirections, and terminated
    by a control operator.  The first word specifies the command to be
    executed, and is passed as argument zero.  The remaining words are
    passed as arguments to the invoked command.

A *control operator* is one of ``|| & && ; ;; ;& ;;& ( ) | |&
<newline>``.

Variable Assignments
^^^^^^^^^^^^^^^^^^^^

Variable assignment is something I *do* use:

.. code-block:: bash

   TZ=GMT+0 date

   PATH=/somewhere/else/first:$PATH cmd args

This is a really neat trick, we make a change to the pending command's
environment (but, crucially, not our own).

It also looks tricky to parse, we need to be able to figure out the
following:

.. code-block:: bash

   CFLAGS=one-thing make CFLAGS=another-thing

I don't like that, it looks too hard.  We could have achieved the same
with a subshell:

.. code-block:: bash

   (
    PATH=/somewhere/else:$PATH

    cmd args
   )

Where, if we forget that the parenthesis have introduced a subshell
and think of it as a code block, I'm getting a sense of a transient
assignment, that ``PATH`` is a dynamic variable, we modify it for the
duration of the code block and that come the time we need to use it,
we figure out its value then.

Interestingly, and I said I learned something new every time I read
the man page, if :lname:`Bash` determines there is no command then the
variable assignments *do* affect the current shell's environment.  So,
changing the current shell's :envvar:`PATH`:

.. code-block:: bash

   PATH=/somewhere/else:$PATH

is a side-effect of the *absence* of a command rather than an explicit
shell-modifying statement in its own right.  :socrates:`Who knew?`
(The guy that wrote the man page did, for a start.)

Redirections
^^^^^^^^^^^^

:lname:`Bash`, at least, is fairly free with redirections, in the
sense that you can have lots of them and they are processed left to
right.  So:

.. code-block:: bash

   ls -al > foo > bar

will create both files :file:`foo` and :file:`bar` but :file:`foo`
will be empty and only :file:`bar` will have any contents.

I guess you're not meant to be doing that, as it looks like a mistake,
but rather more something like a sequence of pseudo-dependent
redirects:

.. code-block:: bash

   exec >log-file 2>&1

Here, of course, the order is critical as we are redirecting *stdout*
to :file:`log-file` and then redirecting *stderr* to wherever *stdout*
is currently (ie. :file:`log-file` not wherever it was when we started
processing the line).

Another example is stashing the current whereabouts of a file
descriptor:

.. code-block:: bash

   exec 3>&1 >log-file
   ...
   exec >&3

where we redirect file descriptor 3 to wherever *stdout* is currently
pointing and then *stdout* to :file:`log-file`.  We do our thing with
*stdout* going to :file:`log-file` and then redirect *stdout* to
wherever file descriptor 3 is pointing -- handily, where *stdout* was
originally pointing.

It's a neat trick and handy in a script for directing tedious output
to a log file whilst simultaneously retaining the ability to print to
the original *stdout* with the likes of ``echo "don't stop
believing..." >&3`` to keep the user's hopes up but it has a terrible
failing.  We, the punter, are somehow supposed to know when file
descriptors are free to use.  How do we know that?  Ans: we don't, we
just stomp over, in this case, file descriptor 3 regardless.

In other languages, such as :lname:`Python`, you might see an
expression of the form:

.. code-block:: python

   with open ("log-file", "w") as f:
       f.write ()

which is nearly what we want -- we actually want to transiently
replace *existing* file descriptors and in such a way that they can be
inherited by any commands we run.  Something more like:

.. parsed-literal:: 

   with open ("log-file", "w") as *stdout*:
       ...

(albeit we've skipped our provision to keep the user up to date.)

Obviously IO redirection is a requirement but I sense that this
carefree way with file descriptors is really because the shell can't
maintain a reference to a file descriptor outside of command
invocation.  In a programming language with access to the usual
systems programming libraries we'd be calling :manpage:`dup(2)` in
some form and be able to pass the return value around as you would
hope.

One problem, though, with our programming language design hats on, is
that this IO redirection is *inline* -- in the sense that the IO
redirection is textually mixed up with the command and its arguments
-- and more particularly is an infix operation.  It's very convenient
to have it parsed out of the line for us but that, to us doing
language design, is a problem.  *We* now have to parse it out.  I'm
not getting good vibes about that.

.. _`shell-pipeline`:

Pipelines
---------

.. code-block:: bash

   bzcat logfile | grep pattern | sort -k 2n > file

There's a certain elegant simplicity in writing a shell pipeline, the
output of a command piped into another command, the output of which,
in turn, is piped into a further command... and with the final output
redirected into a file.

If you've not had the pleasure of *implementing* a pipeline of
commands then that joy awaits us later on.  Probably more than once
(because we are/should be committed).

However, what this pipeline (and its minimalist variant friend, the
:ref:`simple command <shell simple command>`, above) overlooks is that
the shell is manipulating a secondary characteristic of Unix commands
one we need to be in control of.

By and large, when we construct a pipeline, in particular, or even a
simple command we, the user, are looking for some side-effect of the
*output* of that command.  The pipeline is, well, can be,
:underbold:`a`\ ffected by the exit status of any component of the
pipeline but that's not the :underbold:`e`\ ffect we're looking for.
We want the output stream of one command to be filtered by the next
and so on but we are *agnostic* to the command status along the way.

The shell, however, is agnostic to the output and predicates success
or failure of the pipeline on the command status alone -- well, the
command status of the last component of the pipeline -- *and* only if
you ask it to.

That is to say that:

.. code-block:: bash

   something | grep foo

fails, not because there was no output but because :program:`grep`
exits non-zero if it cannot match the regular expression (:samp:`foo`)
in its input stream.

Importantly, the pipeline succeeds if :program:`grep` does match
:samp:`foo` even if ``something`` crashed and burned spewing errors
left right and center.  So long as it managed to splutter :samp:`foo`,
somehow, before it died, then :program:`grep` is happy and therefore
the pipeline is happy.

The canonical example is to have everything fail except the final
component of the pipeline:

..  code-block:: bash

   false | false | false | true
   echo $?
   0

is all good.  :lname:`Bash`'s ``PIPESTATUS`` variable is a little more
honest:

..  code-block:: bash

   false | false | false | true
   echo ${PIPESTATUS[*]}
   1 1 1 0


If the command output vs. exit status is not a familiar distinction
then 1) we're not going to be best friends and 2) try putting:

.. code-block:: bash

   set -e

at the top of your script and sit back and watch the fireworks.  **Not
in production**, though.  That might be bad, fix your script first.
(In fact, try ``set -eu`` and patch up the mess.)

In most programming languages, when you invoke a command or function
call you pass some arguments and you expect a result.  With the shell
we do get a result, an exit status, albeit commonly overlooked.  We're
not going to be able to overlook it with one particularly good example
in :ref:`if <shell-if>`, below.

All these commands, and, rather consistently, the builtins and
user-defined functions, return a status with zero indicating success
and any other number being a command-specific failure.  (There is a
set of common exit statuses relating to whether the command was killed
by a signal but either way the result is just a simple 8-bit number.)

Pipelines have the same problem as IO redirection, though, they are
quite obviously *inline* and infix again.

We need to put our thinking caps on.  Not our *sleeping* caps, those
nodding off at the back, our thinking caps.  How do we handle inline
operators?

.. _shell-list:

Lists
-----

Lists, here in :lname:`Bash` at least, are pipelines separated by a
subtle combination of statement terminators and logical operands.

For logical operands, :lname:`Bash` uses ``&&`` and ``||`` although I
personally prefer :lname:`Perl`'s ``and`` and ``or`` -- which,
coincidentally, match :lname:`Scheme`'s ``and`` and ``or`` -- but also
free up ``&&`` and ``||`` for other uses.

``;`` terminates a statement/pipeline as does a newline.  I'm not so
keen on ``;`` as I don't use it anywhere other than mandated syntax
(in ``if`` or ``while`` etc.) or one-liners.

*Bah!* I do a lot of one-liners interactively, usually to finesse some
complicated filter whereon I then I reuse it with ``$(!!)``:

.. code-block:: bash

   ...fiddles...
   ...more fiddling...
   ...perfecto!...
   for x in $(!!) ; do thing with $x ; done

So maybe it's a thing.

``&`` is a weird, cross-over, end-of-statement marker and signal to
run the pipeline in the background.  Putting stuff in the background
is something, I think, people are fairly used to:

.. code-block:: bash

   sleep 10 &

which is a slightly pointless example but easily recognisable as
putting the command "in the background" (whatever that means).

``&`` is probably less used as a statement separator because things
can get a bit wild:

.. code-block:: bash

   for x in {1..10} ; do sleep $x & done

.. sidebox:: I have used this form in anger, albeit carefully modified
             as the operating system couldn't handle a couple of
             hundred shell scripts being kicked off simultaneously (I
             know, *I know!*) so I had to figure some means of doing
             rate limiting, in the shell.

	     Fun times.

Notice I have ``&`` instead of ``;`` before the ``done`` keyword.  The
shell will immediately kick off ten background processes.  Hitting
:kbd:`RETURN` a few times over the next ten seconds should get a
staggered notification that ten ``sleep $x``\ s have completed.

Back to our syntax considerations.  The logical operators are clearly
infix and the statement terminators are some strange infix or postfix
operation.

.. _`compound command`:

Compound Commands
-----------------

Compound commands are interesting because several of them operate on
:ref:`shell-list` which are built from :ref:`shell-pipeline` which are
built from :ref:`shell command` which are built from, er, compound
commands.  I'm pretty sure I've done an ``if case ...`` combo but the
therapy is helping a lot.

Let's take a look at them.

Subshells
^^^^^^^^^

I use subshells quite a lot but I think I largely use them so I can
``cd`` somewhere without affecting the current shell.  Even better
when backgrounded:

.. code-block:: bash

   for x in ... ; do
       (
	   cd some/where

	   mess with the environment

	   do some thing with $x
       ) &
   done
   wait

As we know -- or will know if we don't -- every command we run is
initially in a subshell because we have ``fork``\ ed and are about to
``exec``.  So is ``( ... )`` syntactic sugar for ``fork`` and run this
block of code?

You can use this as a hint that subshells are still on the ToDo list!

.. _`group command`:

Group Command
^^^^^^^^^^^^^

I'm scratching my brain here but I can't think of anywhere where I've
used ``{ ... }`` other than as a function body -- and there to such an
extent that I think I've only once written a function that *didn't*
use ``{ ... }``.

*shrugs* I don't see them as having a useful purpose in a programming
language (which you expect to have normal lexical structure).

Let Expression
^^^^^^^^^^^^^^

I have to assume that ``(( ... ))`` is only meant to be used in an
``if`` or ``while`` conditional expression as it explicitly returns a
non-zero status if the arithmetic result is zero.  So that's of no use
whatsoever in general flow with any kind of error handling (``set -e``
or ``trap ... ERR``).

If I want to do sums I use :ref:`arithmetic expansion`.

Conditional Expression
^^^^^^^^^^^^^^^^^^^^^^

Hopefully most people use ``[[ ... ]]`` rather than the anachronistic
``[ ... ]`` which, is a synonym for :manpage:`test(1)` and, depending
on the operating system, has some weird rules on the number of
arguments affecting how it behaves.  Yep, not what they are but the
*number* of arguments.  Just use ``[[ ... ]]``.

``[[`` does have a heap of command-specific operators including ``&&``
and ``||`` leaving the possibility of:

.. code-block:: bash

   [[ $a || $b ]] || [[ $c || $d ]]

where the middle ``||`` is managing pipelines and the outer ``||``\ s
are managing conditional expressions.

It's inside ``[[`` that we get regular expression matching (as well as
"regular" :ref:`shell pattern matching`).

There's a lot of behaviour loaded in ``[[`` that feels like it's
bundled in because that's the only place it could fit -- or ``[[`` was
designed to be extended arbitrarily.

Certainly regular expressions are just normal function calls in other
programming languages and you feel that much of the rest of it should
be as well.

For
^^^

There's two variants of ``for``, the common iterator, ``for x in ...``
and the :lname:`C`-like ``for (init; condition; step) ...``.

The former is used all the time.  People *like* iterating over things
and programmers get quite angry when they can't.  The latter, I don't
think I've used in a shell.  I must have...surely?

Select
^^^^^^

``select`` is a peculiar beastie.  I don't use it.  Maybe it's more
useful than I think.  Who wants to interact with *users* anyway?
They'll only type the wrong thing.

.. _shell-case:

Case
^^^^

I use ``case`` a lot as my GoTo means for doing conditional
:ref:`shell pattern matching`:

.. code-block:: bash

   HOSTNAME=$(uname -n)
   case "${HOSTNAME}" in
       '') echo "no hostname?" ;;
       *.*) ;;
       *) echo "need a FQDN!" ;;
   esac

Pattern matching is great!

.. _shell-if:

If
^^

We'll take a moment with ``if`` as it illustrates something quite
ingenious about the shell.  We're back to this exit status business.

The basic syntax is:

.. parsed-literal::

   if *list* ; then *list* ; [ else *list* ; ] fi

(I've skipped the ``elif`` bits.)

You'll probably have called ``if`` two ways:

.. code-block:: bash

   if [[ ... ]] ; then ... ; fi

   if cmd args ; then ... ; fi

The first we always look at as a test, like in most languages, ``if`` is:

.. parsed-literal::

   if *condition* then *consequent* else *alternative*

So ``if [[ ... ]] ; then ...`` looks like the regular programming
language version.  Except it's not, it is exactly the other form of
``if``:

.. code-block:: bash

   if cmd args ; then ... ; fi

because ``[[ ... ]]`` is a builtin *command* which returns a status
code of 0 or 1.  Which brings us neatly back round to the exit status.

``if`` will run the *condition* as a command and irrespective of the
output or other side-effects will determine the truthiness (stop me if
I'm getting too technical) based on the exit status of the command
(technically, the exit status of the *condition* :ref:`list
<shell-list>`).

That ``if`` is conditional on the exit status of the command is also
evident when it is masked by the syntactic sugar of :ref:`command
substitution <command substitution>`:

.. code-block:: bash

   if output=$(cmd args) ; then ... ; fi



Trapped If
""""""""""

Of interest is that ``if`` will not trigger an error trap.  That's
obviously what you want, at least I think it is obvious:

.. code-block:: bash

   if something | grep foo ; then
       ...
   fi

You don't want your shell to exit (``set -e``) if :program:`grep`
doesn't get a match.  That's the whole point of it being in a
conditional test.  Compare that with:


.. code-block:: bash

   # helpful debug!
   something | grep foo

   if something | grep foo ; then
       ...
   fi

where you'll not reach the ``if`` statement because the failure to
match :samp:`foo` will cause :program:`grep` to exit non-zero, ``set
-e`` will then exit your script and you'll be none-the-wiser having
seen nothing printed out.

Similarly, ``while`` and the logical operators ``&&`` and ``||`` also
mask any error trap.

.. _shell-while:

While
^^^^^

Interestingly, I've done OK without having ``while`` in my arsenal.
As we know (cue recovered memories from computer science classes)
iterative control flow operators (eg., ``while``) can be re-written as
recursive function calls (and *vice versa*) and :lname:`Scheme` has a
big thing about being able to do tail-call recursion so, uh, that's
what you do.

Like many things ``while`` is syntactic sugar for what's really
happening underneath the hood.  It still needs writing, though!

.. _co-process:

Co-processes
^^^^^^^^^^^^

These are relatively new to :lname:`Bash` though they're been in other
shells, eg. :lname:`Ksh`.

I've not used them.  Dunno.

In a programming language we'd simply have several file descriptors
floating about we can read from or write to at our leisure.  No need
for specific co-processes.

Function Definitions
^^^^^^^^^^^^^^^^^^^^

A given.

Technically, the body of a shell function is a :ref:`compound command
<compound command>` hence why most function bodies look like ``{
... }``, the :ref:`group command <group command>`, but it could be a
single :ref:`if <shell-if>` or :ref:`case <shell-case>` statement.

I'm not sure I've ever used the IO redirection for a shell function.

One weirdness, in :lname:`Ksh`, at least, regards whether you declare
the function with the keyword ``function``:

.. code-block:: ksh

   foo() { ... }

   function bar { ... }

and therefore whether a trap on ``EXIT`` is executed.

Expansion
=========

Slightly out of order from the man page but expansion is easily the
shell's most distinguishing feature and, likely therefore, its most
misunderstood.

The real bugbears are :ref:`brace expansion <brace expansion>`,
:ref:`word splitting <word splitting>` and :ref:`pathname expansion
<shell pathname expansion>` (and parameter/array expansion) because
they *change the number of words* in the command expression.

That's *bonkers*!  Are there any other languages which actively change
the number of words they are processing?  (There must be, I can't
think of any.)  It defies any form of programmatic rigour when you
can't determine the arguments you have to hand:

.. code-block:: bash

   ${TAR} ${TAR_FLAGS}

Is that potentially erroneous because we did or did not pass the
:program:`tar` *archive* (and optional *files*) in ``${TAR_FLAGS}`` or
are they passed in ``${TAR_FLAGS}`` and all is well.

Is either variable even set?

I have written code like:

.. code-block:: bash

   ${DEBUG} cmd args

.. sidebox:: Even more fun, you can set ``DEBUG`` to ``#`` and the
             command is commented out.

	     The possibilities are legion.

where ``${DEBUG}`` can optionally be set in the environment and is
therefore either nothing, in which case ``${DEBUG} cmd args`` is
expanded to just ``cmd args`` and is run as you would expect, or it is
set to, say, ``echo``, in which case the expansion is ``echo cmd
args`` and ``cmd args`` is echoed to *stdout* (and not run).

Programmatically, then, shell commands can be worryingly
non-deterministic -- and we haven't even started on what ``cmd`` is
anyway, a shell function, a shell builtin, an executable expected to
be found on your :envvar:`PATH`?

Expansion isn't quite performed all at once, brace, tilde, parameter,
arithmetic, command (and optionally, process) substitution are
performed in that order, left-to-right and then word splitting and
pathname expansion are applied before final quote removal.

There's a lot going on!

.. _`brace expansion`:

Brace Expansion
---------------

Brace expansion comes in two forms: a comma variant and a sequence variant.

.. code-block:: bash

   ls /usr/{bin,lib}

   echo {01..16}

The former saves us writing a loop and the latter saves us calling
:program:`seq` (not available on all platforms) -- although brace
expansion does implicitly include the leading-zeroes formatting, see
the ``-w`` flag to :program:`seq`).

Is this syntax something we *need*, though?  I'm not sure.  There's
clearly a function returning a list of (formatted) strings which we
could just call, very much like :program:`seq`:

.. code-block:: bash

   for x in {01..16} ; do ...

   for x in $(seq -w 1 16) ; do ...

We can probably live without this syntax.

Tilde Expansion
---------------

.. sidebox:: |copy| The Chuckle Brothers

``~me``, ``~you``

Of interest is that the shell also checks not just simple variable
assignments, ``HERE=~me`` but also after ``:``\ s in variable
assignments so that ``EVERYWHERE=~me:~you`` does the right thing.

It's nice enough though I fancy I've only really used it
interactively.  I'm happy to be manipulating paths in a more
long-winded fashion so maybe I've happy enough to make an extra call
where I thought it was required:

.. code-block:: bash

   path_prepend EVERYWHERE $(tilde_expand ~me)

although, as we know tilde expansion is the ``pw_dir`` field from a
:manpage:`getpwnam(3)` call, then in some putative language it might
look more like:

.. code-block:: sh

   me_dir = getpwnam ("me").pw_dir
   path_prepend EVERYWHERE me_dir

which is clearly more "work" but suggests we've more (systems
programming) access to the data sources.  We need to handle failures,
of course -- we might need to have an existential crisis if ``me``
doesn't exist, for example.

So I'm thinking that the syntax for tilde expansion isn't required.

Parameter Expansion
-------------------

I use parameter expansion *a lot*.  I particularly use it for
manipulating pathnames where :program:`dirname` and
:program:`basename` can be replaced with ``${FOO%/*}`` and
``${FOO##*/}`` respectively.  Who doesn't want to do array pattern
substitution, ``${array[*]/%\/bin/\/lib}``?  Who, *who*?

Others might think this mix of terse syntax and pattern-matching gives
:lname:`Perl` a good name.

I can understand that, even when you point at ``%/*`` and say it's two
parts, a remove-shortest-match-at-the-end, ``%``, for the pattern
``/*`` (which is a loaded concept in its own right), it still
befuddles non-shell programmers.

It's hook has probably been slung -- which is a good thing, as I don't
fancy trying to replicate any of that terseness.  We'll just have to
plod along manipulating our strings bit by bit like everyone else.

.. _`command substitution`:

Command Substitution
--------------------

I use command substitution, ``$( ... )``, all the time as well.  I'm
usually collecting some fact from a command, often a pipeline:

.. code-block:: bash

   HOSTNAME=$(uname -n)

   CIDR=$(ip addr show dev lo | awk '$1 ~ /^inet$/ {print $2}')

(no second guessing on the loopback device's IPv4 address -- although
I'm assuming there's only one, here!)

Mechanically, of course, the command we run knows nothing about us and
our attempts to capture its output.  It'll be printing to its
*stdout*, nothing more, nothing less.  The trick is, of course, to:

* create a temporary file
* redirect the command's *stdout* to that file
* run the command (*duh!*)
* read the contents of the temporary file
* delete the temporary file

Wrap all that up in the syntactic sugar of ``$( ... )`` and we're
done.  Very neat!

A requirement, surely!

That said, command expansion is one of the most guilty parties for
introducing unexpected whitespace (whitespace as the lesser of such
evils).  Were we to be blessed with the directory ``My Documents`` in
the current directory:

.. code-block:: bash
		
   ls $(ls)

results in:

.. code-block:: bash

   ls: My: No such file or directory
   ls: Documents: No such file or directory

Why?  Performing the expansion by hand we see:

.. code-block:: bash

   ls My Documents

and we probably wanted:

.. code-block:: bash

   ls "My Documents"

There is no general solution to unexpected whitespace, newlines,
etc. introduced by command expansion!  The worst of which will be a
shell-ish `Little Bobby Tables`_

.. _`arithmetic expansion`:

Arithmetic Expansion
--------------------

.. attention:: Please, no more :program:`expr`!

We can do sums in the shell:

.. code-block:: bash

   echo $(( 1 + 1 ))

Performs the arithmetic and replaces the expression with:

.. code-block:: bash

   echo 2

Usefully, during arithmetic expansion you don't need to perform
parameter expansion, that is, you can use variables without the ``$``
sigil:

.. code-block:: bash

   p=2
   echo $(( $p + 2 )) $(( p + 3 ))

will become:

.. code-block:: bash

   echo 4 5

Notice, however, that parameter expansion can be your undoing:

.. code-block:: bash

   echo $(( p++ ))

will become:

.. code-block:: bash

 echo 2

and ``p`` will now have the value 3.  However, were we to have typed:

.. code-block:: bash

   echo $(( $p++ ))

parameter expansion will have gotten there first:

.. code-block:: bash

   echo $(( 2++ ))

which is, obviously(?), an error.

Arithmetic expansion occurs in array index calculations such as
``${array[base+offset]}`` and ``${array[i++]}``.

Arithmetic is assumed, I suppose, for a programming language, though
several of the :lname:`C`-like operators will be hived off as
functions if available at all (think bitwise operators).

However, one thing to note is that the :lname:`C`-like operators are,
largely, infix binary operators, that is, they take two arguments, one
before the operator and one after:

.. code-block:: bash

   1 + 2

Everyone does that, right?  No, not really.  They're in the camp of
yet another (set of) infix operator(s).

Process Substitution
--------------------

On systems supporting named pipes we can substitute a filename for a
dynamic stream:

.. code-block:: bash

   diff expected-result <(cmd args)

results in something like:

.. code-block:: bash

   diff expected-result /dev/fd/M

where ``/dev/fd/M`` is the filename for the file descriptor
representing the output of the pipeline from the invocation of ``cmd
args``.

This is really useful for commands like :program:`diff` which only
operate on files.

Another use case is where you have a requirement to iterate over the
output of a command and to modify a local variable:

.. code-block:: bash

   cmd args | while read line ; do 
       local_var=$(process ${line})
   done

doesn't work because the ``while`` loop, as part of a command
pipeline, is in a subshell so modifications to ``local_var`` have no
effect in us, the parent shell, where we want them.  You need to
rewrite this to, say:

.. code-block:: bash

   while read line ; do 
       local_var=$(process ${line})
   done < <(cmd args)

which will be expanded to something like:

.. code-block:: bash

   while read line ; do 
       local_var=$(process ${line})
   done < /dev/fd/M

It's useful functionality for the shell where we can't hold a file
descriptor open to a sub-process (although see :ref:`co-process
<co-process>`, above) in the latter case.

In the former case does it justify a special syntax?  Maybe.  It is, I
think, more or less a function call, something along the lines of:

.. code-block:: bash

   diff expected-result $(named-pipe cmd args)

.. _`word splitting`:

Word Splitting
--------------

This is where the problems usually start!

Quoth :manpage:`bash(1)`:

    The shell scans the results of parameter expansion, command
    substitution, and arithmetic expansion that did not occur within
    double quotes for word splitting.

The shell splits the result of the expansion based on the contents of
the ``IFS`` variable (usually the ASCII characters ``SPACE``, ``TAB``
and ``NEWLINE``).

.. note:: This word splitting isn't a rigorous *split* on every
          occurrence of a delimiter in ``IFS`` in that a sequence of
          ``IFS`` characters only generate a single split.

	  Naturally, it's more complicated than that.  RTFM!

So, casual use of space-containing variables:

.. code-block:: bash

   dir="My Documents"
   ls ${dir}

expands to:

.. code-block:: bash

   ls My Documents

and fails because word splitting thinks you've passed two separate
arguments, ``My`` and ``Documents`` to the command, just like we we
might pass two arguments, ``-a`` and ``-l`` to ``ls`` if we typed
``ls -a -l``.  We should have written:

.. code-block:: bash

   ls "${dir}"

which expands to:

.. code-block:: bash

   ls "My Documents"

and works as expected.

A general rule of thumb is to double quote everything unless otherwise
advised.

This whole word splitting thing is a bit of a nightmare.  If we're
going to have complex data structures then you feel that these
whitespace-including entities should be being passed as proper
parameters and that:

.. code-block:: bash

   dir="My Documents"
   ls ${dir}

should work as expected without word splitting.

.. sidebox:: I hate the Romans as much as anybody.

I'm not a splitter.

.. _`shell pathname expansion`:

Pathname Expansion
------------------

Pathname expansion should be a requirement but, it transpires, it's
going to be tricky for some other reasons that we'll get onto in due
course.  In the meanwhile, pattern matching must be one of the finest
examples of abstraction and utility in computing!

Famously, or not:

.. code-block:: bash

   ls *

does not pass ``*`` to :program:`ls` (most of the time).  Rather, the
shell has been looking for *meta-characters*, in particular, ``*``,
``?`` and ``[``.  In :lname:`Bash` the ``extglob`` shell option adds
some more matching operators (some of which are available by default
in other shells).

When it identifies a meta-character in a word then the whole word is
treated as a pattern and filename :ref:`shell pattern matching`, aka
*globbing*, begins.  Globbing_ began life at the very beginning of
Unix as a standalone program, :program:`glob` (authored by one
:ref-author:`Dennis Ritchie`), so it's "got some previous" but is now
more readily available as a library call, :manpage:`glob(3)`.  I
*think* :lname:`Bash` still rolls its own version, it certainly has
the code in a subdirectory (:file:`.../lib/glob`).

More importantly to us are the *results* of pathname expansion.  We
get back a list of filenames.  I would suggest that we subsequently
preserve that list and pass it around as you might a list in a regular
programming language.

When we finally get around to running a command (remind me, that's why
we're here, right?) we can expand the list, preserving whitespace
quite happily.

Sorted glob
^^^^^^^^^^^

There's a more general irritation with pathname expansion: you can't
*sort* the results based on attributes of the files your pattern
matches or, indeed, any other arbitrary sorting scheme.  The shell
appears to do a lexicographical sort on its results (possibly
:manpage:`locale(1)`-specific).

There are any number of situations where a list of files could be
bettered by being sorted based on modification date or size or
qualified by ownership for which you have to break out to another
command (and suffer the problems of managing the quoting correctly) to
gather the results back.  Or you rewrite everything in another
programming language...

There's room here, I think, for the results of :manpage:`glob(3)` (or
whatever) to be passed to something that can sort and/or filter the
results based on rules of its own choosing.

Hint: sorted.

.. _`shell pattern matching`:

Pattern Matching
^^^^^^^^^^^^^^^^

Pattern matching is a bit like regular expression matching (if ``*``
and ``?`` became ``.*`` and ``.?``) until all the subtleties kick in.
An obvious one is that ``ls *`` will not report any *dot files*
(unless you explicitly match the leading dot with ``.*``, or the
``dotglob`` shell option is set and even then you must match ``.`` and
``..`` explicitly).

Luckily for us, someone has written :manpage:`glob(3)` and we can
claim uniformity with "everyone else" (noting that many others will be
rolling their own variation, 1standards_, eh?).  We could go there but
it's certainly not necessary right now.

Quote Removal
-------------

If we don't do :ref:`word splitting` we don't need to do any quote
removal.  That's the plan!

Quoting
=======

I'm hoping that (what feels like) the normal use for quoting things,
to avoid :ref:`word splitting`, is nullified because we're not going
to do any word splitting.

However, it is convenient to build strings using variables:

.. code-block:: bash

   echo "PATH=$PATH"

which would require something like the templating mechanism I hinted
at for :ref:`here-documents <shell-here-document>`.

Parameters
==========

Parameters being variously positional parameters, special parameters
and variables.

First though some parameter attributes.

Parameter Attributes
--------------------

Variables are, by default, shared between the main program and shell
functions.  You can restrict the scope of a variable to be *local* to
the function it is declared in.  I suppose, technically, the
:ref:`group command <group command>` it is declared in (not sure).

We previously mentioned that some variables are tagged for *export*
and I'm thinking about them in terms of variables with *dynamic*
scope, whose values come and go based on the run-time path the code
takes.

You can also mark a variable as *readonly*.

A final classification is that of being an *alias*.  I keep thinking
that having synonyms would be handy but then keep being reminded that
even in :lname:`Bash` the suggestion is to use a function instead.
Your synonym function simply calls the aliased function with all of
its arguments.

Shell Variables
---------------

(Of interest to us with design in mind!)

``$!``

   The PID of the last backgound(ed) command.

   One shot or you've missed it.  I envisage the ability to go back
   and query interesting things about your child processes at any time
   although it is possible, like the backgrounded `sleep``\ s above,
   there's no easy way to distinguish between them.

``$?``

   In :lname:`Bash` it is the exit status of the most recently
   executed *foreground* pipeline.

   I've emphasised foreground, there, as I confess it hadn't occurred
   to me.  It's only really useful if you're not running any error
   handling (``set -e`` or ``trap ... ERR``) otherwise the value will
   be ``0`` or your script has errored.

   If you run a bunch of processes in the background (remembering
   their PIDs with ``$!``) then ``wait`` for each PID in turn then
   each ``wait`` (being run as a foreground command) returns as its
   own exit status the exit status of the PID it was waiting on.  A
   little bit of digital legerdemain.

   Being able to reference a (child) process' status is a useful
   thing.  There's a not unreasonable argument that says being able to
   access its status at any time is a good thing.

``PWD``

   ``PWD`` is the current working directory as set by ``cd`` --
   **not** the result of :manpage:`getcwd(3)`.

   Here, you maintaining the logical path in your rat's nest of
   symlinks in the underlying filesystem.

``SECONDS`` (and ``RANDOM``)

   I like ``SECONDS`` and use it to report the elapsed time of a
   script (genius!) but think about what it is.  When you reference it
   you get back a volatile value.  It is what we might describe as a
   *computed* variable in the sense that when it is queried some
   function is called and the value returned by the function is the
   value of the variable.

Signals and traps
=================

Signals in the shell are as complicated as anywhere else compounded by
the "rules" for :ref:`job control <shell job control>`.

By and large, I avoid getting involved as it's hard and prone to
hard-to-repeat errors.  Which is a shame as I'm now trying to write
shell which needs to deal with signals.

In addition to regular Unix signals there are a few fake signals:
``DEBUG``, ``RETURN``, ``EXIT`` and ``ERR``.  I only use ``EXIT`` and
``ERR`` and I use them all the time.

A trap on ``EXIT`` is executed before the shell terminates.  Quite
when is less clear but it seems close enough to the end to do any
clearing up.  If you were of a sort to create a temporary directory
and do all your processing in there then an ``EXIT`` handler can
easily ``rm -rf`` the temporary data.

A trap on ``ERR`` is my GoTo replacement for ``set -e``.  The problem
with ``set -e`` is that your script just dies.  I'd like to know a
little more so I tend to have something like:

.. code-block:: bash

   handle_ERR ()
   {
       echo "ERROR at line $1: exit ($2)" >&2
       exit $2
   }

   trap 'handle_ERR $LINENO $?' ERR

.. sidebox:: Notice the single quoting in the ``trap`` statement so
             that ``$LINENO`` and ``$?`` pick up the correct values at
             the time the expression is evaluated.  Not now, when we
             are declaring the trap!

which gives me a few more clues.

It's not foolproof as the line number is often reported as the end of
a :ref:`compound command <compound command>` which could be anything
within.

Until recently, functions and subshells did not inherit this trap
which was spectacularly annoying.

So, if there's one thing to do, we must be able to handle errors
decently.

.. _`shell job control`:

Job Control
===========

Job control is the idea of selectively stopping and resuming processes
that you have backgrounded.  A job, here, means a pipeline.  When a
pipeline is launched all the processes in the pipeline share a
*process group*.  If the pipeline/job is in the foreground then that
process group is associated with the terminal such that any keyboard
signals raised go to that process group -- and **not** to the shell
nor any of the backgrounded or stopped jobs.

You can't have a foreground *job* in the sense that anything running
in the foreground is receiving input from the controlling terminal and
the shell (and any backgrounded jobs) are not.  If the shell isn't
getting any input then it's not controlling anything, let alone a job.

You can't, therefore, have the shell do anything until the foreground
command completes or is stopped.  The shell's very purpose in life is
to hang about waiting for its children, in this case the foreground
process, to complete/stop, so it will then re-arrange signals and the
terminal and will continue doing shell-like things.

.. sidebox:: Technically, not always :kbd:`Ctrl-C` but whatever your
             terminal thinks is the ``VINTR`` character and only if
             ``ISIG`` is set.

	     But you know your terminals, right?  (I don't but
	     :manpage:`termios(3)` suggests that's correct.  I did say
	     that dealing with the terminal was hard.)

When you have a foreground pipeline running and you hit :kbd:`Ctrl-C`
(or other signal-raising keystroke) the ``SIGINT`` is sent to the
*process group* associated with the terminal and the processes within
that process group will act as they see fit.

The shell, for example, has a ``SIGINT`` handler -- primarily to
interrupt ``wait`` -- but it is functionally ignored.  Thus, when the
shell itself is "foreground", :kbd:`Ctrl-C` doesn't do much.

If you did run a pipeline in the foreground you can raise a "terminal
stop" signal, ``SIGTSTP``, slightly confusingly called the terminal
suspend character, usually, :kbd:`Ctrl-Z`.  Assuming it is not ignored
(a shell usually ignores it!) then the default signal disposition
means the pipeline will stop, the shell is signalled that a child
process has changed state (``SIGCHLD``) and can handle the pipeline as
a job.

Note that the pipeline/job you just stopped is still stopped.  In most
shells you can immediately ``bg`` the pipeline/job to let it carry on
processing.

Foregrounding and backgrounding involves careful manipulation of
process groups, signals and the state of the controlling terminal.
It's quite complicated but, to the relief of all, there's a handy
description of most requirements in the :manpage:`info(1)` pages for
:program:`libc` under the menu item ``Job Control`` or try the
equivalent `online Job Control`_ web pages.

Much of the complexity of job control is for interactive sessions.
Non-interactive shell scripts can still background jobs and the
signalling and terminal management differ.


.. include:: ../commit.rst

