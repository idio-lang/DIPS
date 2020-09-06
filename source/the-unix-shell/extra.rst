.. include:: ../global.rst
.. include:: <isonum.txt>

*************
Extra! Extra!
*************

The shell does quite a lot but is there anything else it could do?  We
can do what we like, we're designing and implementing it after all!

I'm an inveterate fiddler and there's plenty of things that would be
really handy though we should be careful to distinguish between things
that can simply be implemented in our programming language as an
add-on package and things which require a change to the core engine.

Changes in the core engine tend to have wide changes in the :lname:`C`
code base.  A new core type, for example, will need code to allocate
and garbage collect it, to construct, manage and destruct instances of
the type, something to manage type equality, something to print it and
something to create a hash value from it.  There are probably others.

There are plenty of programming language engine features that we might
be interested in.  Is this a real programming language if it doesn't
have a :abbr:`JIT (Just In Time)` compiler?  Threading (of any kind)?
But those aren't shell-ish features, we can pick those up elsewhere.

In no particular order, then.

.. rst-class:: center

---

A long time ago I stumbled over a bug in :lname:`Bash` (version 1 --
showing my age!) where a file descriptor was left open which, for some
reason, tripped up something else away away down the chain -- I
vaguely recall it was something to do with mail that fell over,
:manpage:`mail(1)`, maybe?  It took a while to figure out the culprit
was :lname:`Bash`.

Anyway, I pondered on the fact that I couldn't :manpage:`close(2)`
this file descriptor like I might be able to do in :lname:`Perl`.  How
frustrating.  (A frustration that has bugged me ever since.  Doubly
annoying!)

.. sidebox:: My colleagues took this to heart and hooked a
             :lname:`Perl` interpreter into :lname:`Bash` to talk to
             their :lname:`C++` management system with a glue
             interface using Lisp-y parenthesis to protect the
             :lname:`Perl`-esque input and ``Data::Dumper`` output.

	     Still in use today...

Until I discovered that I *could* write a ``close`` function that
really did :manpage:`close(2)` the errant file descriptor and all was
well.  I had discovered :lname:`Bash`'s loadable builtins mechanism.
I was a happy bunny.

The bug in :lname:`Bash` was fixed in the next release anyway.

C FFI
=====

I'm pretty keen to have a :lname:`C` :abbr:`FFI (Foreign Function
Interface)` so I can poke about and do *stuff*.  There's plenty of
opportunity to be talking about different things here so what I'm
describing is having :lname:`C` functions available as :lname:`Idio`
functions (modulo appropriate nuances).  So that means managing data
types including structures and unions as well as the literal calling
of functions.

Consider :ref:`Job Control` where we have to be able to call exotic
systems programming interfaces like :manpage:`setpgrp(2)` and
:manpage:`tcsetpgrp(3)` to do basic shell work.  I like programming in
:lname:`C` as much as the next guy (probably not true) but I'd rather
be writing code in a language that abstracts me from the nitty gritty
and let's me get on with the logic.  If a system call fails then raise
some kind of error, hopefully some kind of exception, such that it can
be handled by someone who has a bigger picture.  I just made a system
call which failed, how do I know if that means the program should
exit?  A shell is predicated on abstractions, like ``|``, which we
know are 1) chock full of systems calls and 2) any of which can fail.
No-one has stopped writing shell scripts because of that.

.. _`tcsetpgrp example`:

In our putative shell-like language we want to say:

.. code-block:: idio

 tcsetpgrp fd pgrp

where ``tcsetpgrp`` is an :lname:`Idio` function and ``fd`` and
``pgrp`` are :lname:`Idio` values and it will eventually work its way
through to a :lname:`C` function, something like:

.. code-block:: c

 ... idio_primitive_tcsetpgrp (... fd_arg, ... pgrp_arg)
 {
     int fd = <massage fd_arg into int>;
     pid_t pgrp = <massage pgrp arg into pid_t>;

     int ret = tcsetpgrp (fd, pgrp);

     if (-1 == ret) {
         idio_error_system_errno ("tcsetpgrp", ...);
     }

     return <massaged ret>;
 }

However, crafting those calls by hand is quite different to being able
to wave some automated mechanism at the problem and say, *figure it
out*.  

Those calls aren't rocket science and it is instructive to see how we
might manage more complex data structures and calls.  But it is
long-winded.

libffi
------

.. _`starter for ten`: https://en.wikipedia.org/wiki/University_Challenge

.. _libffi: https://sourceware.org/libffi/

On obvious named `starter for ten`_ in this work is
:ref-author:`Anthony Green`'s libffi_.  :lname:`libffi` forms a sort
of glue between compilation units or, indeed, between interpreted code
and compiled code.  The underlying problem is that compilers use an
architecture- and operating system-specific set of calling conventions
when laying out the arguments to function calls.  :lname:`libffi`
provides a high-level programming interface to these conventions.

It's not the end of the matter as :lname:`libffi` deals in :lname:`C`
arguments, not, say, :lname:`Idio` arguments so you need a layer of
abstraction above :lname:`libffi` that massages :lname:`Idio` numbers
into :lname:`C` ``int``\ s, say.  Part of *that* problem is that you
need to know how big your ``typedef``\ ed :lname:`C` type is.  Is your
``time_t`` four or eight bytes?  (Hint: that's not a 32- or 64-bit
question.)  How big is your ``int``, for that matter?

But, do I *really* envisage corralling the arguments for a :lname:`C`
function call on the fly?  No, not really.  That sounds like some
awkward typing and exactly the sort of laboured guff that automation
is supposed to help me with.

I think what I want is something to grovel around *somewhere* and
figure out what the :lname:`C` code would look like if I'd written my
code like the :ref:`tcsetpgrp example <tcsetpgrp example>`, above.  It
can then be compiled up and added as a linkable module (however that
works).

sb-grovel
---------

.. _SBCL: http://www.sbcl.org/

.. _sb-grovel: http://www.sbcl.org/manual/#sb_002dgrovel

.. _`The Groveller`: https://common-lisp.net/project/cffi/manual/html_node/The-Groveller.html

Steel Bank Commom Lisp (SBCL_) have `sb-grovel`_ to help generate
foreign function interfaces and there is a (possibly more portable)
`The Groveller`_ inspired by it.  The basic idea is that you compile
some :lname:`C` code and the groveller figures out the interface and
generates some :lname:`Lisp` for you to call.

Do I want some :lname:`Lisp`, though?  I think I want some :lname:`C`,
don't I?

DWARF
-----

.. _stabs: https://en.wikipedia.org/wiki/Stabs

.. _DWARF: http://www.dwarfstd.org/

Another "back in the day" recollection was a colleague chuntering away
about poking about in the stabs_ output from :program:`gcc`.  I wasn't
really following what he was on about (or why) -- and I don't really
follow what he chunters about today, either, but that's OK, I think,
for both of us.  More importantly, poking about in stabs has stuck
with me.  It might be time...

Except stabs has been superseded by DWARF_ (a pun on :abbr:`ELF
(Executable and Linking Format)`) which describes everything a
debugger needs to know to, uh, debug a program.  That includes a
breakdown of all the data types involved (``typedef``\ s, structures,
unions, etc., sounds good!) but not the actual function call interface
as that is in the executable and part of the calling convention we
just talked about.  *Grr!*  But we're close.

You do have to have some sample code, say for a call to
:manpage:`getrusage(2)`, which we might use to ``time`` things:

.. code-block:: c

 #include <sys/time.h>
 #include <sys/resource.h>

 void foo (void)
 {
     struct rusage r;
     getrusage (RUSAGE_SELF, &r);
 }

which is enough to get you the enumerated type for ``RUSAGE_SELF`` and
a recursive breakdown of ``struct rusage`` and all its constituent
members (which turn out to be a lot of ``union``\ s to force alignment
to the interface's declared ``long``\ s) including the ``struct
timeval`` members:

.. code-block:: bash

 gcc -g -o getrusage.o getrusage.c
 objdump -g getrusage.o


But nothing about the call to :manpage:`getrusage(2)` itself and that
it takes an ``int`` and a ``struct rusage *`` as arguments.

How annoying.

So, :abbr:`WIP (Work In Progress)` and, in the meanwhile, continued
hand-crafting.

SWIG
----

.. rst-class:: center

---

Expect
======

.. _Expect: https://core.tcl-lang.org/expect/index

.. _Tcl: https://www.tcl-lang.org/

:ref-author:`Don Libes`' Expect_ (first released in 1990) is an
extension to :ref-author:`John Ousterhout`'s Tcl_ (Tool Command
Language, first release in 1988).

.. sidebox:: I have used :lname:`Tcl` for its intended purpose,
             directly controlling some test equipment.

	     Although I suspect that the API was set up to be
	     :lname:`Tcl` for *$REASONS* and some backend code poked
	     the kit over the wire.

	     Still, Tool Command Language, indeed.

:lname:`Tcl` is something of a :term:`marmite` language -- but aren't
all programming languages something of an acquired taste? -- though I
prefer using it to :lname:`Perl`'s ``Expect`` package.  No-one's
perfect!

:lname:`Expect` let's you *interact* with programs that expect [hah!]
to be being used by a user on a terminal.  I'm sure many of us have
been through a phase of confidently throwing a file of predicted
answers as input to a command and been "disappointed" when the command
didn't ask the questions that those answers were predicated on.

:lname:`Expect` lets you look at the command's output from which you
can make a decision as to how to progress.  Many programs will change
their behaviour based on some state that is out of your control.  I'm
trying to log into another computer, this time it asks me to confirm a
host identity, next time it doesn't, even though the command I used
was the same.

I mostly use :lname:`Expect` for the ``send``/``expect`` interaction
and relatively rarely for its other powerful feature that you can
automate logins, say, and then *hand control back to the user*.

You could augment that with some "escape codes" (key sequences the
user is unlikely to type normally, say, :kbd:`+++` followed by a
digit) which would signal that :lname:`Expect` should take back
control, log into a different box and hand control back to the user
again.  Very neat.

You can extend :lname:`Tcl` like many languages and I was obliged to
write an extension to hook in some Unix Semaphores to dig myself out
of a hole caused by a worthy but ill-thought out requirement.

.. _`Bob's your uncle`: https://en.wikipedia.org/wiki/Bob%27s_your_uncle

What :lname:`Expect` is doing under the hood is more exotic systems
programming.  It gets a new pseudo-tty through the interfaces
described in :manpage:`pts(4)`.  In a ``fork``\ ed child you can close
file descriptors 0, 1 and 2 then open the pseudo-tty appropriately to
give you file descriptors 0, 1 and 2 now attached to the pseudo-tty.
Cue a wall of terminal oriented systems programming (didn't I say I
didn't want to get involved with terminals...?) and `Bob's your
uncle`_.

To be fair, many of the uses for :lname:`Expect`-like behaviour are
fire-and-forget but sometimes we need to pull some information back
and once again, if we have had to out-source the implementation to
another program we have the problem of handling the quoting of the
results (output!) coming back.

If we can do it "in house", all's well.

.. rst-class:: center

---

Finite State Automata
=====================

My bugbear here is :program:`make`.  For some reason it annoys me that
embedding commands in :file:`Makefile`\ s is so complicated.  Anything
beyond the most vanilla invocation becomes a hot mess.

It feels like the :ref:`here-document` issue we've mentioned before.

.. _Ant: https://ant.apache.org/

.. aside:: Do I recall correctly that Ant_ was created because someone
           was having too hard a time with makefiles?

	   And they used XML to improve things?

Now, I hesitate to suggest that replacing the extensive features of
:program:`make` would be trivial but it got me thinking.

Workflows
---------

.. _workflow: https://en.wikipedia.org/wiki/Workflow

Quite a lot of our activities orchestrating processes are poorly coded
workflow_\ s.  Poorly coded in the sense that whilst they start at the
top and work their way down to the bottom, they don't tend to encode
any state and certainly don't persist that state.

Many of my scripts have to handle idempotency -- have I done this bit
already, OK, do something slightly different.

Would we be better off if we could encode what the script is meant to
be doing in some state driven mechanism which we can suspend and
resume?

BPM
^^^
.. _`Business Process Management`: https://en.wikipedia.org/wiki/Business_process_management

That opens up the world of `Business Process Management`_ (and all of
its horrors).

.. rst-class:: center

---

screen / tmux

Security - ssh - keys

hooks into sqlite for persistence

XML

JSON (no comments, NULL, "true"/true) -> JSON5

YAML

TOML
