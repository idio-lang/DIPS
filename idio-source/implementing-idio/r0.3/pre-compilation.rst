.. include:: ../../global.rst

*****************
Pre-Compilation I
*****************

.. aside::

   Software Engineering-wise, a complete disaster.

This has been a huge investment of time and effort with a pragmatic
but incomplete result.  I've conflated ideas, tried to pursue too much
at once, missed swathes.  A hopeless mess.  Let's get into it.

The basic plan is to replace the live evaluation of source code when
:lname:`Idio` starts up with a system that reads in the pre-compiled
byte code saving time and effort.

.. aside::

   We'll come back to this...

Many :lname:`Lisp`\ y languages support the notion of *undumping*
where, having parsed all of the startup source code into its internal
(byte code) form, the system saves that internal form back out ready
to roll for next time.

The Problem
===========

The crux of the problem with reading in some byte code it that that
byte code cannot know anything about the running :lname:`Idio` engine
when it starts.  Well, it can make some presumptions about the set of
*primitives* in the :program:`idio` executable, probably, but it can't
know whether, say, the symbol ``load``, refers to a primitive or a
closure.  (In fact, ``load`` will refer to both, and be used in the
wrong order!)

This is individually true for every file loaded in as none of the
loaded files can predict what a previously loaded file has done to
modify the state of the :lname:`Idio` engine.

The fix to not knowing anything is to have to look everything up.
Easy!

Strategy
========

I ran around some thoughts previously in :ref:`pre-compilation` and
hopefully have brought it all together here.

A couple of things from that discussion didn't sink in at the time.
The first is the x86_64's use of relative instruction pointers (RIP)
into the GOT to access variables for the loaded object which might be
extremely convenient there but does seem to my eye to be a touch
confusing.  A naïve ``x + x`` would use two different RIPs to access
the same variable.  How would you keep track?

The second was the global offset table (GOT) where all the
doubly-dereferenced entities live.  I couldn't quite see where the GOT
was kept as it is loaded-object specific.  It turns out that it is in
a register.  Which register?  Why, *any* register, of course, it's up
to you to maintain it and apply the appropriate register to your
instructions.

.. aside::

   Yeah, it's obvious *now*\ !

This then led me to the idea that the *VM*'s threads should have
another "register" maintaining a reference to whichever set of tables
needed double dereferencing for this block of code.

For the VM
----------

That leads us to the idea of a table, or series of tables, where the
byte code (restricted to small positive integers) will embed a *symbol
index*, :samp:`{si}`, which will be mapped through (some other tables)
to a *global value index*, :samp:`{gvi}`, containing the value the
*VM* wants to operate on.  We need a common global value index because
my symbol index to the global variable ``A`` is different to your
symbol index for ``A``.  If I then used my own value index for ``A``
then how are you supposed to know what to access/update?

In between symbol index and global value index we want to:

* do a cached lookup of the :samp:`{gvi}` immediately

* otherwise, a one-time:

  * recover a symbol from the loaded object's tables

  * do a symbol lookup of the symbol through the current and imported
    modules (which will contain the global value index or be
    auto-vivified as a symbol -- think ``ls``)

  * set the cached :samp:`{gvi}` for next time

  * use the :samp:`{gvi}` as above

This creates the idea of an *execution environment*, or *xenv*, one
per loaded file, with an associated :samp:`{xi}`, the index into the
table of all xenvs.

I settled on a basic three tables for the *VM*:

#. a symbol table mapping the symbol index, :samp:`{si}`, to an index
   into the constants table, :samp:`{ci}`

   You only need symbol indices for things you need to lookup (as
   though they were variables).  *symbol* symbols are just constants
   (if that makes any sense!):

   .. code-block:: idio-console

      Idio> printf "%s is %s\n" 'load load
      load is #<CLOS load [14]@50196/0x7f2dc6f7f610/Idio>

   Here, we quote the first use of ``load``, as in ``'load``, to
   access the *symbol* ``load`` which will result in a lookup of some
   constant index, :samp:`{ci}` in the byte code.  The second use of
   ``load`` is as a variable which means we must do a ``SYM-REF`` of a
   symbol index, :samp:`{si}`, to force the *VM* to resolve a
   :samp:`{gvi}`.

   In particular, the :samp:`{si}` for ``load`` (the second) will map
   to the same :samp:`{ci}` for ``'load`` as they reference the same
   *symbol* and there can be only one!

#. a constants table containing all of the, uh, constants used in the
   loaded file

   Here, constants are, essentially, anything that isn't a small
   positive integer that can be embedded into the byte code -- think
   symbols, strings, bignums etc..

   In the example from above, there will be constants for the symbol
   ``printf``, the string ``"%s is %s\n"`` and the symbol ``load``
   (only once, there can be only one... *[Ed - stop it!]* )

   There is an associated constants hash table which reverses the
   constants table lookup -- very handy.

#. a values table which maps loaded file value indices, :samp:`{vi}`,
   to the global value indices, :samp:`{gvi}` used by the *VM*

   A :samp:`{gvi}` of ``0`` (zero) is a sentinel value indicating that
   the global value index hasn't been looked up yet.

   Again, for our example, there will be value indices for the symbol
   indices for ``printf`` and ``load``.

Here, it is *critical* that the :samp:`{si}` and :samp:`{vi}` align.
That's because the very first thing we do with a :samp:`{si}` is query
the values table at slot :samp:`{si}` to see if the corresponding
index is non-zero.  If non-zero we can access the global values table
straight away.

If it is zero then we'll have to:

#. use the symbol table to map the :samp:`{si}` to some :samp:`{ci}`
   
#. use the constants table to map the :samp:`{ci}` to a symbol

#. lookup the symbol information tuple in the current environment (or
   create a new symbol tuple for the auto-vivified symbol)

#. extract the :samp:`{gvi}` from the symbol information tuple

#. set the values table at index :samp:`{si}` (the :samp:`{si}` and
   notional :samp:`{vi}` align) to :samp:`{gvi}` ready for next time

#. use the :samp:`{gvi}` index into the global values table as before

Note, however, that for operational reasons, you will have more value
indices (values you need to use) than you will have symbol indices
(symbols you want to lookup) leaving the symbol table with some gaps.

A prominent example, here, is the :ref:`previous work <Lambda Lifting
I>` to separate the creation of closures into two parts: a one-time
``CREATE-FUNCTION`` and a per-use ``CREATE-CLOSURE``.  The
``CREATE-CLOSURE`` needs to refer to the value resulting from the
``CREATE-FUNCTION`` and a value index is reserved for that purpose
leaving the corresponding symbol table index unused.

There are some knock-on effects of xenvs in that, say, any closure
defined in an xenv will have embedded in its byte code references to
that xenv's tables.  As a consequence, the definition of a closure
must now include the xenv or, rather, the :samp:`{xi}`, it was defined
in such that those lookups will be correct.  Similarly, the *arguments
constant index*, :samp:`{aci}`, for a *frame* refers to a constant in
the current xenv and so to decode it, the frame needs to include the
:samp:`{xi}` for the :samp:`{aci}`.

.. aside::

   Noting that ``load`` is defined in the startup then somehow we've
   managed to defined fourteen other xenvs before we started!

You can see that in the printed form of the closure ``load``, above:
``#<CLOS load [14]@50196/0x7f2dc6f7f610/Idio>`` where the ``[14]`` is
indicating that ``load`` was defined in :samp:`{xi}` 14.

The *VM* also has some other tables of interest:

#. a source code expressions table

   This is an array of source code expressions.

   This exists whilst the source code is being parsed but is not saved
   as it is not possible to recreate this data sensibly without
   re-parsing the source code.

   Consider, ``((1 + 2) * (3 + 4))`` where the *reader* can
   successfully maintain references to the internal sub-lists of the
   main expression but when written out becomes three distinct lists,
   ``((1 + 2) * (3 + 4))``, ``(1 + 2)`` and ``(3 + 4)``, with the
   larger one repeating the smaller two.  This duplication of lists
   balloons the memory requirements enormously.

   It may be reported in the disassembled code if the ``--vm-tables``
   flag is passed to :program:`idio` but otherwise is lost.

#. a source code properties table

   (This is one-for-one with the source code expressions table,
   above.)

   This is an array of :samp:`({fi} {line})` tuples where :samp:`{fi}`
   is the index into the constants table for the source code's file
   name.

   The source code properties table is what is indexed by the
   ``SRC-EXPR`` opcode.

Modules
-------

The symbol/variable lookup works much as before in that there is a
module-specific tables of known (and possibly) exported symbols which
contain some internal symbol information data.

That symbol information is a tuple of:

* the kind of symbol (``'predef`` (primitive), ``'toplevel``,
  ``'dynamic``, ``'environ``, etc.)

* an :samp:`{si}`

  Up to r0.2 this was an unreliably module-specific :samp:`{ci}`.

* a :samp:`{ci}`

  Up to r0.2 this was a global :samp:`{ci}`.

* a :samp:`{gvi}`

* the module the symbol was defined in

  This is useful for debugging as, in order to get this tuple, you
  must have known the correct module to ask the question of in the
  first place.  In other words, a module is already known.  However,
  as modules import names from other modules, some import history is
  observable.

* a descriptive string

  This is useful for debugging as it usually hints at the last
  modifier of this data.  Although this isn't reliable.

Evaluator
---------

In addition, the *evaluator* wants to maintain slightly more
information, essentially an association list of the symbol and the
symbol information tuple.

It'll keep track of things in an *evaluation environment*, or *eenv*.

Three Problems
==============

I tried to do three things at once which, you might guess, didn't end
well.

Maintain the Existing Mechanism
-------------------------------

As I already had a perfectly good working system, despite it not
implementing this new strategy, I thought I could maintain it.  The
plan was to pre-compile the known startup files (using
:file:`lib/evaluate.idio` rather than :file:`src/evaluate.c`).

Here, several things went wrong:

* a lack of surety that :file:`lib/evaluate.idio` actually does the
  same thing as :file:`src/evaluate.c`

  The problem here being that, whilst :file:`lib/evaluate.idio` can
  run the test suite quite happily, the test suite doesn't exercise
  the evaluator quite as much as the startup code does.

* the pre-compilation was flawed (see below)

* :file:`lib/evaluate.idio`, via :file:`lib/expander.idio`, implements
  a different template expansion mechanism than
  :file:`src/evaluate.c`, via :file:`src/expander.c`

  This means the resultant (disassembled) code is hard to compare
  (easily).

* when you load the pre-compiled code, using the new strategy, back
  in, the :lname:`Idio` engine behaves differently to the way it
  behaves when evaluating the startup code "live."

  This makes debugging very difficult as the engine is following
  different paths through the code base.

In the end I junked the idea of a special "first pass", reworking it,
and therefore everything, to use the new strategy.

Pre-Compile
-----------

.. aside::

    Read: much at all.

I hadn't thought pre-compilation through properly.

Here the problem is that the behaviour of the code is dependent on its
current state.  If one expression would have modified that state then
the next expression may react differently.  Most of the time this
isn't an issue as the *VM* would "just" look a value up or, at least,
just use a value as modified by the previous expression changing it.

However, we made the judicious decision to allow predefs (primitives)
to be shadowed by (hopefully) improved versions in the form of
closures.  The problem here is that the calling conventions for
primitives and closures are not the same.  Internally, once the
arguments have been computed you can simply call the primitive's
underlying :lname:`C` function with the various arguments.  For a
closure, we construct a frame and copy the argument values into the
frame, change the *PC* to the start of the function and have the
closure code extract arguments from the frame.  The creation and
filling of the frame is completely unnecessary for primitives.

For pre-compilation we have to pretend to modify the program state so
as to know whether the use of a symbol will be for a predef or a
closure.

As it stands, though, the code modifies the *real* program state not a
pretend one.  That's sort of OK for source code you've not seen before
(although, in effect, you are *running* the source code, not
performing a standoff-ish pre-compilation) but is close to disastrous
for source code you *have* seen before such as the startup code.

For the startup code we are trying to distinguish between running the
code for the first time and any subsequent runs which we don't want to
modify the program state because it affects the running program...

A great example, here, is the use of operators by the reader.  Having
started up we now have a full set of operators and we want to run
:file:`lib/evaluate.idio` over the startup code.  However, as the
startup code is being read in, which would normally have no operators
present (as they haven't been defined yet) operators get applied
because we're a fully operational\ *[sic]* system.

I did try an entertaining method of removing the user-defined
operators then carefully re-adding them as the user-definition
appeared.  That (surprisingly) worked but didn't help with the other
modifications of real program state.

Of course it took a while to realise that in modifying the extant
state I wasn't pre-compiling but merely sowing confusion.

Implement the Strategy
----------------------

Actually implementing the strategy is a thing in itself, of course,
with its own set of problems and nuances.

We'll cover this in detail in the next sections.  In the meanwhile...

Undump
======

.. aside::

   A *lot* of time.

I spent a lot of time debugging and requiring more and more detailed
dumping of state, the sort you can see with the ``--vm-tables`` flag,
before realising that the "live" state I was dumping was, in fact, the
very thing I should be using.  All I needed to do was reformat the
output into the chosen cache file format and... *Boom!*  Job done.

Of course, this is exactly the *undumping* described previously.  *Ho
hum.*

Implementation
==============

It's a little bit complicated with a symbiotic relationship between
xenvs and eenvs.  Here, it transpires, as the evaluator reads in
source code it must maintain the newly extended source, constant and
value tables as well as generating the byte code for the *VM*.

The reason for this is that any interactive session must cycle between
reading in source code and running the compiled byte code.  The
evaluator sets everything up ready for the *VM* to roll.

The *VM* also needs to be able to refer back to the original source
file used by the evaluator so it maintains a reference to the eenv
through the xenv.

Evaluator Changes
-----------------

Much of the evaluator's new behaviour has been abstracted behind some
:samp:`idio_meaning_find_{scope}_symbol()` (and
:samp:`meaning-find-{scope}-symbol`) functions which, if the symbol is
not already known to the evaluator will call
``idio_meaning_extend_tables()`` (``meaning-extend-tables``) which
looks to ensure that the symbol and values tables are aligned.

The symbol itself can be added to the constants table (and hash), if
necessary, and that :samp:`{ci}` used in the symbol table.

The values table is extended to keep it aligned but note that, at this
point, no :samp:`{gvi}` can be known and the value table entry is set
to zero.

It will grow the (association) list of known symbols (in this eenv)
and, optionally, set the module's symbol information tuple with the
same information (including the zero :samp:`{gvi}`).

xi 0
----

:samp:`{xi}` 0 (zero) is the xenv for the global tables, notably the
global values table which everything else indirectly seeks to refer
to.

C add_primitives
----------------

Most of the :lname:`C` modules have an ``idio_X_add_primitives()``
function to bootstrap the system with several hundred primitives.

There's nothing to stop module ``A`` defining the same named primitive
as module ``B`` -- it does happen: ``number?`` is either the regular
:ref:`number? <ref:number?>` (for fixnums and bignums) or the
:lname:`C`-specific :ref:`C/number? <ref:C/number?>` that identifies
:lname:`C` numeric types.  So the code in
``idio_meaning_predef_extend()`` needs to select a module-specific
eenv to add the primitive into.

This is the primary reason there are so many xenvs "prior to" starting
up: they're the result of the evaluator creating a separate eenv (and
therefore xenv) for each :lname:`Idio` module that has had a primitive
defined for it.  These are really just holding spaces with no
associated code.

This addition of a primitive is one of the rare occasions that a value
is known in the here and now for the evaluator.  Accordingly, it can
request a new global value index and retro-fit that :samp:`{gvi}` back
into the symbol information tuple created by the extend tables code.

Evaluation
----------

Evaluation proceeds much as it did before except that name lookups are
performed through the eenv-specific list of known symbols rather than
resorting to any recursive lookup through imported modules.

The resultant symbol information tuple now contains the all important
:samp:`{si}` for the symbol which is going to be embedded in the byte
code.

This means that the first time the evaluator sees the symbol, say,
``printf``, in your code it will fail to find it in its list of
previously seen symbols and so extend its tables for this eenv to add
``printf`` as a new constant, an :samp:`{si}` mapping to that new
:samp:`{ci}` and a new values table entry of zero (meaning, the *VM*
needs to look this up).

This is deferring that resolution of ``printf`` to runtime.  It only
needs to be resolved once (as the resolving code will have updated the
values table index with the real live :samp:`{gvi}`) but it is delayed
to runtime.

This is the correct behaviour for a "pre-compiled" file being loaded
in.  It doesn't know how this :program:`idio` executable has laid
everything out so it must look it up at runtime.

Shadowing Predefs
^^^^^^^^^^^^^^^^^

This doesn't happen much but it does happen with a rather critical
function, ``load``, so we need to sort it out.

The primitive ``load`` opens the file and tries to evaluate and run
every expression.  That's great until there's an error or even where
the loaded file redefines the current module.  Who resets everything?

That's when our closure ``load`` (in
:file:`lib/bootstrap/module.idio`) comes into its own.  It utilizes
:ref:`unwind-protect <ref:unwind-protect>` to ensure that the current
module is reset to whatever it was before ``load`` was invoked.  Of
course, otherwise, this ``load`` simply calls the primitive ``load``.

As noted previously, the calling convention for primitives and
closures is different therefore we need to ensure that we know when
which variant of ``load`` is being called.

In practice, the closure ``load`` isn't a definition, it is an
assignment to the symbol ``load`` because the closure is being defined
inside a block to retain access to the original primitive ``load``,
something like:

.. code-block:: idio

   {
     orig-load := load

     load = function (filename) {
       ...
         orig-load filename
       ...
     }
   }

We can't *define* ``load`` inside the block as it will become a block
local variable (who's scope ends at the end of the block).

So we need to capture assignments to a symbol which is currently
flagged as a predef.

We can't just override the value because somewhere there will be byte
code (you imagine the call to ``orig-load filename`` being one of
them) which is expecting a primitive and it's calling convention and,
at the same time, we need to prep for code that is expecting our new
shiny closure and *its* calling convention.

So we need to extend the eenv's symbols again with the same symbol but
now different information.  Future lookups of ``load`` will get a
symbol information tuple for a regular toplevel definition and do the
right thing.

xi Predefs
^^^^^^^^^^

Part of the problem, here, for ``load`` is that the assignment happens
before the primitive is called.  Technically, the primitive ``load``
is invoked in order to load :file:`bootstrap.idio` but that happens in
a non-xenv-specific way.  When the bootstrap code is run, ``load``
(closure or primitive) is not invoked until after we've performed this
assignment which makes you wonder who set up the original association
between some :samp:`{si}` and the primitive ``load`` in this xenv in
order that the assignment to ``orig-load`` at the start of the block
finds anything at all.

.. aside::

   Er, oops.

Answer: no-one!

So we need to record the set of predefs that this xenv uses in order
that, having loaded the compiled code file in we can run round the set
of used predefs setting up the value table mapping from :samp:`{si}`
to the :samp:`{gvi}` that the :lname:`C` "add primitives" code set up.

xi Operators
^^^^^^^^^^^^

In a similar way, we might define an operator in this eenv/xenv but
operators always exist in the ``operator`` module, not the current
module.  That's because their usage is effectively global in that they
must be visible through the reader which looks for them in a
consistent place, the ``operator`` module.

That said, the definition of the operator closure *is* in this eenv
and all of its internal symbol references will use this eenv's symbol
table etc..

So, operators are handled slightly differently to other toplevel
definitions in that they exist in this eenv but their symbol
information tuples are set in the ``operator`` module.

This distinct set of known operators is saved and restored for no good
reason other than general tidiness.

Stack Values
^^^^^^^^^^^^

The *VM* will push some "values" onto the stack as it is processing.
For example, the condition a trap is for, dynamic and environment
variables.

What we *can't* do is push values that are xenv-specific as we won't
know which xenv we are referring to.  We need to push values that are
globally recognised.

That's not a big deal but it is a deal we need to do.

For all of them, we'll pass an :samp:`{si}` in the usual way and have
the runtime code discover the appropriate current global value.

Traps
"""""

For a trap we want to push the global equivalent of the :samp:`{si}`'s
:samp:`{ci}`.  So that's an extra ``constants_lookup_or_extend`` in
the global constants table (in :samp:`{xi}` zero).

Dynamics and Environs
"""""""""""""""""""""

For dynamic and environment variables we'll (continue to) push the
:samp:`{gvi}` of the variable.

That allows separate bodies of code to temporarily create a shadowing
dynamic/environment variable, which will use a new :samp:`{gvi}`.

Invoking
========

``--save-xenvs``

Operational Effects
===================

It's a mixed bag, I'll be honest.

.. sidebox::

   :file:`lib/bootstrap/delim-control.idio` being a particularly
   egregious example where the ratio of template expansion to
   resultant working code is something like 50:1.

In the first instance, loading the compiled startup files, there is a
huge runtime saving.  When evaluating the code, the first time, the
evaluator has to expand all the templates which is very expensive.
This results in some 7.5 million opcodes being run, all in, by the
*VM*.

The resultant code is at least an order of magnitude smaller requiring
around 208 thousand opcodes to be run.

However, the constant double dereferencing far outweighs that benefit
and the overall effect is that the test suite, say, takes about 15-20%
longer.

It's not just the double de-reference *per se*, it is the jumping
about in memory and the complete lack of cache coherence in the code
that is the problem.

On reflection, it might be necessary to revisit this with a view to a
leaner "first pass" with the startup code (and only the startup code?).

Here we'd be going back to the idea of using :samp:`{xi}` zero
directly, ie. the :samp:`{si}`, and therefore nominal :samp:`{vi}`,
*is* the :samp:`{gvi}` and needn't be dereferenced again.

Problems Problems
-----------------

We have a problem if :lname:`C` code wants to look a variable up as no
xenv specifically represents a module.

We have a problem if a loaded file redefines a value already set in
this file.

We have a problem in that *gensyms* are saved.

.. include:: ../../commit.rst

