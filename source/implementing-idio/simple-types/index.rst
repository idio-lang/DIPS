.. include:: ../../global.rst

************
Simple Types
************

The simple types, ie. types that do not reference other types, are
actually far harder to deal with as they tend to break the GC
structure model or have some quite bespoke structure.

In addition, the reader will construct a value from one of these
simple types.

.. toctree::
   :maxdepth: 2

   numbers-and-constants
   characters-and-strings
   symbols-and-keywords
   bignums
   handles
   bitsets
