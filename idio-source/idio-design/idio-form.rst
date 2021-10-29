.. include:: ../global.rst

.. _`Idio Form`:

*******************
:lname:`Idio` Form
*******************

.. aside::

   And by raged I mean I have sighed, wearily.

I have a strong desire to make :lname:`Idio` be strict.  I have
*raged* over shell scripts that do not handle errors.

.. aside::

   Who uses ``set -e`` in an interactive shell?

To be fair, it's not the easiest thing to get to grips with as errors
occur in the shell *all the time*.  Even TAB-completion can generate
errors which, if you had had ``errexit`` enabled, is a touch annoying.

Shell *scripts* which run without error handling are at chronic risk
of blithely crashing on through despite earlier commands failing.
:socrates:`What could possibly go wrong?` This is made far worse when
the screen is clogged with command output with errors and warnings
lost in the noise.

Even something as simple as ``ls *.tar`` can be a life-saver
(script-saver?) as if the expected files don't exist then Pathname
Expansion will have failed passing the literal text ``*.tar`` to
:program:`ls` which will, unsurprisingly, be unable to find such a
file and *fail*.

There's your canary in the coal mine, right there.  :program:`ls` not
only voiced a complaint: ``ls: cannot access '*.tar': No such file or
directory`` but also exited non-zero.  You could have stopped the
script right there, almost for free, and saved whatever was coming
next from crashing and burning.

What's not to like?

Strictly Scripting
==================

.. aside::

   read: be onerously demanding and heinously aggrieving

I have an idea that all technically correct rules and behaviours
should be enabled by default.

This then requires a clear and unambiguous statement in the script
that the rule or behaviour is being disabled.  Something like:

.. code-block:: idio

   suppress exit-on-error

.. aside::

   Not that people should listen to me but at least they will have to
   make an effort.

Of course, regular users wouldn't want to go suppressing
``exit-on-error`` as it defeats the very thing I've been raging about.

However, there are several circumstances when we don't want full-on
``exit-on-error`` behaviour.  Let's take a look at some :lname:`Bash`
casework.

For these examples we'll modify our prompt to include the
:lname:`Bash` environment variable :envvar:`SHLVL` and a small indent
so we know where we are and you can check :var:`$-` for current shell
settings -- albeit that it doesn't report on :samp:`set -o
{long-form}` options.

.. _`set -e`:

set -e
------

Exit on error, right?  Except...

    Subshells spawned to execute command substitutions inherit the
    value of the -e option from the parent shell.  When not in posix
    mode, bash clears the -e option in such subshells.

    --- :manpage:`bash(1)`

Hmm, I don't think I've *ever* run ``bash --posix`` (or typed ``set -o
posix``).  We're not feeling particularly beholden to POSIX's views on
shells so we can ignore that and note that Command Substitution
(alone!) gets the special treatment:

.. code-block:: console

   [ 2]$ set -e
   [ 2]$ echo $(echo hello ; false ; echo world;)
   hello world
   [ 2]$ 

whereas for Process Substitution:

.. code-block:: console

   [ 2]$ cat <(echo hello ; false ; echo world;)
   hello
   [ 2]$ 

but notice that whilst ``false`` failed (hopefully!) and the rest of
the commands were not run the overall "asynchronous process" did not
result in a failure being propagated to :program:`bash` even though
``errexit`` is in effect in shell #2.  You feel there's a sort of
``exit-0-on-error`` mechanism being used in the Process Substitution
part.

Compare that with a regular subshell (for which we use an extra
:program:`bash` to demonstrate):

.. code-block:: console

   [ 2]$ bash
   [  3]$ set -e
   [  3]$ (echo hello ; false ; echo world;)
   hello
   [1]$ echo $?
   1
   [1]$

*Whoa!* All the way back out to shell #1 which reports that shell #2
exited with 1.

Looking more closely, shell #3 has ``errexit`` set and we ran a
subshell which inherits that value.  The subshell sees ``false`` fail
and so exits non-zero itself.  Shell #3 sees the subshell fail and
because it has ``errexit`` set will fail itself.

Of course, we forgot that shell #2 also had ``errexit`` set, because
we were testing Command and Process Substitution, and so it exited
non-zero because shell #3 exited non-zero.

Finally, shell #1 brought a halt to our toppling dominoes because
no-one enables ``errexit`` in an interactive shell because this is
what happens and no-one wants to log in again.

.. aside::

   *Don't we?*  Otherwise, **get off my lawn!**

Shell *scripts* are a different matter and we *do* want them to fail.

One interesting thing to note from both the Process Substitution and
subshell examples is that we do get ``hello\n`` from them before they
exit.  In other words we haven't had any weird *stdio*-style
buffering.

The details are in, for Linux, :manpage:`pipe(7)` where we see that
whilst a *pipe* (or FIFO) can buffer something like 65,536 bytes
(technically, 16 pages) the individual *writes* to the pipe will be
atomic if they are :var:`PIPE_BUF` bytes or less (for example, 4096 on
Linux but 512 on POSIX).

pipefail
--------

I don't normally run with ``pipefail`` enabled.  In the first instance
because I didn't know it was there and then because some reasonable
tasks become burdensome.

For example, I quite often run some fiendishly complex filter piping
the result into, say, ``head -1`` as I only want the first line.

However, we are at risk of :program:`head` stopping reading its input
pipe before the (fiendishly complex filter on the) left hand side has
finished writing.  We are at risk of the ``SIGPIPE``/``EPIPE`` pincer
movement.

As it turns out, the *in-my-head* example doesn't work -- and for
reasons I don't understand:

.. code-block:: console

   [ 2]$ man bash | head -1
   BASH(1)                     General Commands Manual                    BASH(1)
   [ 2]$ echo ${PIPESTATUS[*]}
   0 0
   [ 2]$ 

Hmm, no errors.  The :lname:`Bash` man page is nearly 400k bytes so
:program:`man` should block writing to the pipe and :program:`head`
should exit.  *Dunno.* Maybe :program:`man` does something funny
because it so often sees :envvar:`PAGER` fail when the user stops
reading the man page?

Moving swiftly on, let's try something more back to basics:

.. code-block:: console

   [ 2]$ (echo hello; sleep 1; echo world;) | head -1
   hello
   [ 2]$ echo ${PIPESTATUS[*]}
   141 0
   [ 2]$

Aha!  That's better.  The exit status, 141, is over 128 meaning the
cause was a signal and 141 - 128 is 13, aka SIGPIPE.

Now with added ``pipefail``:

.. code-block:: console

   [ 2]$ set -o pipefail
   [ 2]$ (echo hello; sleep 1; echo world;) | head -1
   hello
   [ 2]$ 

Erm....  :var:`PIPESTATUS` reports the SIGPIPE again, though.

Ah, wait a minute, the pipeline may well have returned a non-zero
status because of the SIGPIPE but we haven't told shell #2 to do
anything about that.  We need ``errexit`` *as well* as ``pipefail``:

.. code-block:: console

   [ 2]$ set -e
   [ 2]$ set -o pipefail
   [ 2]$ (echo hello; sleep 1; echo world;) | head -1
   hello
   [1]$ echo $?
   141
   [1]$

Top!  This time shell #1 reports that shell #2 passed on the SIGPIPE
exit status.

Observations
============

I don't like the :lname:`Bash` Command Substitution mechanism of
un-setting ``errexit``.  That feels wrong in some fundamental way.  If
something went wrong, processing should stop.

That's what happens with the :lname:`Bash` Process Substitution case
with a putative ``exit-0-on-error`` mechanism.  Something went wrong
so we stopped.

That *still* doesn't feel quite right.  *I* don't know that something
went wrong.  I am unaware that Process Substitution was unable to
complete its processing.  I think I ought to know.

Clearly, the nominal ``exit-on-error`` mechanism to too crude for
these "asynchronous" processes.  It feels like there should be another
kind of "trap" that we can hook onto.

Maybe the default behaviour is to ignore asynchronous process failure.
Maybe it should be to raise the standard ``exit-on-error`` (but at
least offering the opportunity to capture it separately).

Here's a (possibly) more illuminating example.  Not all systems have
GNU *tar* with its ``z`` option so I'd habitually separate the
processing myself:

.. code-block:: console

   $ gzcat file.tar.gz | tar xf -

In that example, if :program:`gzcat` fails we have some options to
handle it.  However, a little reworking of the above for Process
Substitution:

.. code-block:: console

   $ tar xf <(gzcat file.tar.gz)

and now, no error handling at all.  Suddenly life is a little harder.

.. include:: ../commit.rst

