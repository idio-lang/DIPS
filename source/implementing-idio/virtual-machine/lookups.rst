.. include:: ../../global.rst

****************
Variable Lookups
****************

We can't just "not look variables up" any more, we need a better plan.
The plan is, to some degree, much like you would expect for a language
like :lname:`C` where the use of a variable name is a thin veneer over
the use of a memory location.  You can imagine the :lname:`C` compiler
allocating slots in memory, big enough to hold a value of type *t* and
then whenever the variable's name is referenced it substitutes in an
access of that memory location.

To, hopefully, few people's surprise that is exactly what we are going
to do.  We'll have a big array of values in the VM and then whenever
the evaluator sees a variable name it will reference its "name to
value array index" table and replace the reference to the variable
name with a reference to the variable's index into this value array.

This doesn't happen for all variable names.  Lexically scoped
variables are already handled with a lookup system, this only affects
"free variables."

So, our example of:

.. code-block:: idio

   n := 3

   define (foo) {
     n + 1
   }

would become a nominal:

.. code-block:: idio

   n := 3		; n is allocated index 99, say

   define (foo) {
     #vi:99 + 1
   }

where :samp:`#vi:{index}` is our symbolism for this value array index.

There's a couple of cases that make life a bit more interesting.

Modules
=======

Modules in the context of variable lookups are going to act as a form
of lookup restrictions.  You can see what is in the module's "top
level" and what is in the exports of it's imported modules (noting
that everybody imports from the ``Idio`` and ``*primitives*`` modules
and all of their variables are exported automatically).

That means that (cross-importing aside) variable ``n`` in module
``m1`` is different to variable ``n`` in module ``m2``.  Exactly what
you'd expect.

In turn, as a side-effect, each module has to maintain a set of
variable names that have been defined at "top level" in that module
alongside the value index used for it.

If a variable name is used but is undefined (in the current top level
or the exports on the imported modules) then it will be added to the
current module's top level (rather than necessarily to the ``Idio``
module's top level).  *Just saying!*

Of course that means we have to maintain a sense of what the current
module actually is.  In principle that's no biggie but in practice it
means being a little underhand.  The problem lies in *who* is doing
the recording of the current module.  It should be the concern of the
VM because it's running the code, right?  Actually, not really, the VM
expects to be given value indices in the byte code and only really
maintains the current module in case someone asks for it.

In practice, the evaluator really needs to know what the current
module is in order that it can find the right value index: it needs to
know if the source code is changing from module ``m1`` to module
``m2`` in order that it can figure out the correct value index for
``n`` to be put in the byte code for the VM.

Unfortunately, the only way the evaluator can do that is to identify
the "change module" function call and read the argument itself.  That,
as a side-effect, means you cannot use a variable (or an expression)
when changing module, you must use the module's true (symbolic) name
-- we can't expect the *evaluator* to rely on someone pre-evaluating
arguments for it, can we?

Therefore, this won't work:

.. code-block:: idio

   mod := 'm1
   module mod

because the evaluator isn't really evaluating, it's inferring meaning
from the forms and can only see the symbol ``mod``, so it thinks
you're changing to module ``mod``.

In the meanwhile, the evaluator can build up a symbol table for the
module containing some useful information associated with each name
created in the module.

The information is for internal use but currently consists of:

* the variable type -- probably *toplevel* in this instance

* the VM constants index

* the VM value index

* the module the symbol was originally bound in -- this is clearly
  useless in the face of re-use but is handy for debugging

* a string indicating the entity that created this

You can access this information with ``find-symbol`` -- noting that it
takes a symbol as an argument, not a value:

.. code-block:: console

   Idio> find-symbol 'read
   (#<CONST predef> 594 908 #<module libc> "idio_predef_extend")

Suggesting (to me) that the symbol was first created in the ``libc``
module as a *predefined* element (ie. a primitive) by the :lname:`C`
function ``idio_predef_extend()``.  ``read`` is #594 in the constants
table and this maps to value #908 in the values table.

You can dump out the VM's constants and values tables if you pass the
``--vm-reports`` option to :program:`idio` then search for those
indices in :file:`vm-constants` and :file:`vm-values` (created when
:program:`idio` exits cleanly).

Forward Lookups
===============

If we revisit the first example, we can legitimately re-write it as:

.. code-block:: idio

   define (foo) {
     n + 1
   }

   n := 3

Hmm.  When the evaluator works its way through the definition of
``foo`` it'll find reference to the variable ``n`` which it hasn't
seen a declaration for (yet).

However, if ``n`` exists as one of the exported symbols from the
modules that this module imports from then we're about to have a
problem.  The evaluator will find ``n`` amongst those exports and use
it, say :samp:`#vi:{e}`.

If we now come across the declaration of ``n`` a few lines later,
about to be dubbed as :samp:`#vi:{i}`, say, it's too late, we've
already bound the ``n`` in ``foo`` to :samp:`#vi:{e}`.  *Whoops!*

On the other hand, if ``n`` was not defined amongst the exports of
imported modules then we can:

* create a new value -- initialised to some sentinel value, ``#<undef>``, say

* add an index in the name to value index table, :samp:`#vi:{k}`

* use an opcode to access it marking that this is in preparation for
  an impending declaration

and carry on.

Now, when we hit the declaration of ``n``, the lookup of the variable
name will give us :samp:`#vi:{k}` and we're good to go.

There's a couple of boundary cases here:

#. if we *never* see a declaration of ``n`` then VM, because of the
   special opcode used which can check if the value is still
   ``#<undef>``, will/should impute your `descendency from rodents
   <http://www.montypython.net/scripts/HG-tauntscene1.php>`_

   Although how *should* we deal with this (other than demeaning
   elderberries with your familial history)?

#. repeated declarations of ``n`` do not give rise to new indices

   .. code-block:: idio

      n := 10
      n := 20

   is functionally no different to:

   .. code-block:: idio

      n := 10
      n = 20

.. _`pre-compilation`:

Pre-Compiled Modules
====================

There are no pre-compiled modules as I type -- I aborted an attempt
but the thinking prevails.

Suppose we can pre-compile modules as standalone entities that another
:lname:`Idio` instance can load in and run.

Suppose our module looks like:

.. code-block:: idio

   module m

   n := 3
   
   define (foo) {
     n + 1
   }

Hmm.  ``n`` will have been resolved to some value index,
:samp:`#vi:{i}`, say.

However, under these module-compiling circumstances, we **do not**
want to resolve ``n`` to this :samp:`#vi:{i}` because :samp:`{i}` is
true of this *currently running instance* of :lname:`Idio`.  If we
stop and start :lname:`Idio` then the perturbation of values --
imagine the modules are loaded in a different order -- might mean that
``n`` *should* resolve to :samp:`#vi:{j}`.

What we really should be doing is storing a reference to the *symbol*
``n`` so that when we load in and run the pre-compiled module then we
can determine that we need to lookup ``n`` *under the current
circumstances* and generate the corresponding :samp:`#vi:{j}` then.

This becomes a double de-reference: once for name to value index and
then to get the value itself.  It looks like it would be useful to
subsequently store this symbol to value index lookup in a per
compiled-module "local value index" table.

Of course we don't want to store *symbols* in the byte code either --
as they are a very non-uniform size, unlike numbers which are merely
slightly non-uniform -- so we need a table of symbols now as well as
well as the local value index table becoming a symbol table index to
value index table....  *Keeping up?*

OK, instead of ``n`` being replaced with a value index in the
generated byte code, we need to replace it with a symbol index,
:samp:`#si:{x}`, say.  So, what is :samp:`{x}`?  Well, if we were back
in the main compilation engine (rather than pre-compiling a module),
we might use the VM's "constant index" -- so, arguably a
:samp:`#ci:{x}`.  The constant table is a big table of all the
constants (*no, seriously?*) that the evaluator has seen.  Symbols are
unique and ``n`` is the same symbol whether it is in module ``m1`` or
``m2``.

However, in our pre-compilation mode, much like the value index, we
can't predict what order the constants are going to appear in a future
:lname:`Idio` engine so we need a per-compilation name to constants
index table to be attached to the pre-compiled code.  This makes it
more like a :samp:`#mci:{x}` -- a (pre-compiled) module constants
index.

So, for pre-compilation, we need to build a local symbol table of free
variables used in the code and we substitute in the byte code a
constant index, :samp:`#ci:{x}` and :samp:`{x}` is the index into the
symbol table to recover the free variable's name.

However, we only need to lookup the value index once, after which it
will always keep the same value index in the currently running VM.  We
can play another little trick.  The byte code has :samp:`#ci:{n}`
embedded in it.  Suppose we always go straight to the value index
table.  We can differentiate between the first and subsequent
iterations by initialising the index here to :samp:`{-n}`.

At every access of the local value index table we can then perform a
test: is the value negative?

* if negative then access the symbol stored in the local symbol table
  at :samp:`{n}` and use the :lname:`Idio` engine's lookup mechanisms
  to figure out if the symbol exists in the current module or an
  export of its imported modules or whether we need to create a new
  value index.

  Either way, we store the resultant (always positive) VM value index
  over the top of the initial :samp:`{-n}` value

  Continue on to access the variable with the value index

* if positive then use the value index to access the variable

.. csv-table:: Module Value Table
   :widths: auto
   :header: index,initial,subsequent
   :align: left

   1,-1,:samp:`{vi-a}`
   2,-2,:samp:`{vi-b}`
   3,-3,:samp:`{vi-n}`

.. csv-table:: Module Symbol Table
   :widths: auto
   :header: index,value
   :align: left
   
   1,``a``
   2,``b``
   3,``n``

.. rst-class:: center

---

In our small code block above it looks like we would have a single
entry symbol table with ``n`` being in slot 1 and therefore the
generated byte code will reference :samp:`#ci:1`.

Let's use a slightly bigger example to flesh this out:

.. code-block:: idio

   module m

   a := 1
   b := 2
   n := 3
   
   define (foo) {
     n + 1
   }

So, not much bigger.

Our pre-compiled module, then, might have a local symbol table like:

.. parsed-literal::

   1: a
   2: b
   3: n
   4: foo
    
and our function ``foo``, will have had ``n`` resolved to
:samp:`#mci:3` from that table -- where we are now using a
(pre-compilation) module constant index.

The local value index is initialised to:

.. parsed-literal::

   1: -1
   2: -2
   3: -3
   4: -4

``-3`` says look up index ``3`` in the symbol table giving us ``n``.
We can now resolve that through the normal module import/exports
mechanisms to get some value index, :samp:`#vi:{i}`, say, and then
rewrite the local value index table as:

.. parsed-literal::

   1: -1
   2: -2
   3: *i*
   4: -4

Now we can access the value correctly with :samp:`{i}` and any
subsequent use of ``n`` will find the value index pre-resolved to
:samp:`{i}` as well.

.. rst-class:: center

---

Perhaps, not hugely surprisingly, that all sounds very much like the
business of the Unix link loader part of whose job is to resolve any
symbol references.

:ref-author:`Eli Bendersky` has written a document on `Position
Independent Code in shared libraries
<https://eli.thegreenplace.net/2011/11/03/position-independent-code-pic-in-shared-libraries/>`_
which covers this sort of thing for x86 (real computers).  What it
boils down to though is that the generated code references a
:abbr:`GOT (Global Offset Table)` associated with the code and the GOT
is re-written to contain the actual memory location of the variable
*per this instance*.

.. rst-class:: center

---

Augmenting Modules
------------------

.. aside:: © `Jimmy Cricket <https://www.jimmycricket.co.uk/>`_

And there's more!

Suppose our little snippet of code was in addition to an already
existing body of code under the guise of module ``m``.

:socrates:`Should adding to an existing module be allowed?  Should it
be disallowed?`

Skipping those vital questions, let's suppose we're augmenting module
``m`` with the vital function ``foo``.  Our pre-compiled code block
has referenced "top level" variables ``a``, ``b``, ``n`` and ``foo``.
That's great for the snippet but how does anyone else find out about
these names?

It sounds like we also need to add those names, if necessary, to the
module's symbol table in the main :lname:`Idio` engine which,
depending on what is stored there, might give us access to the
associated value index without us having to look it up.  Our snippet
of code is always going to be (double) dereferencing through its local
value index table but we have the opportunity to resolve any of those
value indices with ones that already exist in the main module's symbol
table.

Forward Lookups II
==================

Hmm, we had a problem with forward lookups where if no declaration of
``n`` was ever made we would have left a :samp:`#vi:{k}` in the byte
code and have the :lname:`Idio` engine shouting from the ramparts.

This double dereferencing sounds plausible in this scenario to.  If
``n`` is not defined then change the dereference from a
:samp:`#vi:{k}` to a :samp:`#ci:{n}` and the byte code can at least
retrieve the variable name from the constants table and throw that in
the torrent of abuse directed at your antecedents.

Review
======

It looks like we have three varieties of lookups:

#. non-pre-compiled code where we have definitively looked up the
   instance of a variable

   Here we can use a VM value index directly.

#. non-pre-compiled code where we have a forward reference to a
   variable name

   Here we could use a value index (where we had initialised the
   *value* to some sentinel -- which we check).

   Although we should use a VM constants index (causing a double
   dereference) in order that we can report the variable name.  We
   still have to check the value has been defined.

#. pre-compiled code where we don't know about constant or value
   indices in the future :lname:`Idio` instance

   Here we *will eventually* use a per-compiled module local symbol
   and local value index tables.  The local value index is initialised
   to :samp:`{-n}` so we can use the symbol table to get the variable
   name and then look it up, re-writing the local value index table in
   the process.

It also looks like we have a per-module symbol table with details of
names that have been defined in its top level.

.. include:: ../../commit.rst

