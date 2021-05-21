.. include:: ../../global.rst

*********
Functions
*********

We've two types of functions, *primitives* and *closures*, which are
both *abstractions* to encapsulate parameterised behaviour.

*Primitives* are :lname:`C` code which have several broad
categorisations:

#. they are the only things that can manipulate :lname:`C` memory

   Which sounds a bit obvious but at some point it'll get lost.

#. they bootstrap the user-level environment

   Quite a lot of the bootstrap code is then wrappered with more
   exotic forms of the same thing.  This is partly because doing
   anything complicated in :lname:`C` gets a bit awkward.

#. they are quick

   Again, it sounds a bit obvious but after writing your glorious
   :lname:`Idio` function you might just have to bite the bullet and
   write a :lname:`C` version to get any performance.

#. they are our interface to another world

   Whether that is system calls or inter-language calls.

*Closures* are :lname:`Idio` code.

The VM has to be able to cope with both types of functions as
invocable things but there is an interesting reality-warping
difference: *primitives* are instantaneous (mostly).  So far as the VM
is concerned, the moment a *primitive* is called the answer is back in
its hands.

.. _primitives:

Primitives
==========

Primitives are far harder to conceptualise and implement.  So we'll
start with them.

VM Usage
--------

Rather than working from the bottom up let's ask the question, what
does the VM need?

Well, it'll want to know this is a primitive, we'll need a pointer to
the :lname:`C` function, we'll need to know how many formal parameters
it is expecting and whether it is expecting a variable number of
parameters, over and above the formal parameters.

And we can probably chuck in a :lname:`C` string for a name:

.. code-block:: c
   :caption: gc.h

   typedef struct idio_primitive_s {
       struct idio_s *grey;
       struct idio_s *(*f) ();		 /* don't declare args */
       char *name;
       uint8_t arity;
       char varargs;
   } idio_primitive_t;

   #define IDIO_PRIMITIVE_GREY(P)       ((P)->u.primitive->grey)
   #define IDIO_PRIMITIVE_F(P)          ((P)->u.primitive->f)
   #define IDIO_PRIMITIVE_NAME(P)       ((P)->u.primitive->name)
   #define IDIO_PRIMITIVE_ARITY(P)      ((P)->u.primitive->arity)
   #define IDIO_PRIMITIVE_VARARGS(P)    ((P)->u.primitive->varargs)

As the comment notes, we don't declare any arguments for the
:lname:`C` function pointer as that will vary from primitive to
primitive.

I've limited the number of formal parameters, ``arity``, to 255.  That
*should* be OK for most people.  In practice, you need to edit
``idio_vm_invoke()`` in :file:`vm.c` to have more than five formal
parameters.

``varargs`` is a boolean and could, perhaps, should, be a
type-specific flag.  *\*shrugs\**

I've skipped how one of these is created.  That's a complication we
can come back to.

.. rst-class:: center

\*

The actual function *call* needs to gather together the arguments to
be able to say, broadly, for a binary function:

.. parsed-literal::
   :name: ``idio_vm_invoke()`` in :file:`vm.c`

   result = (IDIO_PRIMITIVE_F (prim)) (*arg1*, *arg2*, *args*);

The arguments will have been marshalled up by the VM ready for a
generic function call, actually, marshalled up for a *closure* call.
For a *primitive* we have to un-marshall them with :samp:`{args}`
being the remaining arguments beyond the formal ones.

:socrates:`Wait!  What happened with varargs?` Ah, dirty secret time,
*all* functions, *closures* and *primitives*, are *always* called with
varargs arguments.  The ``varargs`` field is used to syntactically
verify the call point, *not* the invocation.

*Bah!* Even that's not true.  Fixed argument primitives are encoded
such that they can be called directly by the VM with just their fixed
argument, er, arguments.  Varargs primitives go through the full
function call interface (marshalled arguments and all).

:lname:`C` Construction
-----------------------

This is a good deal more involved.

We have an idea of what the VM wants, now we need to construct a
primitive.

Obviously we need to write the actual code (*duh!*) but we
simultaneously need to record the primitive's *pointer*, *arity*,
*varargs* and *name* -- and that's just for the VM.  We might also
want to record meta-information like the primitive's *signature* and
*documentation string*.

    I like the idea of some sort of `Type Inference
    <https://en.wikipedia.org/wiki/Type_inference>`_ in which case it
    is a requirement that the primitive functions fully declare their
    parameter and return types.  This is to bootstrap the whole type
    inference system.

    More *stuff* to record!

That sort of data, describing the primitive, looks like:

.. code-block:: c
   :caption: gc.h

   typedef struct idio_primitive_desc_s {
       struct idio_s *(*f) ();
       char *name;
       uint8_t arity;
       char varargs;
       char *sigstr;
       char *docstr;
   } idio_primitive_desc_t;


To make that recording happen I've cobbled together some increasingly
complex :lname:`C` macros which require the developer to be on song.

When a primitive function is written we won't use a stock :lname:`C`
function signature, instead we'll use a macro.  So, rather than:

.. code-block:: c

   IDIO idio_pair_primitive (IDIO h, IDIO t)
   {
       return idio_pair (h, t);		/* the actual constructor */
   }

we use (in its simplest form):

.. code-block:: c

   IDIO_DEFINE_PRIMITIVE2 ("pair", pair, (IDIO h, IDIO t))
   {
       return idio_pair (h, t);
   }

Let's break this down:

* ``IDIO_DEFINE_PRIMITIVE2``, from :file:`idio.h`, says I'm defining a
  primitive that takes 2 formal parameters.

  ``IDIO_DEFINE_PRIMITIVE2V`` says two formal parameters and varargs.

  (You can guess the rest of the variations.  Hopefully.)

* ``"pair"`` is the :lname:`C` string name which will become the
  function's :lname:`Idio` name

  In this case, I can expect to find an :lname:`Idio` function called
  ``pair``:

  .. code-block:: idio-console

     Idio> pair
     #<PRIM pair>

* ``pair`` is the :lname:`C` function name snippet that will be
  prefixed with ``idio_defprimitive_``

  Clearly, it should be unique amongst all other primitives which, if
  you keep it trivially aligned with the function's :lname:`Idio` name
  should be OK.

  Notice that this newly created :lname:`C` function,
  ``idio_defprimitive_pair`` does not now clash with the pair
  constructor, ``idio_pair``.  It's hardly in a separate namespace but
  so long as developers don't call their regular :lname:`C` functions
  :samp:`idio_defprimitive_{name}` then we're pretty safe.

* ``(IDIO h, IDIO t)`` is the formal parameter list to the :lname:`C`
  function.

:samp:`IDIO_DEFINE_PRIMITIVE{x}` do two key things:

#. create a ``static`` primitive function description structure for
   use later

#. prefix the actual function code with an appropriate header

In combination, that means:

.. code-block:: c

   IDIO_DEFINE_PRIMITIVE2 ("foo-idio", foo_C, (T1 a1, T2 a2))
   {
     ...
   }
		
will expand to:

.. code-block:: c

   IDIO idio_defprimitive_foo_C (T1 a1, T2 a2);
   static struct idio_primitive_desc_s idio_primitive_data_foo_C = {
      idio_defprimitive_foo_C,
      "foo-idio",
      2,
      0,
      "",
      ""
   };
   IDIO idio_defprimitive_foo_C (T1 a1, T2 a2)
   {
     ...
   }

which looks pretty promising.

The next variants have a ``_DS`` suffix meaning they expect a
*signature string* and a *documentation string*.

The two strings are used when constructing user-friendly information
for help and debugging.

The signature string for a closure is, in essence, the formal
parameter list and so it should be similar for a primitive.  This is
straightforward for non-varargs functions, like ``pair`` where the
signature string can be just ``h t``.

For varargs functions, the interpretation varies considerably.  For
some functions the varargs might be "more of the same" but for others
it might be optional parameters, like with ``display`` which takes a
formal parameter, the value to be displayed, and an optional argument,
encoded as varargs, for the *handle* to display to.  If no handle is
passed, it defaults to the *current output handle*.

I'd lean towards a signature string of ``v [handle]`` but this ability
to be more specific about the meaning of varargs parameters is
inconsistent with closures which can only report ``v & args`` from the
formal parameters.  *Dunno.*

The documentation string is for use with ``help`` where it will get
printed out.  I have this fanciful idea that the documentation string
might be processed by, say, :program:`rst2txt` (ReStructuredText to
text) and so I've encoded most documentation strings with that in
mind.  What I haven't done is made any progress in doing the
processing.

The actual ``pair`` PRIMITIVE looks like:

.. code-block:: c

   IDIO_DEFINE_PRIMITIVE2_DS ("pair", pair, (IDIO h, IDIO t), "h t", "\
   create a `pair` from `h` and `t`	\n\
   ")
   {
       IDIO_ASSERT (h);
       IDIO_ASSERT (t);

       return idio_pair (h, t);
   }

Note the assertions of the parameters being passed in.  The only
difference is that we've filled in the ``sigstr`` and ``docstr``
fields.

You can immediately guess that the non-``_DS`` variants simply call
the ``_DS`` variants with ``""`` for the signature and documentation
strings.

.. rst-class:: center

\*

So far, then, we've organised to create a static instance of a
``struct idio_primitive_desc_s`` and defined a :lname:`C` function.
We need to do something with it otherwise the pair of them will just
hang about in the executable doing nothing useful as no-one knows to
call them.

That requires an explicit use the of primitive's description structure
although we don't need to know anything about that directly, we just
need to know the :lname:`C` function name snippet and we can work out
the rest from there.

You may recall all of the :file:`.c` files relating to types have a
similar bootstrap structure including:

.. code-block:: c

   void idio_pair_add_primitives ()
   {
   }

into which we need to "add" our primitive:

.. code-block:: c

   void idio_pair_add_primitives ()
   {
       IDIO_ADD_PRIMITIVE (pair);
   }

:samp:`IDIO_ADD_PRIMITIVE(pair)` is another :lname:`C` macro which
expands into:

.. code-block:: c

   void idio_pair_add_primitives ()
   {
       idio_add_primitive (&idio_primitive_data_pair,
			   idio_vm_constants,
			   __FILE__,
			   __LINE__);
   }

and ``idio_add_primitive()`` does the dirty business of adding a new
symbol (derived from the :lname:`C` string :samp:`{name}`) and have it
reference the ``idio_primitive_t`` (itself constructed from the
``struct idio_primitive_desc_s``).

In principle, this arrangement allows us to construct a primitive
function "manually" as separate from the above sequence of "automated"
construction.  That said, I have yet to create a primitive manually so
this dance through a static object feels like a bit of a waste.

That's it.  For primitives, then, we have a two-step shimmy, a
:lname:`C` macro at the start of the function's implementation and
another macro to add it into the :lname:`Idio` engine.

.. rst-class:: center

---

There are, of course, a few variations on the theme.  Normally,
primitives are added to the ``*primitives*`` module and implicitly
exported from that module.  However, we might want to add a primitive
to another module.

:samp:`libc` is a module wrappering a number of :lname:`libc` system
calls where the result is useful as an :lname:`Idio` value (and thus
requires some data representation transmutation).  :lname:`libc`'s
systems call names frequently clash with "normal" :lname:`Idio` usage
-- ``read`` is our canonical example.  So, here, we want to add the
primitive to a different module (:samp:`libc` rather than
:samp:`*primitives*`).

Separately, we might want to export that primitive from the module.
Indeed, all of the primitives in :samp:`libc` are exported.  By
exporting the name we can call it "long-hand" from elsewhere:

.. code-block:: idio

   libc/getrlimit libc/RLIMIT_NOFILE

If ``getrlimit`` (and ``RLIMIT_NOFILE``) was not exported from
:samp:`libc` then the above call would fail.

For what it's worth, :manpage:`getrlimit(2)` will update a :lname:`C`
``struct rlimit``.  For us, the ``getrlimit`` primitive has then
transcribed the results into an :lname:`Idio` ``struct-rlimit`` with a
couple of familiar looking fields:

.. code-block:: idio-console
		
   #<SI struct-rlimit rlim_cur:1024 rlim_max:524288>

Had we stored the result in a variable and quizzed the (simplistic)
help system it would have told us a bit more about the structure
instance:

.. code-block:: idio-console

   Idio> x := libc/getrlimit libc/RLIMIT_NOFILE
   #<SI struct-rlimit rlim_cur:1024 rlim_max:524288>
   Idio> help x
   struct-instance: x 

   struct-type: struct-rlimit 

   fields (rlim_cur rlim_max)


Closures
========

Closures are a bit more tricky to describe without knowing how the VM
works.  But let's give it a go.

In essence, a closure needs two things:

* some code (*duh!*)

* an *environment* within which that code is run -- from which we
  access the *free variables* (non-lexical variables) in the function

In our case we have compiled our code for a *byte compiler* which
means everything is a bit more like assembly language programming and
the *code* becomes a *program counter* (PC) such that we jump to that
*PC* and keep processing.

The *environment*, here, is the combination of the lexical context at
the point of creation and the module the closure was created in.
Remember that many closures are created with the intent of managing
private variables.  It is quite unlike, say, :lname:`C`.

Documentation
-------------

Like `Emacs Lisp
<https://www.gnu.org/software/emacs/manual/html_node/elisp/>`_ we
should allow the user to write a documentation string for their
function which should be the third argument of four: :samp:`function
{formals} {docstr} {body}` or :samp:`define ({name} {formals})
{docstr} {body}`.

If there are only three arguments then the :samp:`{body}` takes
precedence -- if all you want is for your function to return a string
then that seems legitimate.

The use of :samp:`{docstr}` will need to adhere to our "single line"
reader processing -- which is partly why strings are allowed to be
multi-line.  So we'll have something like:

.. code-block:: idio
   :caption: common.idio

   define (atom? x) "predicate to test if object is an atom

   :param x: object to test" {
     not (pair? x)
   }

Notice how the multi-line documentation string continues the "single
line" from the end of the declaration through to the start of the body
form.

At the moment the documentation string is not processed though I would
expect some ReStructuredText-style formatting to handle parameter
definitions and cross-references.

Implementation
--------------

Like primitives there is a two-step process to manipulating closures.
We need to create one and then use it.

The data we need for a closure looks like:

.. code-block:: c
   :caption: gc.h

   typedef struct idio_closure_s {
       struct idio_s *grey;
       size_t code_pc;
       size_t code_len;
       struct idio_s *frame;
       struct idio_s *env;
   } idio_closure_t;

   #define IDIO_CLOSURE_GREY(C)       ((C)->u.closure->grey)
   #define IDIO_CLOSURE_CODE_PC(C)    ((C)->u.closure->code_pc)
   #define IDIO_CLOSURE_CODE_LEN(C)   ((C)->u.closure->code_len)
   #define IDIO_CLOSURE_FRAME(C)      ((C)->u.closure->frame)
   #define IDIO_CLOSURE_ENV(C)        ((C)->u.closure->env)
	     
Let's take a look:

* ``code_pc`` is the *program counter* for this closure

  It is a ``size_t`` because it is in index into the byte array of
  compiled code.

* ``code_len`` is, not surprisingly, the length of the byte compiled
  code for this closure

  It's not really used in anger but turns out to be quite handy if you
  want to disassemble the code for just one closure (otherwise the
  disassembler doesn't know when to stop).

* ``frame`` is a reference to the lexical context

* ``env`` is a reference to the module the closure was created in

The *frame* and *env* require a little more explanation.  When we
*run* a closure, in our mind's eye we look at the source code and can
see two things:

#. the lexical environment -- which the closure body may or may not
   use

#. the arguments passed into the function by the calling code

Let's try an about-as-complicated-as-it-gets example.  Here in module
``foo`` we create a function ``f`` which uses both "top level"
variables from module ``foo`` as well as lexical variables defined
outside of the function as well as the parameters passed in:

.. code-block:: idio
   :caption: file :file:`foo.idio`

   module foo
   export (f)

   ; top level variable in *foo*
   this := 1

   f = {

     ; lexical variable only visible inside this block
     that := 2

     function (the-other) {
       + this that the-other
     }
   }

and

.. code-block:: idio
   :caption: file :file:`bar.idio`

   module bar
   import foo

   n := 3

   ; call the "remote" function
   f n

We have a reasonable feeling that the result of calling ``f 3`` in
module ``bar`` should be 6.

But wait!  These two sets of information are disjoint.  We have a set
of lexical information which we can see by looking at the source that
is defined in :file:`foo.idio` and therefore the closure must have
access to it and *at the same time* we have this set of parameters
being passed in from who knows where (:file:`bar.idio`).  How does
that external information get linked in with our local lexical
information?

Well, that's the nature of a linked list of frames of parameters.  At
the time of creation of the closure we stash the current linked list
of frames -- which will be all the parameters leading up to the
definition of the closure in the source code -- *in* the closure
structure, the ``frame`` field.

The protocol is that when someone is due to invoke a closure they will
construct a frame and fill it with the evaluated (or unevaluated for
templates!) values and leave it in the *val* register.

The act of invocation does a sequence of *frame*\ y things:

#. it stashes the current frame (of the caller) on the stack

#. it replaces the current frame with the stored frame of the closure,
   the original lexical environment of the closure

#. it calls the closure:

   #. the very first thing the closure does is verify the arity is
      correct by checking the number of args in the frame in *val*

   #. the next thing it does is link the frame in *val* into the
      current frame (for the function defined in :file:`foo.idio`)
      which we just swapped with the original lexical environment
      frame (from the call point in :file:`bar.idio`)

      At this point, the frame tree looks like the values from the
      caller in the top-most frame and then everything the closure saw
      at the point of its definition:

      .. code-block:: text

	 frame 0: [ 3 ]		; from the call in bar
	 frame 1: [ {that} ]	; from the block in foo
	 frame 2: #n		; no other frames! {this} is in *env*

   #. at some point the closure has computed a value and left it in
      *val* and ``RETURN``\ s

#. the calling code's frame is restored from the stack

   At this point we are exactly as before the call to the closure
   except we have had the frame of evaluated arguments in *val*
   replaced with the computed result of the closure.

Having said all that about the *frame*, we can repeat it in kind for
*env*, the "top-level" environment that the closure was defined in:

#. stash the caller's top-level *env* on the stack

#. it replaces the current env with the stored env of the closure, the
   original lexical top-level of the closure

#. it calls the closure

   Now we can find :samp:`{this}` in the environment of the function
   ``f`` defined in module ``foo``.

   In fact the (stored) environment is just the name of the
   environment at the time of definition, ie. ``foo`` in this case.
   That variables defined in this environment are an attribute of the
   module.

   So, even though ``f`` was called in ``bar``, because ``f`` was
   defined in ``foo`` the current environment is toggled to ``foo``
   and we can (successfully) find :samp:`{this}` in the known
   variables of ``foo`` -- even though the call is "live" in ``bar``.

#. the calling code's *env* is restored from the stack

Creation
^^^^^^^^

Creating a closure is a little bit of art.  In the first instance, we
don't have to but we will encode the *creation* of the closure as well
as the code for the *implementation* of the closure in the output byte
code.  Subsequently, we have a generated code stream that means if we
could store the byte code out as a loadable module then we have the
creation code embedded in it.

When we hit a function abstraction:

.. code-block:: idio

   function (a b) {
       a + b
   }

we have two things:

* a function prototype: this example takes two formal parameters and
  no varargs

* the function implementation or body

In addition we have the lexical context (we *should* have the lexical
context, *we're* doing the evaluation!) and the current module.

In combination we have everything we require to satisfy the need to
create a closure.  Remember, though, with a function declaration,
we're only looking to define the function, not run it, so:

.. code-block:: idio

   x := 1
   define (y a b) {
       a + b
   }
   z := x + 1

is the pseudo-code:

.. parsed-literal::

   define :samp:`{x}` as the result of evaluating :samp:`1`

   define :samp:`{y}` as the result of evaluation the function definition
   :samp:`function (a b) \\{ a + b }` into a closure value

   define :samp:`{z}` as the result of evaluating :samp:`{x} + 1`

In other words, we're not *running* the function during this process,
just establishing it as something that can be run.

A *closure value* is, from the data structure above, a program
counter, a code length, a future frame (of arguments) and a pointer to
an environment.

The process is:

#. we'll create the code for the body in a temporary array

   From that we can calculate the ``code_len``.

   Actually, the body:

   * is prefaced with an arity check and something to link the
     argument frames

   * has a ``RETURN`` instruction tacked on the end

   but that's by the by.

#. in the normal byte code array we'll add the ``CREATE-CLOSURE``
   instruction which requires an *offset* to the ``code_pc`` (which
   will be after the upcoming ``JUMP`` instruction)

   plus some standard fields:

   * the code length

   * a reference to the signature string

   * a reference to the document string

   All of which we will need to be able to construct the ``struct
   idio_closure_s``.

#. since we are only *creating* the closure, we don't want to run it
   right now, we'll add a ``JUMP`` instruction followed by the code
   length (again) so that we (during creation) jump over the function
   body.

   This means that when this creation code is *run*, we'll see:

   a. ``CREATE-CLOSURE`` with a ``code_pc`` (and its three arguments:
      code length, signature string and documentation string) then a

   #. ``JUMP`` to *beyond the end of the body*

   #. the definition of :samp:`{z}` in the example, above.

   The ``CREATE-CLOSURE`` has been given the *offset* to the
   ``code_pc`` and can create the closure value.  *Neat!*

   However we do it, we want to jump over the function body so as not
   to run it.

#. We can now copy the function body from the temporary array

   The first byte of which (now in the normal byte code array) is
   ``code_pc``.

   But wait, this is now an *unknown* number of bytes beyond the
   ``CREATE-CLOSURE`` instruction because we're not sure how many
   bytes it took to encode the ``JUMP`` instruction.  How do we
   determine what *offset* should have been?

   Of course, the answer is that we're *expecting* this to happen, so
   made sure to look at the code length and figure out that either:

   a. it is a short jump in which case the jump length is encoded in a
      byte and the overall *offset* is two bytes (including one for
      the jump instruction)

   #. it is a long jump in which case we encode the jump length in
      (yet another) temporary byte code array and can say that the
      *offset* is one plus the length of this temporary array -- plus
      one because the jump instruction takes one byte!

   The code generator can now add the correct *offset* to the
   ``code_pc`` after the ``CREATE-CLOSURE`` instruction.

Another way of looking at it is this abstraction of the generated byte
code:

.. code-block:: text
   :linenos:

   ...
   CREATE-CLOSURE (length of #3) sigstr docstr
   JUMP to #5
   function body (including a trailing RETURN)
   ...

When we come to *run* the closure, the closure value has had
``code_pc`` set to ``#4`` and will stop processing before it hits
``#5`` -- the definition of :samp:`{z}` -- because it has a ``RETURN``
statement stamped on the end.

Operations
==========

:samp:`function? {value}`

      is :samp:`{value}` a function, ie. a primitive or a closure


.. include:: ../../commit.rst

