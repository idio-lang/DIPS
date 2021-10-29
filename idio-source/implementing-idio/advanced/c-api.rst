.. include:: ../../global.rst

.. _`C-api`:

*******
C API
*******

Rationale
=========

:lname:`Idio` is written in :lname:`C` and therefore uses "the"
:lname:`C` API.  So what's the problem?

The problem comes in the form of portability.  Let's say I want to
call and use the result of :manpage:`getpid(2)`.  Easy enough, it's:

.. aside::  No flies on us!

.. code-block:: c

   pid_t pid = getpid ();

OK.  Now I need to store this ``pid_t`` to be able to pass it around
as an ``IDIO`` value.  And a ``pid_t`` is a what, exactly, on your
system?  I have access to systems where it is either an ``int`` or a
``long`` (which doesn't tell me if an ``int`` differs from a ``long``
anyway).  So, er, which one?

Another slightly more famous example is a ``time_t``.  It was (and
still will be in some cases) a 32-bit entity resulting in the
impending `Epochalypse
<https://www.linaro.org/blog/the-end-of-an-era/>`_ in January 2038.
Except every modern Linux operating system doesn't have that problem
as Arnd Bergmann and John Stultz plodded though and changed the
interfaces to 64-bit (kicking the Epochalyse can down the road for `a
few hundred billion years
<https://en.wikipedia.org/wiki/Time_formatting_and_storage_bugs#Year_292,277,026,596_problem>`_...).

And, another bugbear, how do I print a ``time_t`` out without
upsetting the compiler on some system or another?

Underlying this is that the :lname:`C` API uses an opaque *typedef*
for some base :lname:`C` type.  For us to be able to store and
transport it we could do with knowing what that type is.

In the first instance, we might just use ``intmax_t`` and
``uintmax_t`` (whatever *they* are) to store all :lname:`C` integral
types and let the :lname:`C` compiler figure out the casting.  But
that doesn't seem like *Art*.  Not least because we *still* don't know
if a ``pid_t`` or a ``time_t`` is signed or unsigned -- OK, we can
take a look/reasonable guess and hope that everyone else uses the
same.

Instead, wouldn't it be useful if we could write code that looked
like:

.. code-block:: c

   pid_t pid = getpid ();
   IDIO ipid = idio_C_pid_t (pid);

where the ``idio_C_pid_t`` constructor is aware of whatever underlying
base type a ``pid_t`` is on *this* system and stashes it as an ``int``
or ``long`` as appropriate.

Now that the value is an ``IDIO`` value we can pass it merrily around
to anyone else.  The only people who will actually care whether it is
an ``int`` or a ``long`` are those manipulating it and they would want
a deconstructor, ``IDIO_C_TYPE_pid_t``, that is equally aware of the
stash leaving us to write:

.. code-block:: c

   void idio_func (IDIO v)
   {
       IDIO_USER_C_TYPE_ASSERT (pid_t, v);

       pid_t pid = IDIO_C_TYPE_pid_t (v);
       ...
   }

where the type assertion knows the mapping from ``pid_t`` to ``int``
or ``long`` as well.

Conversions
-----------

Hmm, wait a minute, what if *we* in :lname:`Idio`\ -land want to
create a ``pid_t``?  Suppose we've read in the output of :program:`ps`
and decide we need to :manpage:`kill(2)` some egregious process?
We'll have started with some string which we can convert into an
:lname:`Idio` number with ``read-number`` but we, probably, don't even
know if that number is even a fixnum or a bignum.  How are we going to
create a ``pid_t``?

We do have ``C/integer->`` to help us which can be given a clue as to
which :lname:`C` type to create.

So, we need to pass it some clue as to which of the fourteen
:lname:`C` base types we want.  Obviously, we're going to pass it
``pid_t`` -- because that's *all* we want to know about this value --
which needs to map to some symbol (the usual :lname:`Scheme`\ -ish
way) which eventually resolves to either ``'int`` or ``'long``
dependent on system.

.. code-block:: idio-console

   Idio> C/integer-> 23 libc/pid_t
   23

.. aside::

   I don't think the :lname:`C` compiler would cope with two typedefs
   of ``pid_t`` so maybe we should have a flat namespace (here, just
   ``pid_t``) as well.

   However, see the commentary in :ref:`namespaces`, below.

In practice, ``pid_t`` is really ``libc/pid_t``, ie. to accommodate
different libraries' potential name clashes we'll prefix the typedef
name with the module the name comes from.

Those names are exported from ``libc`` but so are many many other
names with a huge potential for clashes:

.. code-block:: idio

   import libc

can be interesting.

Also notice that the printed representation of a :lname:`C` ``pid_t``
is, perhaps unsurprisingly, indistinguishable from the fixnum we
constructed it from!  I'm not sure there's a useful solution to this.

There is the similar ``C/->integer`` which will return an
:lname:`Idio` fixnum or bignum (depending on the size of the
:lname:`C` value).  On a 64-bit machine:

.. code-block:: idio-console

   Idio> fixnum? (C/->integer libc/INT_MAX)
   #t
   Idio> fixnum? (C/->integer libc/INTMAX_MAX)
   #f

On a 32-bit system, ``libc/INT_MAX`` is also a bignum.

Predicates
----------

In the same manner any ``libc``-oriented code will want to be able to
test that some :lname:`Idio` value is a ``libc/pid_t``.  That
predicate should, by rights, be ``libc/pid_t?``.

Given that ``pid_t`` is a typedef to ``int`` (or ``long`` or whatever)
then we're going to need a mapping from ``libc/pid_t?`` through to the
:lname:`C` domain's ``C/int?`` or ``C/long?`` as appropriate.

Note that the change, arguably, *chain*, from a :lname:`C` library
(ie. :lname:`Idio` module) into the :lname:`C` domain's (fourteen)
base types might well involve some multi-library hops depending on how
the typedefs roll.

Caveats
=======

The main caveat is that if your interface uses ``#define`` then this
mechanism won't help you.  ``#define``\ s are part of the :lname:`C`
pre-processor and so those definitions will have disappeared by the
time the :lname:`C` compiler has its way and we get to look at the
generated code.

Another issue is that the set of values that some parameters take
might be system-dependent.  Think of the ``resource`` parameter to
:manpage:`getrlimit(2)`, the likes of ``RLIMIT_NOFILE``,
``RLIMIT_NPROC`` etc..  On the one hand that ought not be an issue
except that it presumes we do, somehow, know what values have been
defined on this system.  Some Linux systems have migrated these values
into an enumerated type, which we can see, and maintained the
:lname:`C` macros for backwards compatibility.  Other systems are
``#define`` only.

For these to be portable you will have to resort to using something
along the lines of the error, signal and rlimit value tests:

.. code-block:: c
   :caption: :file:`src/libc-wrap.c`

   #if defined (EBADF)
       IDIO_LIBC_ERRNO (EBADF);
   #endif

and empirical knowledge of the ported systems.

.. _namespaces: 

Namespaces
==========

I started out distinguishing between the base :lname:`C` types in the
existing ``C`` namespace and those new typedefs being introduced from
libc in the ``libc`` namespace before thinking that :lname:`C` doesn't
have any namespaces, what am I doing?

However, :lname:`C++` does have namespaces so I guess it would be
prudent to maintain this artiface.

This will lead to the mildly confusing ``idio_libc_pid_t`` constructor
and some :samp:`idio_{libfoo}_pid_t` constructor from some
:samp:`{libfoo}` API which also happens to use a ``pid_t`` in its
interface.

So, to correct the earlier names, the proper convention is that for
true :lname:`C` domain types (``int``, ``long`` etc.) we'll use:

.. code-block:: c

   IDIO_USER_C_TYPE_ASSERT ({base-type}, v);

   {base-type} C_v = IDIO_C_TYPE_{base-type} (v);

   IDIO r = idio_C_{base-type} (C_v);

and for some :samp:`{libfoo}` API using a typedef'd symbol we'll have:

.. code-block:: c

   IDIO_USER_{libfoo}_TYPE_ASSERT ({type-def}, v);

   {type-def} C_v = IDIO_{libfoo}_{type-def} (v);

   IDIO r = idio_{libfoo}_{type-def} (C_v);

therefore, for the ``pid_t`` in ``libc`` example, we'll have:

.. code-block:: c

   IDIO_USER_libc_TYPE_ASSERT (pid_t, v);

   pid_t C_v = IDIO_libc_pid_t (v);

   IDIO r = idio_libc_pid_t (C_v);

Build Bootstrap I
=================

We'll come back to this but :lname:`Idio` uses the :lname:`C` API for
:file:`libc` to run and yet we're somehow using :lname:`Idio` to
*build* that :file:`libc` interface.  How does *that* work?

.. aside::

   "Cheat" is a very loaded term.  Of course we mean that we use our
   experience, wisdom and guile buried under a weight of fortune...

Well, we cheat, of course.  In the first instance there are some
:file:`libc` API files that are at least consistent, if not
necessarily correct for this system, these are in
:file:`build-bootstrap` subdirectories.

That is enough to allow us to run :program:`idio-c-api-gen` to build
correct :file:`libc` API files for this system.  The presence of which
prompts :program:`make` to rebuild :program:`idio`.

DWARF
=====

.. sidebox::

   DWARF was originally a `play on words
   <http://wiki.dwarfstd.org/index.php?title=DWARF_FAQ#Why_is_it_called_DWARF.3F_And_why_isn.27t_it_spelled_.22Dwarf.22.3F>`_
   given its relationship to ELF, the Executable and Linking Format
   for object files but later backronym'ed to...well, who cares?

`DWARF <http://dwarfstd.org/>`_ is our friend, here.  One observation
is that the debugger seems to know a lot about the types in our system
and if we investigate the output of a "debug" object file it turns out
to contain a lot of information about the types in the object file.

But, as noted, nothing from the :lname:`C` pre-processor.

.. sidebox::

    :program:`readelf` is not available on Mac OS X -- noting, in
    turn, that :program:`objdump` on Mac OS X is rubbish and you need
    to run :program:`dwarfdump` to get anything useful.

:program:`objdump` seems to exist on all the systems I use which
produces a wealth of information in text format.  Given we'll have to
parse something, text format seems a lot easier for us.

DIEs
----

The output is in the form of cascades of :abbr:`DIE (Debugging
Information Entry)`\ s.  These look something like:

.. code-block:: text

    <1><50>: Abbrev Number: 2 (DW_TAG_base_type)
       <51>   DW_AT_byte_size   : 2
       <52>   DW_AT_encoding    : 5        (signed)
       <53>   DW_AT_name        : (indirect string, offset: 0x9c4): short int
    <1><57>: Abbrev Number: 3 (DW_TAG_base_type)
       <58>   DW_AT_byte_size   : 4
       <59>   DW_AT_encoding    : 5        (signed)
       <5a>   DW_AT_name        : int

The output varies with:

* the (historic) version of :program:`objdump` changes the exact format

* the set of entries is dependent on the types used in the object file (duh!)

* the *order* of output varies on the contents of the object file

However, reading between the lines we can see there appear to be two
``base_type``\ s defined in that snippet:

* a ``short int`` with a ``byte_size`` of 2 is type ``<50>``

* an ``int`` with a ``byte_size`` of 4 is type ``<57>``

The sizes seem about right for this system for a start!

The ``encoding`` attribute is interesting as it is a clue as to how to
interpret those 2 or 4 bytes.  ``signed``, ``signed char``,
``unsigned`` and ``float`` are examples.  I don't think in :lname:`C`
there's really very much going on, here, but I get the impression that
the ``encoding`` allows for much more like the
``UTF-8``/``UCS-2``\ -style of encoding.

.. note::

   A DIE without a type uses the implied type of ``void``.

pid_t
^^^^^

Let's try a ``pid_t``:

.. code-block:: c
   :caption: :file:`src/libc-api.c`

   int main (int argc, char ** argv)
   {
       pid_t pid = getpid ();

       return 0;
   }

which compiling, ``gcc -g -c -o libc-api.o libc-api.c`` gives us
(amongst other things):

.. code-block:: text

    <1><57>: Abbrev Number: 3 (DW_TAG_base_type)
       <58>   DW_AT_byte_size   : 4
       <59>   DW_AT_encoding    : 5        (signed)
       <5a>   DW_AT_name        : int

    <1><e9>: Abbrev Number: 4 (DW_TAG_typedef)
       <ea>   DW_AT_name        : (indirect string, offset: 0x7f1): __pid_t
       <ee>   DW_AT_decl_file   : 2
       <ef>   DW_AT_decl_line   : 154
       <f0>   DW_AT_decl_column : 25
       <f1>   DW_AT_type        : <0x57>

    <1><1ea>: Abbrev Number: 4 (DW_TAG_typedef)
       <1eb>   DW_AT_name        : (indirect string, offset: 0x727): pid_t
       <1ef>   DW_AT_decl_file   : 3
       <1f0>   DW_AT_decl_line   : 97
       <1f1>   DW_AT_decl_column : 17
       <1f2>   DW_AT_type        : <0xe9>

The third DIE shown, ``<1ea>`` at the bottom, is a ``typedef`` for
``pid_t`` and has some clues about a file and that its ``type`` is
``<0xe9>``.

The middle DIE shown, is ``<e9>`` which is itself a ``typedef`` for
``__pid_t`` from a different file (you would guess) and in turn has
its type as ``<0x57>``.

The first DIE shown is ``<57>`` and is a ``base_type``, an ``int``.

Sweet!

As noted, another system typedefs ``pid_t`` directly to a ``long int``
base type.

That raises another spectre.  Where has this ``__pid_t`` type come
from and is it portable?

Well, the answer is that it is obviously some local definition and is
clearly not portable so we need to be more careful.  Not only are the
ultimate base types of the typedefs different but the mappings through
to them are different too.

That might come back to bite us, it might not.

.. rst-class:: center

\*

In the meanwhile we can see a means to automatically generate many of
the interfaces we've been talking about, most of which are simply
redefinitions of existing base types.

In the :lname:`C` world, you can imagine creating:

.. code-block:: c
   :caption: :file:`src/libc-api.h`

   #define IDIO_TYPE_C_libc___pid_t            IDIO_TYPE_C_INT
   #define idio_libc___pid_t                   idio_C_int
   #define IDIO_C_TYPE_libc___pid_t            IDIO_C_TYPE_int
   #define idio_isa_libc___pid_t               idio_isa_C_int

   #define IDIO_TYPE_C_libc_pid_t              IDIO_TYPE_C_libc___pid_t
   #define idio_libc_pid_t                     idio_libc___pid_t
   #define IDIO_C_TYPE_libc_pid_t              IDIO_C_TYPE_libc___pid_t
   #define idio_isa_libc_pid_t                 idio_isa_libc___pid_t

Here,

* :samp:`IDIO_TYPE_C_{module}_{name}` is a mapping from the :lname:`C`
  constructed name to an :lname:`Idio` :file:`src/gc.h` compatible
  macro for the :lname:`C` base types

  This allows us to figure out the correct :manpage:`printf(3)` format
  string for a given type.

* :samp:`idio_{module}_{name}` is the constructor

* :samp:`IDIO_C_TYPE_{module}_{name}` is the destructor

  An unfortunate naming near-miss with
  :samp:`IDIO_TYPE_C_{module}_{name}`.

* :samp:`idio_isa_{module}_{name}` is a predicate

The :samp:`IDIO_USER_{module}_TYPE_ASSERT({type},{x})` is a generic
macro which ultimately is going to call
:samp:`idio_isa_{module}_{type} ({x})` which we've just defined.

and for the :lname:`Idio` world:

.. code-block:: idio
   :caption: :file:`lib/libc-api.idio`

   export (
	   __pid_t
	   __pid_t?

	   pid_t
	   pid_t?
	   )

   __pid_t                            := 'int
   define __pid_t?                       C/int?

   pid_t                              := __pid_t
   define pid_t?                         libc/__pid_t?

Meaning that some :lname:`Idio` code can:

.. code-block:: idio

   pid := ...
   c-pid := C/integer-> pid libc/pid_t

and everything lines up!

Structures and Unions
^^^^^^^^^^^^^^^^^^^^^

Structures and unions are all "lifted" up to the top level, even if
they are only used inside another structure or union.

That said, they are very simple being the ``structure_type`` itself
(with or without a ``name``) and a sequence of ``member``\ s each of
which has a ``type`` in turn.

Hmm, now we know about the fields in a structure, we ought to be able
to generate some code to be able to access the fields.

From :lname:`Idio` you can imagine wanting to access a
:manpage:`stat(2)` ``struct stat`` along the lines of:

.. code-block:: idio

   sb := libc/stat "."
   printf "size=%s\n" sb.st_size

which is utilizing the ``value-index`` operator ``.`` to access the
``st_size`` member using a symbol, ``st_size``.

What do we need for that?  Well, we should define the symbol, for a
start, then we need a function that can poke about in the ``struct
stat``, let's call it ``struct-stat-ref``:

.. code-block:: c

   IDIO_SYMBOL_DECL (st_dev);
   IDIO_SYMBOL_DECL (st_ino);
   ...
   IDIO_SYMBOL_DECL (st_size);
   ...

   IDIO_DEFINE_PRIMITIVE2_DS ("struct-stat-ref", libc_struct_stat_ref, (IDIO stat, IDIO member), "stat member", "\
   in C, stat->member                      \n\
					   \n\
   :param stat: C struct stat      \n\
   :type stat: C/pointer           \n\
   :param member: C struct member          \n\
   :type member: symbol                    \n\
   :return: stat->member           \n\
   :rtype: varies on member                \n\
   ")
   {
       IDIO_ASSERT (stat);
       IDIO_ASSERT (member);

       /*
	* Test Case: libc-errors/struct-stat-ref-bad-pointer-type.idio
	*
	* struct-stat-ref #t #t
	*/
       IDIO_USER_C_TYPE_ASSERT (pointer, stat);
       /*
	* Test Case: libc-errors/struct-stat-ref-bad-member-type.idio
	*
	* struct-stat-ref v #t
	*/
       IDIO_USER_TYPE_ASSERT (symbol, member);

       ... can we check that stat is a pointer to a struct stat?

       struct stat *statp = IDIO_C_TYPE_POINTER_P (stat);
       if (idio_S_st_dev == member) {
	   return idio_libc_dev_t (statp->st_dev);
       } else if (idio_S_st_ino == member) {
       ...
       } else if (idio_S_st_size == member) {
	   return idio_libc_off_t (statp->st_size);
       } else
       ...
   }

We should be able to generate a similar ``struct-stat-set!`` although
whether such a function is warranted is another question.  *a priori*
it's a valid operation.

For the answer to testing whether ``stat`` really is a ``struct
stat``, see :ref:`subprograms`, below.

Separately, though related, there is the question, about how the
system might know that it should use ``struct-stat-ref``, in
particular, when de-structuring some (random) :lname:`C` pointer,
rather than any other primitive (or function).  More on that below.

Pointers
^^^^^^^^

Pointers are flagged en route to the real type underneath.  Here's the
case for the ``formal_parameter`` :samp:`{argv}`:

.. code-block:: text

    <1><178>: Abbrev Number: 9 (DW_TAG_pointer_type)
       <179>   DW_AT_byte_size   : 8
       <17a>   DW_AT_type        : <0x17e>
    <1><17e>: Abbrev Number: 2 (DW_TAG_base_type)
       <17f>   DW_AT_byte_size   : 1
       <180>   DW_AT_encoding    : 6       (signed char)
       <181>   DW_AT_name        : (indirect string, offset: 0x351): char
    <1><2fa>: Abbrev Number: 9 (DW_TAG_pointer_type)
       <2fb>   DW_AT_byte_size   : 8
       <2fc>   DW_AT_type        : <0x178>
    <2><115d>: Abbrev Number: 36 (DW_TAG_formal_parameter)
       <115e>   DW_AT_name        : (indirect string, offset: 0x57b): argv
       <1162>   DW_AT_decl_file   : 1
       <1163>   DW_AT_decl_line   : 55
       <1164>   DW_AT_decl_column : 28
       <1165>   DW_AT_type        : <0x2fa>
       <1169>   DW_AT_location    : 4 byte block: 91 f0 b9 7f      (DW_OP_fbreg: -8976)

Which you should be able to see both that :samp:`{argv}` is a pointer
to a pointer to a ``char``, ie. ``char **argv`` and that DIEs are not
necessarily printed in an obvious order.

Arrays
""""""

Array types are a bit more subtle.  They are described distinctly from
pointers, as they should be, though *we* might use them
indiscriminately from pointers.

In this example, all of the member of the ``struct utsname`` are
``char []`` rather than ``char *``:

.. code-block:: text

    <1><c80>: Abbrev Number: 28 (DW_TAG_structure_type)
       <c81>   DW_AT_name        : (indirect string, offset: 0x1e8): utsname
       <c85>   DW_AT_byte_size   : 390
       <c87>   DW_AT_decl_file   : 23
       <c88>   DW_AT_decl_line   : 48
       <c89>   DW_AT_decl_column : 8
       <c8a>   DW_AT_sibling     : <0xcdf>
    <2><c8e>: Abbrev Number: 12 (DW_TAG_member)
       <c8f>   DW_AT_name        : (indirect string, offset: 0x5e1): sysname
       <c93>   DW_AT_decl_file   : 23
       <c94>   DW_AT_decl_line   : 51
       <c95>   DW_AT_decl_column : 10
       <c96>   DW_AT_type        : <0xcdf>
       <c9a>   DW_AT_data_member_location: 0
    <2><c9b>: Abbrev Number: 12 (DW_TAG_member)
       <c9c>   DW_AT_name        : (indirect string, offset: 0x459): nodename
       <ca0>   DW_AT_decl_file   : 23
       <ca1>   DW_AT_decl_line   : 54
       <ca2>   DW_AT_decl_column : 10
       <ca3>   DW_AT_type        : <0xcdf>
       <ca7>   DW_AT_data_member_location: 65

    <1><cdf>: Abbrev Number: 5 (DW_TAG_array_type)
       <ce0>   DW_AT_type        : <0x17e>
       <ce4>   DW_AT_sibling     : <0xcef>

``<17e>`` was the ``char`` in the pointer example, above.

Notice also, part of the ABI (as opposed to the API) is exposed in
that the ``data_member_location`` for ``nodename`` is 65 bytes along
suggesting that ``sysname`` is defined as ``char sysname[65]`` on this
system.

:manpage:`uname(2)` on this system notes:

    The length of the fields in the struct varies.  Some operating
    systems or libraries use a hardcoded 9 or 33 or 65 or 257.  Other
    systems use SYS_NMLN or _SYS_NMLN or UTSLEN or _UTSNAME_LENGTH.
    Clearly, it is a bad idea to use any of these constants; just use
    sizeof(...).  Often 257 is chosen in order to have room for an
    internet hostname.

Enumerated Types
^^^^^^^^^^^^^^^^

Enumerated types have a ``type`` and a number of ``enumerator``\ s
each of which has a ``const_value``.

.. sidebox::

   "A bit loose"?  How Unusual for :lname:`C`... *not!*

The wording around the type for an enumerated type is a bit loose and
merely suggests something big enough to hold the entire set of
enumerators.

I can see both ``int`` and ``unsigned int`` enumerated types.

.. _subprograms:

Subprograms
^^^^^^^^^^^

I'm not sure what ``subprogram`` is meant to describe but you will
usually get to see ``main`` or whatever the main enclosing function
is.

The information provided includes the formal parameters and any
variables used in the function (possibly including any lexical blocks
they exist in).

.. sidebox::

   Fedora using GCC 10!
   
However, rather usefully, on some systems it will also have a
``subprogram`` entry for each function it calls.

This is strikingly useful as it only requires one system, using
portable definitions, to produce this information from which we can
sketch out the framework for a series of ``IDIO_DEFINE_PRIMITIVE``
functions describing those calls.  Once defined they are, by
definition(?), using the portable :lname:`C` API and are therefore
applicable to all systems.

Due to the absence of debugging information in, in my case, libc,
there's no formal parameter names for the system and library calls I'm
referencing but we do get the formal parameter types and the return
type.  We can obviously invent some arguments names, *arg1*, *arg2*,
etc..

For :manpage:`kill(2)`, whose prototype looks like:

.. code-block:: c

   int kill(pid_t pid, int sig);

this becomes:

.. code-block:: c

   IDIO_DEFINE_PRIMITIVE2_DS ("kill", libc_kill, (IDIO arg1, IDIO arg2), "arg1 arg2", "\
   in C: kill (arg1, arg2)         \n\
   a wrapper to libc kill()                \n\
					   \n\
   :param arg1:                            \n\
   :type arg1: libc/__pid_t                        \n\
   :param arg2:                            \n\
   :type arg2: C/int                       \n\
   :return:
   :rtype: C/int
   ")
   {
       IDIO_ASSERT (arg1);
       IDIO_ASSERT (arg2);

      /*
       * Test Case: libc-errors/kill-bad-arg1-type.idio
       *
       * kill #t #t
       */
       IDIO_USER_libc_TYPE_ASSERT (__pid_t, arg1);
       __pid_t C_arg1 = IDIO_C_TYPE_libc___pid_t (arg1);

      /*
       * Test Case: libc-errors/kill-bad-arg2-type.idio
       *
       * kill #t #t
       */
       IDIO_USER_C_TYPE_ASSERT (int, arg2);
       int C_arg2 = IDIO_C_TYPE_int (arg2);

       int kill_r = kill (C_arg1, C_arg2);

       /* check for errors */
       if (-1 == kill_r) {
	   idio_error_system_errno ("kill", idio_S_nil, IDIO_C_FUNC_LOCATION ());

	   return idio_S_notreached;
       }


       /*
	* WARNING: this is probably an incorrect return
	*/
       return idio_C_int (kill_r);

   }

Now, that's not too shabby for something automatically generated.

.. rst-class:: center

\*

If we *do* install the libc debugging symbols we *still* don't get
``formal_parameter`` names -- well, for the ``subprogram``\s we're interested in,
anyway.

Installing the debugging symbols isn't quite as obvious as you might
think.  In the case of Fedora these are in separate packages in
disabled repos but on the plus side tools like :program:`gdb` know to
go looking for them and programs like :program:`objdump` can be
persuaded with an extra argument (``K`` in this case).

.. code-block:: console

   $ sudo dnf --enablerepo=fedora-debuginfo debuginfo-install glibc-debuginfo
   $ objdump -WilK /lib64/libc-2.33.so

.. code-block:: text

    <1><3452f>: Abbrev Number: 52 (DW_TAG_subprogram)
       <34530>   DW_AT_external    : 1
       <34530>   DW_AT_name        : (indirect string, offset: 0x108c0): kill
       <34534>   DW_AT_decl_file   : 93
       <34535>   DW_AT_decl_line   : 112
       <34536>   DW_AT_decl_column : 12
       <34537>   DW_AT_prototyped  : 1
       <34537>   DW_AT_type        : <0x2a>
       <3453b>   DW_AT_declaration : 1
       <3453b>   DW_AT_sibling     : <0x34547>
    <2><3453c>: Abbrev Number: 24 (DW_TAG_formal_parameter)
       <3453d>   DW_AT_type        : <0x2341>
    <2><34541>: Abbrev Number: 24 (DW_TAG_formal_parameter)
       <34542>   DW_AT_type        : <0x2a>
    <2><34546>: Abbrev Number: 0

Some ``subprogram``\s do have named formal parameters in libc which
makes me think the construction of things might be considerably more
interesting than at first blush.

Wait a minute, isn't there some ``__kill`` nonsense floating about
with system calls?  Hmm.  The ``__kill`` ``subprogram`` also declines
to offer us any formal parameter names.  So let's dig deeper:

.. code-block:: console

   $ sudo dnf --enablerepo=fedora-debuginfo debuginfo-install kernel-debuginfo-$(uname -r)
   $ cd /usr/lib/debug/lib/modules/$(uname -r)
   $ nm vmlinux | grep '[tT] kill_'
   ...
   ffffffff810ecb50 T kill_pgrp
   ffffffff810ecc20 T kill_pid
   ffffffff810ecb90 T kill_pid_info
   ffffffff810ea580 T kill_pid_usb_asyncio
   ffffffff8131ecc0 t kill_procs
   ...

*I don't think we're in Kansas any more, Toto!*

.. code-block:: console

   $ objdump -WilK vmlinux  | less +/kill_pid

.. code-block:: text

    <1><10e9d79>: Abbrev Number: 53 (DW_TAG_subprogram)
       <10e9d7a>   DW_AT_external    : 1
       <10e9d7a>   DW_AT_name        : (indirect string, offset: 0x179603): kill_pid
       <10e9d7e>   DW_AT_decl_file   : 2
       <10e9d7f>   DW_AT_decl_line   : 1793
       <10e9d81>   DW_AT_decl_column : 5
       <10e9d82>   DW_AT_prototyped  : 1
       <10e9d82>   DW_AT_type        : <0x10bcbd0>
       <10e9d86>   DW_AT_low_pc      : 0xffffffff810ecc20
       <10e9d8e>   DW_AT_high_pc     : 0x1a
       <10e9d96>   DW_AT_frame_base  : 1 byte block: 9c    (DW_OP_call_frame_cfa)
       <10e9d98>   DW_AT_GNU_all_call_sites: 1
       <10e9d98>   DW_AT_sibling     : <0x10e9e07>
    <2><10e9d9c>: Abbrev Number: 51 (DW_TAG_formal_parameter)
       <10e9d9d>   DW_AT_name        : pid
       <10e9da1>   DW_AT_decl_file   : 2
       <10e9da2>   DW_AT_decl_line   : 1793
       <10e9da4>   DW_AT_decl_column : 26
       <10e9da5>   DW_AT_type        : <0x10c3638>
       <10e9da9>   DW_AT_location    : 0x3a232c (location list)
       <10e9dad>   DW_AT_GNU_locviews: 0x3a2326
    <2><10e9db1>: Abbrev Number: 51 (DW_TAG_formal_parameter)
       <10e9db2>   DW_AT_name        : sig
       <10e9db6>   DW_AT_decl_file   : 2
       <10e9db7>   DW_AT_decl_line   : 1793
       <10e9db9>   DW_AT_decl_column : 35
       <10e9dba>   DW_AT_type        : <0x10bcbd0>
       <10e9dbe>   DW_AT_location    : 0x3a237e (location list)
       <10e9dc2>   DW_AT_GNU_locviews: 0x3a2378
    <2><10e9dc6>: Abbrev Number: 28 (DW_TAG_formal_parameter)
       <10e9dc7>   DW_AT_name        : (indirect string, offset: 0x3b5017): priv
       <10e9dcb>   DW_AT_decl_file   : 2
       <10e9dcc>   DW_AT_decl_line   : 1793
       <10e9dce>   DW_AT_decl_column : 44
       <10e9dcf>   DW_AT_type        : <0x10bcbd0>
       <10e9dd3>   DW_AT_location    : 0x3a23ce (location list)
       <10e9dd7>   DW_AT_GNU_locviews: 0x3a23ca
    <2><10e9ddb>: Abbrev Number: 90 (DW_TAG_GNU_call_site)
       ...
    <3><10e9e05>: Abbrev Number: 0
    <2><10e9e06>: Abbrev Number: 0

Hmm, *three* parameters.  I think we've gone *too* deep.

So, *query-replace* :samp:`arg{n}` seems fine to me.  We almost
certainly need to tweak the code anyway.

.. rst-class:: center

\*

We have a portability issue as Fedora has defined the API with
``__pid_t`` but if we *query-replaced* the double-underscore we're in
a much better position.

We can obviously query-replace ``arg1`` for ``pid`` and ``arg2`` for
``sig`` leaving us with:

.. code-block:: c

   IDIO_DEFINE_PRIMITIVE2_DS ("kill", libc_kill, (IDIO pid, IDIO sig), "pid sig", "\
   in C: kill (pid, sig)         \n\
   a wrapper to libc kill()                \n\
					   \n\
   :param pid:                            \n\
   :type pid: libc/pid_t                        \n\
   :param sig:                            \n\
   :type sig: C/int                       \n\
   :return:
   :rtype: C/int
   ")
   {
       IDIO_ASSERT (pid);
       IDIO_ASSERT (sig);

      /*
       * Test Case: libc-errors/kill-bad-pid-type.idio
       *
       * kill #t #t
       */
       IDIO_USER_libc_TYPE_ASSERT (pid_t, pid);
       pid_t C_pid = IDIO_C_TYPE_libc_pid_t (pid);

      /*
       * Test Case: libc-errors/kill-bad-sig-type.idio
       *
       * kill #t #t
       */
       IDIO_USER_C_TYPE_ASSERT (int, sig);
       int C_sig = IDIO_C_TYPE_int (sig);

       int kill_r = kill (C_pid, C_sig);

       /* check for errors */
       if (-1 == kill_r) {
	   idio_error_system_errno ("kill", idio_S_nil, IDIO_C_FUNC_LOCATION ());

	   return idio_S_notreached;
       }


       /*
	* WARNING: this is probably an incorrect return
	*/
       return idio_C_int (kill_r);

   }

and we may just have a working, portable, interface to the ``libc``
API!

Re-imagining APIs
-----------------

.. sidebox::

   It does cover a lot of cases, though!

Now, this almost certainly won't work for you `off the bat
<https://en.wiktionary.org/wiki/off_the_bat>`_ as I've clearly
directed the automatic code generation to handle the most common form
of error that system and library calls produce and assumed you can
directly return the value from the API call.

For calls like :manpage:`getcwd(3)` the value returned is a ``char *``
and for error checking we should be comparing to ``NULL``.

For something like :manpage:`times(3)` which is expecting a ``struct
tms`` to be supplied (unlikely from :lname:`Idio`-land!) but also the
returned value is a ``clock_t``.  Here, whilst the "check for errors"
is nominally correct we should be retaining the value and we will end
up returning a list of the ``clock_t`` and the ``struct tms`` back to
the user.

Similarly, a direct copy of the :lname:`C` API is not usefully correct
for something like :manpage:`stat(2)` where the user is in no position
to create a ``struct stat`` to pass as an argument.  In this case we
would only accept a ``pathname`` argument and allocate a ``struct
stat`` to be freed later.

This leads to the idea that the automatic code generation will give us
a starter for ten which we can edit into permanence.

.. _`CSI`:

Auto-Application of Methods
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Now, about that ``struct stat`` we've just allocated.  We've gone to
the trouble of creating ``struct-stat-ref`` (and the moot
``struct-stat-set!``) to manipulate it.  How might we get that to
happen auto-magically?

Well, suppose we associate with the ``C_pointer`` in the ``IDIO``
value we're about to return some useful type information.  What's
useful?  Hmm, how about a couple of things: a string, ``"struct
stat"`` (useful for reporting) and a reference to ``struct-stat-ref``?

In the latter case, we don't need to also add ``struct-stat-set!`` as
we can use our trusty :ref:`setters` mechanism to do the right thing.

We want something that is unique for each type and a ``pair`` always
falls into that category -- even if the contents are the same the
actual ``pair`` itself is unique in memory.

So, at the time we define our structure, let's throw out a "C
Structure Identification":

.. code-block:: c

   IDIO_C_STRUCT_IDENT_DECL (libc_struct_stat);
   IDIO_SYMBOL_DECL (st_dev);
   ...

and then a bit later on, when we're adding primitives etc. we can
expand that into a list:

.. code-block:: c

    IDIO fgvi = IDIO_EXPORT_MODULE_PRIMITIVE (idio_libc_module, libc_struct_stat_ref);
    IDIO_C_STRUCT_IDENT_DEF ("struct stat", libc_struct_stat, fgvi);
    IDIO_EXPORT_MODULE_PRIMITIVE (idio_libc_module, libc_struct_stat_set);

Here, we take advantage of the fact that
``IDIO_EXPORT_MODULE_PRIMITIVE`` always returned the actual primitive
reference (the value associated with the symbol ``struct-stat-ref``)
-- except we normally throw it away.

We can stick that reference in a list through the :lname:`C` macro
``IDIO_C_STRUCT_IDENT_DEF``.

In practice, it defines a name in :lname:`C`\ -land,
``idio_CSI_libc_struct_stat`` whose value is the list ``("struct stat"
struct-stat-ref)``.

So, we have something unique per structure that we can associate with
a pointer and the ``stat`` primitive can return:

.. code-block:: c

   return idio_C_pointer_type (idio_CSI_libc_struct_stat, statp);

Now we can revisit ``struct-stat-ref`` and perform the check:

.. code-block:: c

       IDIO_USER_C_TYPE_ASSERT (pointer, stat);
       if (idio_CSI_libc_struct_stat != IDIO_C_TYPE_POINTER_PTYPE (stat)) {
	   idio_error_param_value ("stat", "should be a struct stat", IDIO_C_FUNC_LOCATION ());

	   return idio_S_notreached;
       }

and we can extend the code for ``value-index`` to have a nosey in any
:lname:`C` pointers that come its way:

.. code-block:: c
   :caption: :file:`src/util.c`

	    ...
	    case IDIO_TYPE_C_POINTER:
		{
		    IDIO t = IDIO_C_TYPE_POINTER_PTYPE (o);
		    if (idio_S_nil != t) {
			IDIO cmd = IDIO_LIST3 (IDIO_PAIR_HT (t), o, i);

			IDIO r = idio_vm_invoke_C (idio_thread_current_thread (), cmd);

			return r;
		    }
		}
		break;
	    ...

We need to do a couple of changes for the *-set!* side of things to
work.

In :lname:`Idio`\ -land we can check that both *-ref* and *-set!*
primitives exist -- after all, someone might deem modifying a
:samp:`struct {foo}` a poor move and have removed ``struct-stat-set!``
-- but the auto-generated :file:`lib/libc-api.idio` doesn't know that:

.. code-block:: idio
   :caption: :file:`lib/libc-api.idio`

   if (and (function? struct-stat-ref)
	   (function? struct-stat-set!)) {
     set! (setter struct-stat-ref) struct-stat-set!
   }

and the code for ``set-value-index!`` can be updated for :lname:`C`
pointers as well:

.. code-block:: c
   :caption: :file:`src/util.c`

	    ...
	    case IDIO_TYPE_C_POINTER:
		{
		    IDIO t = IDIO_C_TYPE_POINTER_PTYPE (o);
		    if (idio_S_nil != t) {
			/*
			 * We want: (setter ref) o i v
			 *
			 * but we have to invoke by stage:
			 */
			IDIO setter_cmd = IDIO_LIST2 (idio_module_symbol_value (idio_S_setter,
										idio_Idio_module,
										idio_S_nil),
						      IDIO_PAIR_HT (t));

			IDIO setter_r = idio_vm_invoke_C (idio_thread_current_thread (), setter_cmd);

			if (! idio_isa_function (setter_r)) {
			    idio_debug ("(setter %s) did not yield a function\n", IDIO_PAIR_HT (t));
			    break;
			}

			IDIO set_cmd = IDIO_LIST4 (setter_r, o, i, v);

			IDIO set_r = idio_vm_invoke_C (idio_thread_current_thread (), set_cmd);

			return set_r;
		    }
		}
		break;
	    ...

Printing
^^^^^^^^

Of course, with your bespoke structure, you might want a bespoke
printer.  There's a mechanism there too.

The ``add-as-string`` system for adding bespoke printing for
:lname:`Idio` structures has been extended to support :lname:`C`
structures with ``idio_CSI_`` support.  The printer is associated with
the ``idio_CSI_`` value such that all :lname:`C` pointers to the same
kind of ``struct`` use the same printer.

The generated printers have two parts, a :lname:`C` part
``_as_string()`` which creates the results via ``idio_display_C()``
and ``idio_display()`` and an output string handle and an
:lname:`Idio` part which calls the :lname:`C` part.

The normal structure printing is to:

#. add :samp:`#<CSI {structure-name}`

#. for each structure member:

   #. add :samp:`{member-name}:`

   #. add the printed form of the structure member

      This requires a helper function, ``idio_C_type_format_string()``
      which can map, say, ``libc/pid_t`` into the appropriate
      :manpage:`printf(3)` format string (probably, ``%ld`` or ``%d``)

#. add ``>``

For some structure types there is a natural printed format.  For
example, a ``struct timeval`` has seconds and micro-seconds parts and
is commonly displayed in a :samp:`{seconds}.{micro-seconds}` form.

We know that the ``tv_usec`` member of a ``struct timeval`` represent
micro-seconds and can only be six decimal digits even though its type,
``suseconds_t``, is probably a ``long``.  In fact, it *must* be
displayed as six leading-0-padded digits otherwise it makes no sense.
For example, 1s and 213us would be displayed as ``1.000213`` and not
``1.213``.

Further, if there is a precision pending, say, 3, then the precision
is applied to the leading-0-padded string, not the literal ``tv_usec``
value, giving a result of ``1.000``.

.. sidebox::

   You wouldn't read back in the printed form, would you?

   No brownie points for you!

Note that the resultant printed form does not include the structure
name, it appears as just a floating point number.  The *value* is a
``struct timeval``, it's just the printed form that looks like a
floating point number.  Compare that with the printed representation
of the fixnum, 23, and the ``libc/pid_t``, 23, we had before.

The auto printing of :lname:`C` structures comes in quite handy.  For
example, noting I accidentally called the external command
:program:`stat` first, we get to compare results:

.. code-block:: idio-console

   Idio> stat "."
     File: .
     Size: 8192            Blocks: 24         IO Block: 4096   directory
   Device: fd00h/64768d    Inode: 17910888    Links: 3
   Access: (0775/drwxrwxr-x)  Uid: ( 1000/     idf)   Gid: ( 1000/     idf)
   Context: unconfined_u:object_r:user_home_t:s0
   Access: 2021-07-05 12:24:42.072310969 +0100
   Modify: 2021-07-05 12:24:43.574321757 +0100
   Change: 2021-07-05 12:24:43.574321757 +0100
    Birth: 2021-05-11 11:19:01.916839841 +0100
   #t
   Idio> libc/stat "."
   #<CSI libc/struct-stat
	 st_dev:64768
	 st_ino:17910888
	 st_nlink:3
	 st_mode:16893
	 st_uid:1000
	 st_gid:1000
	 st_rdev:0
	 st_size:8192
	 st_blksize:4096
	 st_blocks:24
	 st_atim:1625484282.072310969
	 st_mtim:1625484283.574321757
	 st_ctim:1625484283.574321757>

(I've broken the CSI printout for viewing convenience -- it is one long line!)

In this case, a ``struct timespec`` with a ``tv_nsec`` field for
nano-seconds is seen for the timestamp fields.  Notice the leading 0
for the access time entries.

And, not wanting to emphasise the point, those ``struct timespec``
printed representations use 19 significant digits which, if you recall
the work on :ref:`bignums`, is one too many for an accurate floating
point value.  Off to inexact school for you!

Files
-----

:program:`idio-c-api-gen` takes a nominal library name as an argument,
say, ``libc``.  It then seeks out an :file:`.../ext/libc` directory
where :file:`.../ext` is derived from possible directories called
:file:`.../lib/idio` in :envvar:`IDIOLIB`.

It then looks for :file:`.../ext/libc/api/libc-api.c` and compiles it
into :file:`.../ext/libc/api/libc-api.o` using the local
:file:`Makefile`.

It then runs :program:`objdump` on that :file:`.o` file and starts
generating output in :file:`.../ext/libc/gen`:

* :file:`gen/libc-api.c` (unfortunate name clash with the original
  source file)

  This :lname:`C` source file contains:

  - primitives for the :lname:`C` ``struct`` accessors and printer

  - primitives for any ``subprogram`` definitions -- excluding
    ``main``

    **It will be incorrect!**

    It is impossible to infer the correct handling of any errors.  The
    sample code is for the most common for of system errors.

    It is also not possible to identify when, commonly, a :lname:`C`
    pointer in the API is meant to be allocated by the caller.

    That sort of :lname:`C` API is likely to be replaced by an
    :lname:`Idio` API where the pointer is not required as an argument
    but is allocated and supplied internally and subsequently returned
    to the user rather than the nominal return value from the API
    call.

    Think of the example of :manpage:`stat(2)` where the :lname:`Idio`
    user cannot supply a ``struct stat`` and have an expectation that
    the value returned from a ``stat`` call is the ``struct stat``
    (and not the ``int`` that :manpage:`stat(2)` returns).

  - a putative :samp:`idio_{libc}_api_add_primitives()` function

  - a putative :samp:`idio_init_{libc}_api()` function which will
    contain:

    * ``#ifdef``\ -wrappered definitions for any ``enumeration_type``\
      s

    * the definitions for any ``struct`` members' symbols

    * the corresponding ``idio_CSI_`` definition for the ``struct``
      itself

* :file:`gen/libc-api.h`

  This :lname:`C` header file contains:

  - a helpful description of the used ``base_type``\ s in a comment

  - a generic :samp:`IDIO_USER_{lib}_TYPE_ASSERT()` macro

  - a series of :lname:`C` macro expansions for each ``typedef``:

    * a constructor

    * an accessor

    * a predicate

  - declarations for the ``struct`` definitions in
    :file:`gen/libc-api.c`

* :file:`gen/libc-api.idio`

  This :lname:`Idio` source file contains:

  - exports of:

    * the ``typedef`` type mappings (for the ``C/integer->`` function)

    * (commented out) the ``enumerated_type`` ``enumeration``\ s

  - the definitions of the entities just exported

  - the setup for some :ref:`setters`

* :file:`gen/test-libc-error.idio`

  This :lname:`Idio` source file contains a reasonable attempt at a
  test suite based on the known type and value tests that can be
  automatically inferred from the ``struct``\ s and ``subprogram``\ s
  described.

  It should be able to alert when a test fails to generate the
  expected error but do not rely on this.

* :file:`gen/libc-errors/*`

  This directory contains putative instances of all the test cases
  described above.

  **It will be incorrect!**

  For example, for ``struct`` test cases, to be able to reach some
  test cases then an valid argument needs to be supplied.

  It is impossible to infer how to create such an argument and the
  sample code simply refers to :samp:`{v}`.

  For example, for ``stat``-related tests which require a valid
  ``struct stat`` I've replaced :samp:`{v}` with ``(libc/stat ".")``
  which, since we've been writing the above code, successfully returns
  a ``struct stat`` with appropriate ``idio_CSI_`` definition.

Inconsistent Outputs
--------------------

You will not get the same output from all systems at the very least
because of the issues regarding ``typedef`` mappings as described
previously.

There are further complications with ``struct`` definitions and
``subprogram`` API types.

In the case of a ``struct`` you may find that some systems define
extra structure members over and above the nominal :lname:`C` API.
These should have no effect -- other than adding extra member name
symbols that you have no reason to use.  I have generally removed them
from the code to reduce the members down to the portable set.

For both ``struct`` and ``subprogram`` definitions you may find that
the actual :lname:`C` API uses some of these intermediate typedefs
we've mentioned.

For example, my Fedora system seems to use ``__pid_t`` everywhere
where the nominal :lname:`C` API thinks a ``pid_t`` should be used.

There are two problems here:

#. the generated :file:`gen/libc-api.c` will be using ``__pid_t``,
   eg. ``IDIO_USER_libc_TYPE_ASSERT (__pid_t, arg1);``

   That's not too traumatic to fix but you need to be aware of it if
   you choose a Fedora system as the source for your proto-permanent
   :file:`src/libc-api.c`.

#. unless you make an effort then the typedef for ``pid_t`` itself
   will be nowhere to be found

   This can be trivially solved by re-writing the original source file
   to say:

   .. code-block:: c

      pid_t pid = getpid ();

   thus forcing the ``typedef`` mapping to appear.

   Although, obviously, you won't know that that is required until you
   discover that the expected ``pid_t`` is missing.

   In other words, the creation of :file:`.../ext/libc/gen/libc-api.c`
   could take a couple of iterations around the loop.

Inconsistent API
----------------

In some cases the API has changed over time.  Historically, the
:manpage:`stat(2)` API had three ``time_t`` members, ``st_atime``,
``st_mtime`` and ``st_ctime``.

Since the ``time_t`` work described above the API has (mostly) become
three ``struct timespec`` members, ``st_atim``, ``st_mtim`` and
``st_ctim``.  There's lots of good things here and one bad one.

.. sidebox::

   The latter has potential typedef issues but appears to be a
   ``long`` on most systems.  I guess any 16-bit systems might have an
   issue.

A ``struct timespec`` has both a ``time_t`` member, ``tv_sec``, now,
of course, 64 bits wide and a nano-second-capable member, ``tv_nsec``.

The positives, then, are that we have our billions of years in a
``time_t`` *and* we have nano-second granularity.

The downside is that there is no (longer) a reference to the
``time_t``, the notional ``st_atime`` etc., in the API.

Most systems:

.. code-block:: c

   #define st_atime st_atim.tv_sec

but as we know, no traces of the :lname:`C` pre-processor are left in
the object file.

That means that :program:`idio-c-api-gen` cannot generate any such
references.

Of course, that's easy enough to fix when we're patching up the
generated code for other reasons.  We can manually write the code to
declare and use the extra symbols, ``st_atime`` etc., and add extra
clauses in the ``struct`` accessor primitives to handle the extra
symbols and, of course, we can correctly return the value with the
constructor ``idio_libc_time_t``.

Oddities
^^^^^^^^

Mac OS X chooses to be different and uses ``st_atimespec`` etc. as the
member names.

OpenIndiana uses a ``timespec_t`` which ought to cause us a problem as
we don't *use* a ``timespec_t`` in the source file so no ``typedef``
mapping is created.  Luckily, it has typedef'd ``struct timespec`` as
``timespec_t`` and so the nominal :lname:`C` API code which access
``statp->st_atim`` etc. just works.

Many systems don't typedef a ``suseconds_t`` for a ``struct timeval``
(returned by :manpage:`gettimeofday(2)` and :manpage:`getrusage(2)`)
even though they seem to get most of the way with :lname:`C` macros
for ``__suseconds_t_defined`` or ``_SUSECONDS_T_DECLARED``.

Evolution
=========

In the first instance, `muggins
<https://www.lexico.com/definition/muggins>`_, here, wrote the
``libc`` interfaces by hand in :file:`src/libc-wrap.c` -- the initial
prompt to look to automate the process as I was getting fed up trying
to figure out that a ``pid_t`` was on my collection of test systems.

I can then run :program:`idio-c-api-gen` for ``libc`` and take a copy
of the resultant :file:`gen/libc-api.c` and refashion it to replace
the interfaces in :file:`src/libc-wrap.c`.

Refashioning for me consisted largely of replacing the likes of
``__pid_t`` with ``pid_t`` and query-replacing the interface argument
names.

Interfaces to the likes of :manpage:`stat(2)` require more involvement
as the user wouldn't be supplying a ``struct stat`` and we want to
return the (suitably tagged) ``struct stat`` back to the user rather
than the ``int`` that :manpage:`stat(2)` returns.

Interfaces to the likes of :manpage:`getcwd(3)` require different
error tests and something like :manpage:`mkstemp(3)` requires even
more fiddling to return the open file descriptor and the name of the
file (from the modified template passed in).

Thus :file:`src/libc-api.c` requires the definitions in
:file:`src/libc-api.h` to build and, once I'd rejigged all the callers
-- think all the ``libc`` interfaces in :file:`lib/job-control.idio`
-- :program:`idio` requires the definitions in
:file:`lib/libc-api.idio` to run.

So, :file:`src/libc-api.*` are great for me on this box.  But, whilst
:file:`src/libc-api.c` has been manually tweaked to use the nominal
:lname:`C` API, :file:`src/libc-api.h` and :file:`lib/libc-api.idio`
are full of system-specific definitions.

I can't check those into source control as they're simply wrong for
anyone else.

Build Bootstrap II
------------------

Well, they're wrong but not *too* wrong which let's us play a trick.
Let's put a copy of whatever I've generated here, on my dev system, in
a :file:`src/build-bootstrap` directory which *all other systems* will
use to get going.

We can say that :program:`bin/idio` depends on a locally created
:file:`src/libc-api.h` and :file:`lib/libc-api.idio` and have a
specific rule to create those.

That specific rule can change the include paths for both the
:lname:`C` compiler and :program:`bin/idio` such that it uses the
:file:`src/build-bootstrap` directories just for long enough to run
:program:`idio-c-api-gen`.

Compiling this bootstrap version is likely to generate some warnings
about overflow and implicit constant conversions and others.  We care
deeply about this and... *Look! A squirrel!*

Having run :program:`idio-c-api-gen` on this system we will have
generated correct typedef mappings in :file:`src/libc-api.h` and
:file:`lib/libc-api.idio` and :program:`make` should convince itself
to rebuild :program:`idio` because a header file has changed
(technically, appeared).

:file:`src/libc-api.c` was refashioned to use the nominal :lname:`C`
API so requires no adjustment on any other system.


.. include:: ../../commit.rst

