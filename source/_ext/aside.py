from docutils import nodes
from docutils.parsers.rst import Directive

from sphinx.locale import _
from sphinx.util.docutils import SphinxDirective

##############################

class aside(nodes.General, nodes.Element):
    pass

def visit_aside_node(self, node):
    self.body.append (self.starttag (node, 'aside', CLASS='aside'))

def depart_aside_node(self, node):
    self.body.append ('</aside>')

class AsideDirective(SphinxDirective):

    has_content = True

    def run(self):
        targetid = 'aside-%d' % self.env.new_serialno('aside')
        targetnode = nodes.target('', '', ids=[targetid])

        aside_node = aside('\n'.join(self.content))
        self.state.nested_parse(self.content, self.content_offset, aside_node)

        return [targetnode, aside_node]
    
##############################

class sidebox(nodes.General, nodes.Element):
    pass

def visit_sidebox_node(self, node):
    self.body.append (self.starttag (node, 'div', CLASS='sidebox'))

def depart_sidebox_node(self, node):
    self.body.append ('</div>')

class SideboxDirective(SphinxDirective):

    has_content = True

    def run(self):
        targetid = 'sidebox-%d' % self.env.new_serialno('sidebox')
        targetnode = nodes.target('', '', ids=[targetid])

        sidebox_node = sidebox('\n'.join(self.content))
        self.state.nested_parse(self.content, self.content_offset, sidebox_node)

        return [targetnode, sidebox_node]
    
    
def setup(app):
    app.add_directive("aside", AsideDirective)
    app.add_directive("sidebox", SideboxDirective)
    
    app.add_node(aside,
                 html=(visit_aside_node, depart_aside_node),
                 latex=(visit_aside_node, depart_aside_node),
                 text=(visit_aside_node, depart_aside_node))
    
    app.add_node(sidebox,
                 html=(visit_sidebox_node, depart_sidebox_node),
                 latex=(visit_sidebox_node, depart_sidebox_node),
                 text=(visit_sidebox_node, depart_sidebox_node))
    
    return {
        'version': '0.1',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
