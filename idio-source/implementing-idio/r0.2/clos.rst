.. include:: ../../global.rst

****
CLOS
****

Tiny CLOS is a tiny, er, CLOS.  So what is CLOS?

`CLOS <http://community.schemewiki.org/?CLOS>`_ refers to the Common
Lisp Object System.  That link will take you through to documents
describing `meta-object-protocol
<http://community.schemewiki.org/?meta-object-protocol>`_ as well as
:ref-author:`Erick Gallesio`'s STklos_, :ref-author:`Eli Barzilay`'s
`Swindle <http://www.cs.cornell.edu/courses/cs212/Swindle/>`_ and
others all of which give some background and inspiration.

CLOS QuickRef
=============

That still doesn't tell us what CLOS is.  The primary difference with
more familiar object systems are probably that whilst the class
hierarchy is much the same, in that classes have super-classes and
slots (or fields), the functions that operate on classes are not
elements of the classes but are, so-called, generic functions which
will can be applied to any set of arguments.

You then define methods, tied to the generic function by name, which
declare that for given parameter classes, use this method.  The magic
in the system is how to determine which method should be called given
a particular set of arguments.

Generics are making their way into other object systems but another
key difference, and partly why generic functions are not elements of
the class hierarchy, is that they are not restricted to selecting an
implementation method based on one (usually the first) of their
arguments but use all arguments to select the most specific method.

We now get another intriguing concept.  In single-inheritance object
systems you have the concept of being able to call your super-class'
comparable method, often through a function called ``super``.  In
multiple-inheritance object systems that doesn't make sense as the
function isn't tied to any one of its arguments and instead you have
the concept of the next most specific method, indeed a chain of them
from the most specific applicable method through to the least specific
applicable method.

That also brings front and centre *applicability* as the generic
function isn't restricted to having methods appropriate to you and
your classes but for any and all classes, should anyone write a method
for them.

Here, think of something like a printer.  You might have a
``print-object`` generic function where you can add methods
appropriate for your classes or allow the fallback method (associated
with the base ``<object>`` class) to print nothing or whatever.

CLOS goes a bit further with some concepts to do with methods.  In
addition to what are called primary methods it has the idea of methods
that should be run before or after any corresponding primary methods
and even methods that should be run around other methods.

A final word on the :abbr:`meta-object-protocol (MOP)` which is a
mechanism by which the behaviour of the object system can be
controlled by giving every instance in the system a meta-class.
Meta-classes are, *of course*, just regular classes and all classes
are instances of other classes giving the whole enterprise the sense
of a digital `Gordian knot
<https://en.wikipedia.org/wiki/Gordian_knot>`_.  When
:ref-author:`Kiczales` talks about "initializing the braid," he means
it.

Tiny CLOS
=========

.. aside::

   Let's not miss this boat!

:ref-author:`Gregor Kiczales`, after co-authoring :ref-title:`The Art
of the Metaobject Protocol`, :cite:`AMOP`, in 1991, published
TinyCLOS_ in 1992 which has become a popular base for
:lname:`Scheme`-ish languages' object systems.

.. aside::

   We'll try to :strike:`steal`\ re-imagine as much as we can.

Much of what was described for CLOS is available in :lname:`Tiny CLOS`
and where :lname:`Tiny CLOS` is pedagogical in nature, others have
looked at making the implementation a little more efficient and
broader in scope.

I'll try to break :lname:`Tiny CLOS` down, throwing in a few notes.
Some terms get overused, mind, for example, instance.

One thing to remember, though, is that Tiny CLOS is *tiny*.  A full
multi-methods object system in, depending on what support code you
include, 600 lines of code.  It'll take far more lines to describe
what's going on.

You'll want to follow along with :file:`tiny-clos.scm`, probably from
the GitHub mirror at `https://github.com/kstephens/tinyclos
<https://github.com/kstephens/tinyclos>`_ as modern browsers don't
like FTP links any more.

Memory Model
------------

The underlying memory model in :lname:`Tiny CLOS` is a :lname:`Scheme`
vector, akin to an :lname:`Idio` array.  Anything could have been
used, we just want to access individual slots.

The first three slots represent the meta-class, the instance proc and
a lock.  The lock is used to prevent the instance proc being used for
non-generic functions -- something we can do in other ways.

The instance proc itself is a slightly disjoint concept.  The idea is
that if this value is found to be in functional position, about to be
applied to zero or more arguments, then we want something to run to
implement behaviour.  A vector (array) in functional position isn't
going to do much so we want something to substitute in, in its place,
to actually do some work.

All instances will have an instance proc -- that's just the way the
data structure is laid out -- but it is only a useful concept for
generic functions, which are the only things we expect to find in
functional position (and therefore need the instance proc to implement
behaviour).

The remaining slots are either descriptive (for a class) or data (for
instances of classes).

:lname:`Tiny CLOS` goes a step further and instead of returning an
instance, the vector, perhaps, returns a function which, when invoked,
actually calls the instance proc.  This is done for two reasons:

#. it's a neat trick meaning that the instance, here, generic
   function, despite notionally being a data structure, is implicitly
   invokable

   We don't need to go there as we have a :lname:`C` function,
   ``idio_vm_invoke()``, which decides if something is invokable.
   We've bodged all sorts in there already, symbols and strings will
   be looked for down the :envvar:`PATH`, continuations are invokable
   (or rather, we rewrite the stack and jump to a new instruction!) as
   well as closures and primitives.

   If we want to add generic functions as something that is invokable,
   by substituting in the instance proc and carrying on, then so be
   it.

   I first saw this invokable-object trick in :ref-author:`Bill
   Hails`' :ref-title:`Exploring Programming Language Architecture in
   Perl` (:cite:`EPLA`) and :ref-author:`Eli Barzilay` notes that for
   :lname:`Swindle`, :lname:`PLT Scheme` "has applicable struct
   objects", so, not without precedent.

#. because classes and instances are self-referential, it avoids some
   complications in printing such a value

   Instead, the regular printer can simply say this "instance" is an
   (opaque) function.

The system still needs to get the associated vector so the function is
used as an index into an association list of :samp:`({function}
{vector})` tuples which itself is a private variable for a suite of
functions that need access to it.

A class has slots which describe the elements of the class:

* direct super-classes

* direct slots

* the class precedence list (CPL), which is the derived set of all
  relevant classes drawn from the class and its super-classes

  The CPL is critical to getting a deterministic method resolution
  order (MRO) which, let's be fair, sounds like a good thing.

* the slots, now including the non-duplicated set of super-class slots
  as well the direct slots

* a set of per-slot "getters-n-setters" -- often functions that simply
  access the corresponding slot in the underlying vector
  
An instance of a class has as many slots as the class description says
there should be!

Allocation
----------

Noting that we are saying in advance that the object system is going
to be self-referential, then at the very base level we need to
separate the allocation of an instance from the assignment of elements
in it.

Once we're beyond the bootstrap we can write, with increasing degrees
of "finality", a ``make-instance`` function that combines allocation
and assignment.

``make-instance`` is actually ``make`` in :lname:`Tiny CLOS` and other
variants which is fine for them but clashes rather spectacularly with
:program:`make` for us Shell People.

Class Bootstrap
---------------

Here we allocate ``<class>`` and, as the very first thing, set its own
meta-class ("instance-class" in the code) to... ``<class>``, itself.

What we're saying here is that when we come to do *stuff* if we want
to ask questions about how to implement the behaviour of class
``<class>`` then we should query the meta-class, ``<class>``.

OK, that's probably not helpful right now so we'll just leave it
hanging.  Of interest, almost everything has a meta-class of
``<class>`` as, perhaps unsurprisingly, almost everything is an
instance of a class which is described by ``<class>``.

OK, I'll stop.

Let's fill in the rest of ``<class>``'s slots, as much as we can right
now:

* ``direct-supers`` is ``#n`` -- to be modified in a moment

* ``direct-slots`` is this list of slots names that we're iterating through right now

* ``cpl`` is ``#n`` -- to be modified in a moment

* ``slots`` is the same as ``direct-slots``

* ``nfields`` is the count of the number of slots (seven!)

* ``field-initializers`` list of *nfields* functions which set the
  slot to ``#n``

* ``getters-n-setters`` is a list of *nfields* tuples with an
  appropriate ``vector-ref`` (``%instance-ref``) getter and a
  ``vector-set!`` (``%instance-set!``) setter

Of interest, most implementations drop ``field-initializers``, often
extending ``getters-n-setters`` to include an "init-function" and also
add another slot, ``name``, for self-reflection purposes.

make-instance I
^^^^^^^^^^^^^^^

At this point we can create our first ``make-instance`` (``make`` in
:lname:`Tiny CLOS`, of course) which is only aware of some simple
meta-classes which it knows how to manually construct.

We have the advantage that, at this stage, the computation of the CPL
and slots is going to be the straightforward merge of super-classes
and super-class direct slots.

We'll mostly be calling ``make-instance`` as:

    :samp:`make-instance <class> 'direct-supers {supers} 'direct-slots {slots}`

and can figure out the CPL, slots and compute some getters and setters
based on that information.

<top> and <object>
^^^^^^^^^^^^^^^^^^

We can now create a couple more classes to fix the top of the class tree.

A class, ``<top>``, with no super-classes or slots and a meta-class of
``<class>`` (of course).  It's the top of the class hierarchy tree.

A class, ``<object>``, with a super-class of ``<top>``, no slots and a
meta-class of ``<class>``.  ``<object>`` will be the base class for
all *object system* object values.  That doesn't mean it is the base
class for all objects as you might describe native types (pairs,
strings, etc.) slightly differently and, in an object class hierarchy,
directly descended from ``<top>``.  Native types aren't object system
objects *per se* but can be manipulated within the guise of an object
system.

Semantic nuance aside, that allows us to patch up ``<class>`` such
that its direct super is ``<object>`` and its CPL is, therefore,
``(<class> <object> <top>)``.

We now have a vaguely sensible class hierarchy of ``<top>`` to
``<object>`` to ``<class>`` all of which have ``<class>`` as a
meta-class.

Base Classes
^^^^^^^^^^^^

Finally we can create the remaining base classes:

* ``<procedure-class>`` the base class of all invokable classes

  It has a super-class (and meta-class) of ``<class>`` and no direct
  slots.

* ``<entity-class>`` a feature of MOPs

  It has a super-class of ``<procedure-class>`` and meta-class of
  ``<class>`` and no direct slots.

  I'll be honest, I've not quite got a finger on what an entity-class
  is in this (or any) context.  However, it appears in...

* ``<generic>`` the base class of generic functions

  It has a super-class of ``<object>`` and a meta-class of
  ``<entity-class>``.  ``<generic>`` does have a direct slot:

  * ``methods`` which is a list of the methods associated with this
    generic function

  Other implementations extend the slots with:

  * ``name``

  * ``documentation``

  ``<generic>`` is the only standard class that has a meta-class that
  isn't ``<class>`` (albeit noting that ``<entity-class>`` has a
  super(-super)-class of ``<class>`` and therefore you end up with the
  same slots anyway).

* ``<method>`` which is the base class of methods for generic
  functions

  It has a super-class of ``<object>`` and a meta class of
  ``<class>``.  ``<method>`` has a couple of direct slots:

  * ``specializers`` which are the classes of the arguments for which
    this method is appropriate

  * ``procedure`` which is the actual function to implement the method
    behaviour

  Other implementations extend the slots with:

  * ``generic-function`` to allow some cross-referencing

All of the above is a little dry, particularly with respect to generic
functions and methods.  Getting ahead of ourselves very slightly, in a
moment we'll be adding a bunch of generic functions and methods, one
of which is ``initialize`` which expects to be passed an instance of
some kind and some initargs.  We want to perform different actions
based on the kind of instance passed.

The :lname:`Tiny CLOS` mechanism is a little bit exposed:

#. :samp:`add-method {generic-function-name} {method}` will add
   :samp:`{method}` to the named generic function

#. :samp:`make-method {specializers} {function}` creates a method with
   the given parameter specializers and the given function definition

There's a couple of slightly confusing aspects here in that there
appear to be two extra arguments supplied to the function definition:
``call-next-method`` and ``initargs``, neither of which appear in the
list of specializers.

``call-next-method`` is a thunk we can call to do the moral equivalent
of calling ``super``.  It's always provided so there's no need to have
it in the specializers.

``initargs`` seems, to me, to be anomalous.  I think it should appear
as a specializer where, as we don't know what it is and therefore
can't give it a specializer, it will automatically be given ``<top>``
as a specializer.  I've tacked those on as comments.

.. code-block:: scheme

   (define initialize (make-generic))

   (add-method initialize
       (make-method (list <object>)			; (list <object> <top>) ??
	 (lambda (call-next-method object initargs)
	   ...
	   manipulate the <object> in object
	   ..
	   )))

   (add-method initialize
       (make-method (list <class>)			; (list <class> <top>) ??
	 (lambda (call-next-method class initargs)
	   ...
	   manipulate the <class> in class
	   ...)))

   (add-method initialize
       (make-method (list <generic>)			; (list <generic> <top>) ??
	 (lambda (call-next-method generic initargs)
	   ...
	   manipulate the <generic> in generic
	   ...)))

I find the :lname:`Scheme` above harder to read than I feel it should
be.  It all looks a bit by rote and indeed :lname:`STklos` leads us to
our preferred style through the template, :ref:`define-method
<ref:object/define-method>`, which looks like a regular function
declaration except with the formal parameters optionally qualified by
a class:

.. code-block:: idio

   define-method (initialize (obj <object>) initargs) {
     ...
     manipulate the <object> in obj
     ...
   }

   define-method (initialize (cl <class>) initargs) {
     ...
     manipulate the <class> in cl
     ...
   }

   define-method (initialize (gf <generic>) initargs) {
     ...
     manipulate the <generic> in gf
     ...
   }

Even better if ``define-method`` can implicitly create the underlying
named generic method.

make-generic
------------

We're not out of the woods yet.  There are nine generic functions
which define the MOP and, as we can't casually add generic functions
without the MOP, we need to pre-declare these nine.  Hence the:

.. code-block:: scheme

   (define initialize (make-generic))

   ...

which, more or less, reduces to a simple allocation of the generic
function.

add-method
----------

``add-method`` wants to do two things:

#. add the supplied method to the list of methods in the generic
   function

   Of course we need to be careful to remove any existing method with
   the same specializers as the one we're adding.

   Note, though, that the list of methods is just a list of methods
   without any ordering.  We can't know what ordering to use until
   someone invokes the generic function with some particular
   arguments.

#. set the generic function's instance proc, the thing that is going
   to figure out what the ordered set of applicable methods are with
   whatever the arguments are at the time of calling

   Here, we set the instance proc to the results of a call to the
   generic function ``compute-apply-generic``.

   .. aside::

      Doubter!

   :socrates:`Wait, what?  Generic functions don't work yet!`

   Also note that ``compute-apply-generic`` is expected to return a
   function, to become the instance proc, that will accept any number
   of arguments.  We don't know how many arguments generic functions
   are going to take in general, so these MOP generic functions must
   be ready.

compute-apply-generic
---------------------

So, let's review.  ``add-method`` is going to set the instance proc of
some generic function to be the result of calling the generic function
``compute-apply-generic``.  The act of invoking a generic function is
to actually call the instance proc of the generic function instead.
So ``compute-apply-generic`` needs an instance proc, right?  That
should sort it.

Here, as :ref-author:`Kiczales` notes, we need a couple of carefully
crafted functions.

#. we need a bootstrap function because ``add-method`` is going to
   call *something*, right?

   Here, we explicitly set the instance proc of
   ``compute-apply-generic`` to be a one-shot function that simply
   calls the first of the generic function's methods, because, well,
   because that'll work.

   Technically, of course, we don't call the method *per se* but,
   rather, apply the function in the method's ``procedure`` slot to
   the supplied arguments.

   Of interest, as we don't know (read: can't figure out) what the
   next methods should be for this one-off, as we called it blindly
   without looking at the specializers, we simply pass ``#f`` for
   ``call-next-method`` and trust that whatever this method is won't
   call it.

#. we need to ``add-method`` a genuine method to
   ``compute-apply-generic`` which

   * catches calls to a magic four generic methods (including
     ``compute-apply-generic``) whereon we call the *last* defined
     method -- in effect the *first* method that was added as new
     methods are pushed on the front of the list of methods

   * otherwise goes full-on MOP

   Here, some of the magic starts taking place.

   ``add-method`` adds the method to the generic functions list of
   methods before trying to set the instance proc to the result of the
   call to ``compute-apply-generic``

   Now that ``add-method`` is calling ``compute-apply-generic`` we run
   the one-shot function which (blindly) calls the first method on the
   list of methods (which we just added a moment ago).

   Here, there's a sleight of hand as the result of calling
   ``compute-apply-generic`` is to return a function, to become the
   next instance proc.  In other words, we can reduce the visual
   complexity down to:

   .. code-block:: scheme

      (add-method compute-apply-generic
	  (make-method (list <generic>)
	    (lambda (call-next-method generic)
	      (lambda args
		...
		do something *next time*
		...))))

   That's an important distinction, the one-shot function effectively
   called ``(lambda (call-next-method generic) ...)`` which returned a
   new instance proc for *next time*, not this time.

As it happens, that's it for ``compute-apply-generic``, we don't (need
to) touch it again.  It has a special clause for itself (never used)
and its three friends (which we're about to see) but otherwise will go
full-on MOP for anything else.

The MOP
-------

The MOP is actually the whole business of the introspection and
intercession (fiddling with!) of instances and classes but the real
magic lies in the full-on MOP part elegantly realised in
``compute-apply-generic`` as:

.. code-block:: scheme

   ((compute-apply-methods generic) ((compute-methods generic) args) args)

``compute-apply-methods``, ``compute-methods`` and the unseen
``compute-method-more-specific?`` are the other three special generic
functions which, like ``compute-apply-generic`` only have a single
method created for them and are handled separately.

They also return functions hence their results are applied in turn.

Let's try to figure this out.

.. aside::

   *Closures, eh?*  Sneaky beggars.

In the first instance, and this will be true for all four generic
functions, they were called with an argument, ``generic``, which is in
scope of the function they returned.

In the case of ``compute-apply-generic``, that function became the
instance proc and has now been called with some arbitrary ``args``.
So, both ``generic`` and ``args`` are available to us.

``compute-methods`` returns a function which, when applied to some
arguments, will figure out an ordered list of the applicable methods.
In other words, it will ignore methods whose specializers are not
appropriate for these arguments and then sort the resultant list by
some reasoning.

The applicability of a method is determined by ensuring that each
specializer in the method's specializers is a member of the CPL of the
class of the corresponding argument.

Sorting the resultant list is quite involved.  ``gsort`` in
:lname:`Tiny CLOS` is a simple wrapper to the slightly different
calling conventions of ``sort`` across the various :lname:`Scheme`
implementations.  We pass ``gsort`` a function that takes two methods
as parameters.

The sorting function, in turn, calls the generic function
``compute-method-more-specific?`` which itself returns a function that
takes the two method parameters and ``args`` again.

Here, now, we can walk over the specializers of each of the methods
and the corresponding argument asking if the specializer of one method
is a member of the list returned by asking for the membership of the
other method's specializer in the CPL of the class of the argument.

That probably needs an example but is a neat side-effect of the way
:ref:`memq <ref:memq>` works in that it doesn't simply return `true`
or `false` about membership but returns the rest of the list starting
at the match which can be exploited to see if the one is a (in this
case) "more specific" element than the other:

.. code-block:: idio-console

   Idio> cpl := '(C B A)
   (C B A)
   Idio> memq B cpl
   (B A)
   Idio> memq C cpl
   (C B A)

   Idio> memq C (memq B cpl)
   #f
   Idio> memq B (memq C cpl)
   (B A)

from which you can see that ``C`` is more specific than ``B`` because
it doesn't appear in the results of ``(memq B cpl)``.  Alternatively,
``B`` does appear in the results of ``(memq C cpl)`` meaning it is
less specific than ``C``.

Of course, this pre-supposes that the CPL of any class is itself a
ordered list which is another problem to come.

That now leaves ``compute-apply-methods`` which returns a function
which will take a list of the sorted, applicable methods, as returned
by the application of ``compute-methods``, and the original ``args``
again.

``compute-apply-methods`` is the action part but it has a surprisingly
complicated job of its own -- something has to implement
``call-next-method``.  Fortunately it's been given a sorted list of
applicable methods, what it has to do is massage those into a callable
chain.

That's the job of the internal function, ``one-step``.  This is a bit
complicated but let's ask what it should look like.

We expect that the most specific method is called with the arguments
``call-next-method`` (bound to a thunk) and ``args``, the original
arguments to the generic function (all that time ago!).

Invoking the thunk, ie. calling ``(call-next-method)``, should call
the next most specific method with the arguments ``call-next-method``
(bound to a thunk) and ``args``, the original arguments to the generic
function (again).

Hmm, it looks like once we jump onto this chain we'll merrily have the
opportunity to walk down (up?) the tree, if called.  How do we jump
on, though?  Well, ``one-step`` returns a thunk, so
``compute-apply-methods`` could simply apply the thunk resulting from
a call to ``one-step`` (with the full list of methods) which will call
the most specific method with ``call-next-method`` (bound to a thunk)
and etc. etc..

``one-step`` itself, simply checks whether there's any methods left in
the list and if so applies the function in the method's ``procedure``
slot with a call to itself, passing the tail of the method list, and
``args``.

The call to itself, of course, doesn't go into some infinite loop but
simply returns a thunk, ready to go one step further when it is called
in due course.

initialize
----------

:lname:`Tiny CLOS` now defines four variants of the generic function
``initialize``, as seen above, which is also passed ``initargs``.

The variants are for:

* ``<object>`` which does nothing interesting, just returning the
  ``object`` passed in

* ``<class>`` which is expecting ``initargs`` to optionally have
  :samp:`'direct-supers {supers}` and :samp:`'direct-slots {slots}`
  pairs of arguments

  It then gets busy figuring out values for all the class slots.

  There are three more generic functions involved: ``compute-cpl``,
  ``compute-slots`` and ``compute-getter-and-setter``.  We'll come
  back to these but as they are defined as generic functions it means
  they can be specialized by user-definitions.

* ``<generic>`` which doesn't do much, setting the list of methods to
  ``#n`` and a default instance proc to something reporting that no
  methods have been defined.

* ``<method>`` which looks for :samp:`'specializers {specializers}`
  and :samp:`'procedure {procedure}` argument pairs

allocate-instance
-----------------

:lname:`Tiny CLOS` defines two variants of the generic function which
only differ by the meta-class of the instance.  The body of the
methods runs through the ``field-initializers`` slot of the underlying
class and sets the initial value of the instance's slots.

compute-cpl
-----------

Here, I see most implementations veering away from :lname:`Tiny CLOS`
in the direction of `C3 linearization
<https://en.wikipedia.org/wiki/C3_linearization>`_ to determine the
class precedence list.

Ultimately, the goal is a deterministic :abbr:`method resolution order
(MRO)` which :lname:`Tiny CLOS` effects using the CPL.

The generic function is defined for the specializer ``<class>``.

compute-slots
-------------

Here, we're looking to collect a list of all direct slots and slots of
super-classes.

There's no distinction between identically named slots across classes
and the result is just the list of non-duplicated names.

The generic function is defined for the specializer ``<class>``.

compute-getter-and-setter
-------------------------

Here, we're looking to determine the getter and setter per slot.  The
arguments are ``class`` (specialized on ``<class>``), ``slot`` and
``allocator``.

make-instance II
----------------

Now that we've defined all the generic functions for the MOP we can
combine them all together into the final definition of
``make-instance`` (``make`` in :lname:`Tiny CLOS`):

.. code-block:: scheme

   (set! make
	 (lambda (class . initargs)
	   (let ((instance (allocate-instance class)))
	     (initialize instance initargs)
	     instance)))

where we allocate an instance of the supplied ``class`` with the
generic function ``allocate-instance`` before initializing the
instance with the generic function ``initialize`` passing the supplied
``initargs``.

And *Boom!*  A multi-methods object system is born.

Native Types
------------

There's a final nicety to provide a bit of completeness.  We can
define a bunch of classes representing the native :lname:`Scheme` (or
:lname:`Idio`) types, say fixnum, bignum, string, etc..

We can augment the ``class-of`` function which would normally return
the meta-class of an instance to check for each of the native types,
:ref:`fixnum? <ref:fixnum?>`, :ref:`bignum? <ref:bignum?>`,
:ref:`string? <ref:string?>`, etc. and return the corresponding type.

This now means that you can have a specializer of ``<fixnum>``,
``<bignum>``, ``<string>``, etc. and pass ``1``, ``1.0``, ``"1"``,
etc. as arguments for the right thing to happen.

Enhancements
============

STklos
------

STklos_ looks to add a reasonable chunk of the bootstrap in :lname:`C`
(see :file:`src/object.c`).  Whilst it supports the
``compute-apply-generic`` principles (called ``apply-generic`` and
similarly in :file:`lib/object.stk`) the code for actual ``<generic>``
instances is handled in :lname:`C`.  Which seems like a good thing as
the mechanism is quite slow.

Swindle
-------

Swindle extends the initializers to allow for more useful, er,
initialization.

It also supports the wider CLOS-like system of primary methods to
include before, after and around methods.

Problems
========

:lname:`Tiny CLOS` does suffer from some problems.  A search for
:lname:`Swindle` documentation may well end in frustration as
:ref-author:`Eli Barzilay` has disabled access to the
documentation, none of which was transposed into any other form
previously.

He has noted some problems with :lname:`Swindle` and related
technologies in that generic functions have a shared state.  If
there's only you editing code it's not a problem but when one or more
libraries are affecting generic functions and one makes a mistake it
has the potential to take down all the rest.

Both of these are in the first reply in this Reddit thread `Why is
Swindle hidden away?
<https://www.reddit.com/r/Racket/comments/2crihw/why_is_swindle_hidden_away/>`_.

In the follow-up he makes another interesting point:

    The work that I referred to might be possible. I've heard ideas
    about generics that instead of being mutated they're being
    extended, so when you do a defmethod, your own version of the
    generic is extended, but not my version, and therefore such horror
    stories are gone. Doing something like that would be wonderful,
    IMO, but nobody really tried to make it happen.

.. aside::

   Hmm...  *\*scratches chin\**

That's an intriguing idea.  In essence it would require that generic
functions become localized to modules.

.. include:: ../../commit.rst

