.. include:: ../global.rst

##########################
Implementing :lname:`Idio`
##########################

Implementing something as complex as :lname:`Idio` involves a lot of
subsystems and the description of any one may necessarily involve the
understanding of another.  There's no easy way to describe the
"finished product" (I use both words loosely) without accepting that,
as a reader, you will have to `take some things as read
<https://en.wiktionary.org/wiki/take_something_as_read>`_ and perhaps
come back again to some sections.

Books such as :ref-title:`LiSP` (:cite:`LiSP`) describe multiple
complete implementations gradually upping the complexity with each one
in turn.  The repetitive nature is the classic methodology to pick up
the various techniques.

This treatise isn't pedagogical in that sense but simply dives
straight in.

.. toctree::
   :maxdepth: 2

   notes
   style
   virtual-machine/index
   reader/index
   evaluator/index
   garbage-collection
   idio-allocator
   idio-GC
   simple-types/index
   compound-types/index
   r0.1/index
   r0.2/index
   shell/index
   advanced/index
   extensions/index

.. include:: ../commit.rst

