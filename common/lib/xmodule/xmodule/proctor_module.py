import json
import logging
import random
import requests

from lxml import etree
from pkg_resources import resource_string

from django.conf import settings
from django.contrib.auth.models import User

from xmodule.x_module import XModule
from xmodule.seq_module import SequenceDescriptor

from xblock.core import Integer, Scope, String

log = logging.getLogger('mitx.' + __name__)

class ProctorPanel(object):
    '''
    Interface to proctor panel system, which determines if a given proctored item 
    (specified by its procset_name) is released to a given student (specified by the
    user_id).
    '''

    ProctorPanelServer = getattr(settings, 'PROCTOR_PANEL_SERVER_URL', 'https://proctor.mitx.mit.edu')

    def __init__(self, user_id, procset_name):
        
        self.user_id = user_id
        self.procset_name = procset_name
        self.ses = requests.session()
        self.user = User.objects.get(pk=user_id)

    def is_released(self):
        url = '{2}/cmd/status/{0}/{1}'.format(self.user_id, self.procset_name, self.ProctorPanelServer)
        log.info('ProctorPanel url={0}'.format(url))
        #ret = self.ses.post(url, data={'userid' : self.user_id, 'urlname': self.procset_name}, verify=False)
        ret = self.ses.get(url, verify=False)
        try:
            retdat = json.loads(ret.content)
        except Exception as err:
            log.error('bad return from proctor panel: ret.content={0}'.format(ret.content))
            retdat = {}

        log.info('ProctorPanel retdat={0}'.format(retdat))
        enabled = retdat.get('enabled', False)
        return enabled


class ProctorFields(object):
    username = String(help="username of student", scope=Scope.user_state)
    procset_name = String(help="Name of this proctored set", scope=Scope.settings)


class ProctorModule(ProctorFields, XModule):
    """
    Releases modules for viewing depending on proctor panel.

    The proctor panel is a separate application which knows the mapping between user_id's and usernames,
    and whether a given problem should be released for access by that student or not.
    
    The idea is that a course staff member is proctoring an exam provided in the edX system.
    After the staff member verifies a student's identity, the staff member releases the exam
    to the student, via the proctor panel.  Once the student is done, or the elapsed time
    runs out, exam access closes.

     Example:
     <proctor procset_name="proctorset1">
     <sequential url_name="exam1" />
     </proctor>

    """

    js = {'coffee': [resource_string(__name__, 'js/src/javascript_loader.coffee'),
                     resource_string(__name__, 'js/src/conditional/display.coffee'),
                     resource_string(__name__, 'js/src/collapsible.coffee'),
                     ]}

    js_module_name = "Conditional"
    css = {'scss': [resource_string(__name__, 'css/capa/display.scss')]}

    def __init__(self, *args, **kwargs):
        XModule.__init__(self, *args, **kwargs)

        # check proctor panel to see if this should be released
        user_id = self.system.seed
        self.pp = ProctorPanel(user_id, self.procset_name)

        self.child_descriptor = self.descriptor.get_children()[0]
        log.debug("children of proctor module (should be only 1): %s", self.get_children())
        self.child = self.get_children()[0]

        log.info('Proctor module child={0}'.format(self.child))
        log.info('Proctor module child display_name={0}'.format(self.child.display_name))
        self.display_name = self.child.display_name


    def get_child_descriptors(self):
        """
        For grading--return just the child.
        """
        return [self.child_descriptor]


    def not_released_html(self):
        return self.system.render_template('proctor_release.html', {
                'element_id': self.location.html_id(),
                'id': self.id,
                'name': self.display_name or self.procset_name,
                'pp': self.pp,
        })
        

    def get_html(self):
        if not self.pp.is_released():	# check for release each time we do get_html()
            log.info('is_released False')
            return self.not_released_html()
            # return "<div>%s not yet released</div>" % self.display_name

        log.info('is_released True')

        # for sequential module, just return HTML (no ajax container)
        if self.child.category in ['sequential', 'videosequence', 'problemset']:
            return self.child.get_html()

        # return ajax container, so that we can dynamically check for is_released changing
        return self.system.render_template('conditional_ajax.html', {
            'element_id': self.location.html_id(),
            'id': self.id,
            'ajax_url': self.system.ajax_url,
            'depends': '',
        })
        


    def handle_ajax(self, _dispatch, _data):
        if not self.pp.is_released():	# check for release each time we do get_html()
            log.info('is_released False')
            # html = "<div>%s not yet released</div>" % self.display_name
            html = self.not_released_html()
            return json.dumps({'html': [html], 'message': bool(True)})
        html = [child.get_html() for child in self.get_display_items()]

        log.info('is_released True')
        return json.dumps({'html': html})


    def get_icon_class(self):
        return self.child.get_icon_class() if self.child else 'other'


class ProctorDescriptor(ProctorFields, SequenceDescriptor):
    # the editing interface can be the same as for sequences -- just a container
    module_class = ProctorModule

    filename_extension = "xml"


    def definition_to_xml(self, resource_fs):

        xml_object = etree.Element('proctor')
        for child in self.get_children():
            xml_object.append(
                etree.fromstring(child.export_to_xml(resource_fs)))
        return xml_object

