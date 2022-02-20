.. include:: ../../global.rst

.. _`shell functions`:

***************
Shell Functions
***************

There are plenty of shell functions it would convenient to retain.

Predicates
==========

:lname:`Bash` offers a number of predicates which we can re-imagine
and maybe (maybe not!) avoid some legacy.  In particular,
:lname:`Bash` uses upper-case ``-S`` to test if a file is a socket
whereas all the other file predicates are in lower-case.  In addition,
rather than ``-h`` or ``-L`` for testing for a symbolic link we can
use ``l?``.

We can now use upper-case predicates for other objects, notably, file
descriptors, eg. ``T?`` for terminals.

.. _`b?`:

.. idio:function:: b? pathname

   Is ``pathname`` a block special device?

   :param pathname: pathname to test
   :type pathname: string

.. _`c?`:

.. idio:function:: c? pathname

   Is ``pathname`` a character special device?

   :param pathname: pathname to test
   :type pathname: string

.. _`d?`:

.. idio:function:: d? pathname

   Is ``pathname`` a directory?

   :param pathname: pathname to test
   :type pathname: string

.. _`e?`:

.. idio:function:: e? pathname

   Does ``pathname`` exist?

   :param pathname: pathname to test
   :type pathname: string

.. _`f?`:

.. idio:function:: f? pathname

   Is ``pathname`` a regular file?

   :param pathname: pathname to test
   :type pathname: string

.. _`l?`:

.. idio:function:: l? pathname

   Is ``pathname`` a symlink?

   :param pathname: pathname to test
   :type pathname: string

.. _`p?`:

.. idio:function:: p? pathname

   Is ``pathname`` a FIFO?

   :param pathname: pathname to test
   :type pathname: string

.. _`r?`:

.. idio:function:: r? pathname

   Does ``pathname`` satisfy :samp:`libc/access {pathname} libc/R_OK`?

   :param pathname: pathname to test
   :type pathname: string

.. _`s?`:

.. idio:function:: s? pathname

   Is ``pathname`` a socket?

   :param pathname: pathname to test
   :type pathname: string

.. _`T?`:

.. idio:function:: T? fd

   Is ``fd`` a terminal?

   :param fd: file descriptor to test
   :type fd: ``C/int``

.. _`w?`:

.. idio:function:: w? pathname

   Does ``pathname`` satisfy :samp:`libc/access {pathname} libc/W_OK`?

   :param pathname: pathname to test
   :type pathname: string

.. _`x?`:

.. idio:function:: x? pathname

   Does ``pathname`` satisfy :samp:`libc/access {pathname} libc/X_OK`?

   :param pathname: pathname to test
   :type pathname: string

.. include:: ../../commit.rst

