.. include:: ../../global.rst

.. _vtables:

*******
vtables
*******

.. sidebox::

   We want to be careful, here, in that we're talking about vtables
   for values and not (yet!) vtables for multi-methods.  However, it's
   a stepping stone.

In Release 0.0 we've built a functional mechanism for handling values.
However, it's pretty bespoke, as in, there are very few generic
functions.  Obviously, all predicates are generic in the sense that
they'll say *yeah* or *nay* for any supplied value, whatever its type
but, by and large, functions are type-specific.

.. aside::

   ``type->string`` is also pretty inefficient as it returns a new
   string each time you call it, failing to memoize the type-to-string
   mapping.

   Not to worry, it was fit for purpose which was to discover what you
   have in your hands, it wasn't used in anger.

One of the few that you might argue isn't, is :ref:`type->string
<ref:type->string>` which, unsurprisingly, returns a string describing
the value's type.  It should really be returning a symbol, though,
giving us a putative ``type->symbol`` which you would sensibly
decompose into ``type``.

Printing is another generic (set of) function(s) although printing is
something of `a dog's dinner
<https://www.collinsdictionary.com/dictionary/english/a-dogs-dinner>`_
which we'll come back to.

A more interesting pair of cases are :lname:`Idio` structures and
:lname:`C` structs both of which support a notion of being able to get
and/or set named members.  As things stand we either call
:samp:`struct-instance-ref {v} {member}`, which is fairly generic, or
some type-specific :samp:`libc/struct-timeval-ref {v} {member}`
function, say.

The nominally generic :ref:`value-index <ref:value-index>` looks at
the type of :samp:`{v}` and either calls :ref:`struct-instance-ref
<ref:struct-instance-ref>` or the type-specific reference function
associated with the :lname:`C` type through the CSI mechanism (which
will check that :samp:`{v}` is of the right :lname:`C` type).

In both cases, the setting function is provided through the
:ref:`setter <setters>` functionality.

For both getters and setters, though, ``value-index`` needs to figure
out the type and do the correct type-specific thing.  It would, of
course, be better if ``value-index`` simply asked for the getter
function, whatever the type.

What if the type doesn't have a getter, for example, if we tried to
``value-index`` a fixnum?  Previously we would have raised a
``^rt-parameter-value-error`` noting that the value is non-indexable.
If a type doesn't have a getter method associated with it then we
should raise a ``^rt-vtable-method-unbound-error``.

Background
==========

:ref-author:`Ian Piumarta and Alessandro Warth`'s :cite:`oeom` paper
provides a very readable introduction to vtables for dynamic object
models.  That's heading towards the full multi-methods scenario and,
indeed, they do that academic thing where go all-in and demonstrate
that everything can have a vtable and it is all self-supporting.

We don't need to go there but we can take away a few interesting
things.

In their model, the vtable, mapping names of methods to
implementations, doesn't point to their :lname:`C` implementation
directly.  Rather they indirect via a "ClosureVT" which associates the
actual implementation with some arbitrary data.

That's very subtle.  Now you can re-use the same implementation across
several similar types.  You could imagine using the same
:manpage:`printf(3)`-style printing function for all of the :lname:`C`
base types but associate with each a different *length modifier*
(``%hh``, ``%l``, etc.) with each type.  We won't do that but you can
imagine you could.

Another interesting aspect, and something of interest to us, is that
you might associate the implementation of a closure with the byte code
interpreting function (``idio_vm_run1()``) with a small chunk of byte
code.

We'd have to up-end a lot of things to make that work but then we need
to think about something along those lines anyway for
:ref:`pre-compilation`.

Implementation
==============

Our implementation is reasonably simple.

We'll have an ``idio_vtable_t`` which has an array of
``idio_vtable_entry_t`` each mapping a method name (a symbol) to a
``idio_vtable_method_t`` method (which has the :lname:`C`
implementation function pointer and the arbitrary data).  The
``idio_vtable_t`` can have a parent which, for most of our types
including :lname:`C` structs, will be ``NULL`` but could be another
``idio_vtable_t`` and thus we can draw the same relationship between
:lname:`Idio` struct-types as the struct-types have themselves.

idio_vtable_t
-------------

.. code-block:: c

   struct idio_vtable_s {
       unsigned int flags;
       struct idio_vtable_s *parent;
       int gen;		/* generation */
       size_t size;	/* # entries, ie. methods */
       idio_vtable_entry_t **vte; /* array of size methods */
   };

We've thrown in another field, ``gen`` for the generation.  Any time
we modify a vtable's methods or parentage then the overall generation
increments.  Whenever we look to use a vtable we'll check to see if
this vtable is out of date in which case we'll validate our tree
(bringing all tables in the hierarchy up to date).

In the future, ``parent`` should be a list to accommodate multiple
inheritance.  We *could* have made it an :lname:`Idio` list but then
we have to walk down the hierarchy of vtables in all of our objects in
the GC.  We'll hit GC-oriented problems soon enough!

idio_vtable_entry_t
-------------------

.. code-block:: c

   struct idio_vtable_entry_s {
       struct idio_s *name;
       unsigned int inherited:1;
       unsigned int count:31;
       idio_vtable_method_t *method;
   };

Here we have our name-to-method mapping but with a couple of other
fields.

Until we recognise we are a generation out of date, we can inherit any
parent method locally saving lookup time.

We can also increment a usage counter whenever this method is looked
up.  Post-lookup, the code can quietly "bubble-up" the method in the
vtable's array of ``idio_vtable_entry_t``'s so that next time the most
used methods are found sooner rather than later.

idio_vtable_method_t
--------------------

.. code-block:: c

   struct idio_vtable_method_s {
       struct idio_s *(*func) (struct idio_vtable_method_s *method, struct idio_s *value, ...);
       size_t size;
       void *data;
   };

Nothing exciting here.

Apart from the arguments to the :lname:`C` method.  In the first
instance we need to pass ourselves in order that the implementation
can access ``data`` (and ``size``).

:samp:`{value}` is the :lname:`Idio` value we're operating on and
``...`` is obviously a varargs component.

.. sidebox::

   Printing is even worse but I said we'd get back to that.

The problem is that we don't know what arguments are going to be
necessary for the implementation.  You can imagine that the ``type``
method takes no (extra) arguments.  We know that the ``value-index``
methods are going to take a :samp:`{member}` argument and a setter (if
we defined such a vtable method and there wasn't a proper setter)
would take :samp:`{member} {v}` arguments.

Method Creation
^^^^^^^^^^^^^^^

There are two kinds of method creation, ones that have some (or no)
static :lname:`C` data associated with them and ones that have an
:lname:`Idio` value associated with them.

For the :lname:`C` variants, ``size`` and ``data`` reflect the
arguments passed.  We either copy the supplied data or not.

For the :lname:`Idio` variants we know that an ``IDIO`` value is a
:lname:`C` pointer so we can clearly stuff the value in ``data``,
which is another :lname:`C` pointer, but then we have something of a
problem.  The GC is not going to be walking down the set of vtable
methods trying to second-guess if the ``data`` value is really an
:lname:`Idio` value and needs to be accounted for.

Here, we're going to have to take a hit and stash the value into a
hash table of ``idio_vtable_method_values`` so that we can be sure the
value won't be GC'd from under our feet.

We want a hash table, here, as we don't know if someone has previously
passed us this value and appending the same value repeatedly to an
array is wasteful.

Idio values
-----------

We need to add a vtable to every :lname:`Idio` value.  For most of
them that's easy enough as it'll just sit inside the ``struct
idio_s`` and be set at instantiation by the type-specific code:

.. code-block:: c

   IDIO idio_closure (...)
   {
       ...
       IDIO c = idio_gc_get (IDIO_TYPE_CLOSURE);
       c->vtable = idio_closure_vtable;
       ...
   }

where ``idio_closure_vtable`` was instantiated itself by the closure
initialisation code:

.. code-block:: c

   void idio_init_closure ()
   {
       ...
       idio_closure_vtable = idio_vtable (IDIO_TYPE_CLOSURE);
       ...
   }

For fixnums and constants etc. we need to define some global vtables.
These are scattered throughout the code base in files broadly
associated with their usage: ``idio_fixnum_vtable`` in
:file:`src/fixnum.c`, say.

In the same vein, we'll need an ``idio_value_vtable()`` function to
return either the vtable in the ``struct idio_s`` or one of those
global vtables as appropriate.

vtable.c
--------

Creating vtables
^^^^^^^^^^^^^^^^

The code to create a vtable maintains an array of all created vtables
(broadly, one per type) and sets the generation of the new vtable to
the current (global) generation counter.

Adding Methods
^^^^^^^^^^^^^^

The code for adding a method and inheriting a method only differ by
the "inherit" flag so they call the same base code.  We can describe
the "add" functionality:

* add the method name

  The method name is an :lname:`Idio` symbol and we need to avoid
  having the name GC'd from under our feet so we can add it to an
  array of ``idio_vtable_method_names``.

* look for this method name in our array of ``idio_vtable_entry_t``

  If we find an existing one we can overwrite it.

* if we didn't overwrite it then we need to add another element to the
  array of ``idio_vtable_entry_t``

* increment the global generation value so that future method lookups
  know that something has happened somewhere

If we are inheriting then we don't need to add the method name or
increment the (global) generation count.

Method Lookup
^^^^^^^^^^^^^

Looking up a method isn't hard:

* walk through the array of ``idio_vtable_entry_t`` for the method
  name

  Here we can increment the lookup counter and if this isn't in the
  first slot and has a higher count than the entry in the previous
  slot then swap them over so we'll find this more popular method
  sooner next time.

* if we didn't find the method name and we have a parent then lookup
  the method in our parent (or list of parents, in the future)

  If we get back a method -- failure to find a method will eventually
  raise a condition -- then we can call the method inherit code.

vtable Validation
"""""""""""""""""

At the start of method lookup we'll want to validate the vtable if the
generation count is behind the global counter.

This is a little squirrelly as the side-effect of validation should be
to reset the per-vtable generation to the current global value and yet
we simultaneously want to know if one of our ancestors had had a
generation newer than us (which will invalidate any of our inherited
methods).

The overall trick is to remember the current vtable's generation with
the intention of returning it to our caller.

Then we recurse into our parent, if any, and capture the value *it*
returns.

If it returned a generation newer than us then we update the value we
will return and invalidate any inherited methods.  We do the latter by
bubbling any non-inherited methods up over any inherited methods and
reducing the array size appropriately.

So, we might think we are only using 3 slots out of a (memory)
allocated 5 slots and hopefully ``idio_realloc()`` won't get upset
when we ask to increase the array size to 4 and then 5 slots again.

dump-vtable
^^^^^^^^^^^

Obviously, we should have a :ref:`dump-vtable <ref:dump-vtable>`
function so we can check what's going on!

Type Variances
--------------

Most types are going to follow a fairly benign pattern of not doing
very much.  They'll have a vtable with some methods.

Other types are a bit more interesting as we have the concept of a
type and an instance of a type.

C/pointers
^^^^^^^^^^

Regular C/pointers are benign, we're more interested in those we've
previously applied a C Structure Identification (CSI) mark to.

In this case, when we create such a "typed" C/pointer we want to
create a *type*-specific vtable for it whose parent is the base
C/pointer vtable.

If we look in the supplied CSI data we'll have:

#. the struct's nominal name, say, ``libc/struct-timeval``, a symbol

#. a list of the members of the :lname:`C` struct

#. (possibly) a *-ref* function -- usually a primitive

Here, we look for, or create, a vtable for this "type" of C/pointer
(in the ``idio_C_pointer_type_vtables`` hash table) which we can point
to from this C/pointer instance of the C/pointer "type".

structs
^^^^^^^

:lname:`Idio` structs are a bit more interesting as we want to match
the parentage of the struct-type within the vtables.

Of course, that's incredibly easy as, when we create the struct-type,
we can make the vtable's parent for this struct-type be the vtable of
the struct-type's parent.

struct-instances
""""""""""""""""

For struct-instances it gets a bit more messy.  For all other
instantiations of a type, think: 37, a fixnum, the underlying type is
a :lname:`C` construct.  For a struct-instance the underlying type is
an :lname:`Idio` struct-type.

Whilst most of the operations on an instance of the struct-type should
be methods defined against the struct-type, think that the
``typename`` method is associated with the fixnum type and not the 37
*per se*, we might want to legitimately ask questions about the
struct-type itself.

Printing is the obvious problematic case.  If I want to print a
struct-instance it would probably involve some :samp:`{field}={value}`
output, whereas printing a struct-type would want to print just the
fields but also the name of the parent struct-type.

Methods
-------

Let's look at a few methods.

typename
^^^^^^^^

This is our putative ``type`` method but we'll use a separate name,
:ref:`typename <ref:typename>`, while we're getting a feel for things.

In every possible case we will have a symbol in our hands describing
the name of the type.  We need to add all the :lname:`Idio` basic type
names into :file:`src/symbol.[ch]` but for "typed" C/pointers and
struct-types we'll have a type name passed to us.

That means we can use a method with a bit of stored ``data``, a symbol
for the type's name and a generic method which simply retrieves the
stored data and returns it.

Let's have a look at fixnum:

.. code-block:: c
   :caption: :file:`src/fixnum.c`

    idio_vtable_add_method (idio_fixnum_vtable,
			    idio_S_typename,
			    idio_vtable_create_method_value (idio_util_method_typename,
							     idio_S_fixnum));

where ``idio_vtable_add_method()`` wants to take a vtable, a method
name and a method.  ``idio_vtable_create_method_value()`` will create
a method from the :lname:`C` function pointer and the :lname:`Idio`
type name we want to return as data.  There are
``idio_vtable_create_method_*()`` methods for other kinds of data.

The method's :lname:`C` implementation:

.. code-block:: c
   :caption: :file:`src/util.c`

   IDIO idio_util_method_typename (idio_vtable_method_t *m, IDIO v, ...)
   {
       IDIO_C_ASSERT (m);
       IDIO_ASSERT (v);

       IDIO data = (IDIO) IDIO_VTABLE_METHOD_DATA (m);

       if (idio_isa_symbol (data) == 0) {
	   idio_error_param_value_msg_only ("typename", "method->data", "should be a symbol", IDIO_C_FUNC_LOCATION ());

	   return idio_S_notreached;
       }

       return data;
   }

Here, not only do we ignore the varargs but we don't even do anything
with :samp:`{v}`, the value the method is operating on, as we simply
retrieve the ``data`` from the method definition.

Of course it become trivial to write a primitive that calls that
method:

.. code-block:: c
   :caption: :file:`src/util.c`

   IDIO_DEFINE_PRIMITIVE1_DS ("typename", typename, (IDIO o), "o", "\
   return the type name of `o`	\n\
				   \n\
   :param o: object		\n\
   :return: the type of `o`	\n\
   ")
   {
       IDIO_ASSERT (o);

       idio_vtable_method_t *m = idio_vtable_lookup_method (idio_value_vtable (o), o, idio_S_typename, 1);

       return IDIO_VTABLE_METHOD_FUNC (m) (m, o);
   }

All we need to do now is for each type add the same kind of method:

.. code-block:: c
   :caption: :file:`src/closure.c`

    idio_vtable_add_method (idio_closure_vtable,
			    idio_S_typename,
			    idio_vtable_create_method_value (idio_util_method_typename,
							     idio_S_closure));

Identical other than the vtable used and type name supplied.  The very
differences we are concerned with.

For struct-types and "typed" C/pointers, at the time of creation we'll
have a struct-type name or the CSI data will have the :lname:`C`
struct name and so we can add the ``typename`` method on the fly as
we're passing through.  The C/pointer vtables are cached by CSI info
so we're not repeating ourselves.

Finally, let's see it in action (running :program:`ls` to get a useful
value in ``%%last-job``):

.. code-block:: idio-console

   Idio> typename 37
   fixnum
   Idio> typename load
   closure
   Idio> ls -U
   LICENSE  doc  ext  lib  src  utils  LICENSE.others  Makefile  README.md  bin  tests  CONTRIBUTING.md
   #t
   Idio> typename %%last-job
   %idio-job
   Idio> typename (libc/gettimeofday)
   libc/struct-timeval

An interesting side-effect of this is that we won't ever see
``struct-instance`` as a type (even though it is a distinct
:lname:`Idio` GC type) as semantically it is no different than asking
for the typename of 37.  37 is an instance of a fixnum and
``%%last-job`` is an instance of a ``%idio-job``.

Similarly, you won't see ``struct-type`` as a typename as all
struct-types are their own type.

.. code-block:: idio-console

   Idio> typename %idio-job
   symbol			;; doh! %idio-job is not exported from job-control
   Idio> module job-control
   #<unspec>
   job-control> typename %idio-job
   %idio-job

.. aside::

   Note to self: start reading about object models...

This is slightly unexpected compared to r0.0 (for which
:ref:`type->string <type->string>` will still return
``"struct-instance"`` and ``"struct-type"``) but is more correct as we
head towards an object model.

members
^^^^^^^

:ref:`members <ref:members>` should return the list of members of a
struct-instance or C/pointer instance.

Given that the ``data`` we want to pass is an :lname:`Idio` list we
could re-use the same :lname:`C` implementation function as
``typename`` although we should (probably) check for the data type
being a list (of symbols) rather than a symbol.

Otherwise it works the same.

.. code-block:: idio-console

   Idio> members %%last-job
   (pipeline procs pgid notify-stopped notify-completed raise? raised tcattrs stdin stdout stderr report-timing timing-start timing-end async)
   Idio> members (libc/gettimeofday)
   (tv_sec tv_usec)

Of course, it doesn't make sense to ask for the members of something
that has none:

.. code-block:: idio-console

   Idio> members 37
   default-condition-handler:[20075]:libc.idio:line 465:members:^rt-vtable-method-unbound-error:method 'members' is unbound: detail value is a fixnum: name members
   ...

Printing
--------

Printing is awkward on two fronts:

* strings and unicode have a different presentation depending on
  whether they're being printed (in a manner suitable for the reader
  to use, think: ``"foo"`` or ``#U+0061``) or being displayed (in a
  manner suitable for humans to read, think: ``foo`` or ``a``)

* unlike most methods, this functionality wants to be called from the
  :lname:`C` code base as well as from the :lname:`Idio` code base

That said, the real problem is that we can define printers for things.
In r0.0, for struct-instance and C/pointer types.

And I did say that struct-instances were awkward?

struct-instance
^^^^^^^^^^^^^^^

Here, the problem is that we might well define a printer for a
struct-instance but the struct-type is also (user-)defined and is
worthy of being printed out in its own right.

A struct-instance printer might gloss over the administrative details
in the struct-type whereas you might want to know that the
administrative details exist (and have to ask for them individually as
the printer doesn't print them).

So the definition of a printer for a struct-instance or a struct-type
defines a ``struct-instance->string`` vtable method distinct from the
``->string`` vtable method which mechanically reports the fields names
and parent type (if any).

display-string
^^^^^^^^^^^^^^

We can (reasonably) easily address the display vs print string by
having a ``->display-string`` vtable method for those entities that
need one and fall back to a ``->string`` vtable method if one isn't
found.  The displayed and printed representations of fixnums are
identical, for example, so there's no need to have separate functions
to do the displayed or printed form.

This means, for most types, that there is a failed method lookup for
``->display-string`` followed by a successful method lookup for
``->string``.

At this point you might consider forging an "inherited"
``->display-string`` method which is really just the ``->string``
method except we get into a(nother) mess.

This time the problem lies in that the mechanism to add a printer
modifies the ``->string`` vtable method.  But we've just "inherited"
the ``->string`` vtable method as the ``->display-string`` method.
What could possibly go wrong?

Fortunately, the test suite stumbled on to this as it tested bad
printers, one's that don't return a string.  The order of demerit is:

#. add a bad printer to a C/pointer type

#. have the C/pointer displayed which

   #. inherits the ``->string`` method as the ``->display-string`` method

   #. raises a condition

#. the code *did* re-add the proper C/pointer type printer which does
   bump up the vtable generation

#. however, as none of the parent vtables had changed there was no
   cause to invalidate any inherited methods

#. the next ``display-string``/``format`` of that C/pointer type would
   invoke the errant ``->display-string`` vtable method and raise an
   unexpected condition

The fix is two-fold:

#. don't inherit the method unless it has successfully returned a
   string

#. if, when validating a vtable, we didn't invalidate any inherited
   methods because of an ancestor's vtable generation change then run
   through specifically looking for an inherited ``->display-string``
   method and invalidate it

I did say it was a mess.

C calling
^^^^^^^^^

We want to print values out from the :lname:`C` code base all the
time, it's a thing.  The :lname:`C` code base can be a bit more
efficient if it stays in the realms of ``char *``\ s and doesn't have
to decode :lname:`Idio` strings repeatedly.

The obvious solution is to split the printing into two parts, a
:lname:`C` variant, say, :samp:`idio_{X}_as_C_string()`, which returns
the requisite ``char *`` and a vtable method, say,
:samp:`idio_{X}_method_2string()` (where the :lname:`C` ``2string``
aligns with the :lname:`Idio` ``->string``), which calls the
:lname:`C` variant and constructs an ``IDIO`` object from it.

Now, we can replace the historically enormous switch statement that
was ``idio_as_string()`` (in :file:`src/util.c`) with a new (still
large enough, sadly) switch statement that knows about all the
:samp:`idio_{X}_as_C_string()` variants and calls those directly.

The printing of any given type can now migrate into the
:file:`src/{X}.c` source file that handles most of the type's other
behaviour.

Defining Printers
^^^^^^^^^^^^^^^^^

Defining printers messes everything up.

If we're "coming in" from :lname:`Idio`-land, say, ``%format`` (the
base of the ``printf`` calls) calling ``display-string``, then we
dutifully lookup the vtable ``->display-string`` method (modulo all
the ``->string`` nonsense, above) to get a :lname:`C`
:samp:`idio_{X}_as_C_string()` or user-defined printer, either of
which we can call.  That seems easy enough.

If we're "coming in" from :lname:`C`-land, say, ``idio_as_string()``,
we're going to directly call the :samp:`idio_{X}_as_C_string()`
:lname:`C` function because that's all we know.

Hmm, so how do we get to run the user-defined method if one exists?

.. aside::

   Ugly!

Bah!  Here, we have to have the :lname:`C` function *also* (or
alternatively) perform the vtable method lookup but this time
carefully check that the method's :lname:`C` function pointer isn't
itself.  If it is something else then we call it and return the value
otherwise we fall back to whatever the default behaviour is.

Implementation
""""""""""""""

There's still the question of how to run the user-defined method.

The historic mechanism has been to invoke the function with the value
to be printed (duh!)  and a "seen" value, defaulting to ``#n``.

We can generalize that, to some degree, by stashing a list, say,
:samp:`({func} [{arg} ...])`, in the value of the method and have an
implementation function, ``idio_util_method_run()``, which extracts
the list, inserts the ``value`` parameter it was given, re-arranging
it as :samp:`({func} {value} [{arg} ...])`, something we can pass
directly to ``idio_vm_invoke_C()``.

In the particular case of :ref:`add-as-string <add-as-string>` which
takes ``o`` and ``f`` parameters:

.. code-block:: c

    idio_vtable_add_method (idio_value_vtable (o),
			    m_name,
			    idio_vtable_create_method_value (idio_util_method_run,
							     IDIO_LIST2 (f, idio_S_nil)));

.. sidebox::

   Which means you cannot override the default printer for a
   struct-type.

where we have ``m_name`` defaulting to ``idio_S_2string`` but swapped
for ``idio_S_struct_instance_2string`` for when ``o`` is a
struct-instance or struct-type.

.. include:: ../../commit.rst

