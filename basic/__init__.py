# -*- coding: utf-8 -*-
# <Openstack-Test-Suite - integration test suite for Openstack>
# Copyright (c) 2012 Grid Dynamics Consulting Services, Inc, All Rights Reserved
# http://www.griddynamics.com
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.


from nose.tools import assert_equals
from nose.tools import assert_not_equals
from nose.tools import assert_true
from nose.tools import assert_false

import datetime
import re
import os
import logging
import time
import uuid
import commands
import imaplib

from collections import namedtuple
import collections
import yaml
import string

import conf
from lettuce import step, world, before, after
from lettuce_bunch.special import get_current_bunch_dir

from selenium import webdriver

from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support.ui import Select
from pdb import Pdb

dir_path = get_current_bunch_dir()
conf.init(dir_path)
config_file = os.path.join(dir_path, "config.yaml")
config = conf.load_yaml_config(config_file)
bunch_working_dir = dir_path


OUTPUT_GARBAGE = ['DeprecationWarning', 'import md5', 'import sha', 'DEBUG nova.utils', 'is deprecated', 'Warning:', 'PowmInsecureWarning:', 'RandomPool_DeprecationWarning:']
SSH_PRIVATE_KEY_PATH = os.path.join(get_current_bunch_dir(), config['keypair']['private-file'])
SSH_OPTS = '-T -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null'


def trace_me(*args, **kwargs):
    import pdb; pdb.set_trace()




PAGE_BLOCKS = {
    'top_menu': 'div.navbar-inner',
    'project_menu': 'div.container:nth-child(0n+2) ul.nav.nav-pills',
    'content_table': 'div.container table.table',
    'modal_dialog': 'div.modal.in',
    'content_form': 'div.container form.form-horizontal',
    'header': 'header.jumbotron.subhead h1',
    'subheader': 'header.jumbotron.subhead p',
    'period_menu': 'ul.period_menu'
}


def screen_on_failure(fcn):
    """
    Makes screenshot of failed scenario
    """
    def _wrapped(*args, **kwargs):
        try:
            fcn(*args, **kwargs)
        except:
            screen_path = os.path.join(get_current_bunch_dir(), 'screenshots-%s__%s.png' %
                (args[0].scenario.name, args[0].original_sentence ))
            world.selenium['browser'].get_screenshot_as_file(screen_path)
            raise
    return _wrapped


def patch_browser(fcn):
    """
    Creates properties for browser object which are associated with page parts
    """
    def _wrapped(*args, **kwargs):
        fcn(*args, **kwargs)
        for block, selector in PAGE_BLOCKS.items():
            try:
                setattr(world, block,
                        world.selenium['browser'].find_element_by_css_selector(selector))
            except:
                pass
    return _wrapped


def slugify(text):
    """
    Converts "Confirm Password" to "confirm_password"
    """
    return text.replace(' ', '_').lower()


def slugify1(text):
    """
    Converts "Confirm Password" to "confirmpassword"
    """
    return text.replace(' ', '').lower()


def slugify2(text):
    """
    Converts "Upload type" to "upload-type"
    """
    return text.replace(' ', '-').lower()


@step(u'I open browser')
def setup_browser(step):
    webdriver.DesiredCapabilities.FIREFOX['webdriver.log.file']="%s/firefox_console" % get_current_bunch_dir()
    world.selenium['browser'] = webdriver.Remote(config['selenium'],
                                        webdriver.DesiredCapabilities.FIREFOX)
    world.selenium['wait'] = WebDriverWait(world.selenium['browser'], 10)
    world.selenium['srv'] = config['focus']
    world.selenium['browser'].maximize_window()



@step(u'I close browser')
def clean_browser(step):
    world.selenium['browser'].quit()


@step(u'I close page')
def close_page(step):
    world.selenium['browser'].close()


class StepAssert(object):
    def __init__(self, step):
        self.step = step
        conf.log(conf.get_bash_log_file(),"asserting in step: %s" % step.sentence)

    def assert_equals(self, expr1, expr2, Msg=None):
        msg = 'Step "%s" failed ' % self.step.sentence
        if Msg is not None:
            msg += '\n' + Msg
        assert_equals(expr1, expr2, "%s. %s != %s" % (msg, expr1, expr2))

    def assert_not_equals(self, expr1, expr2, Msg=None):
        msg = 'Step "%s" failed ' % self.step.sentence
        if Msg is not None:
            msg += '\n' + Msg
        assert_not_equals(expr1, expr2, msg)

    def assert_true(self, expr, msg=''):
        msg = 'Step "%s" failed. %s' % (self.step.sentence, msg)
        assert_true(expr, msg)

    def assert_false(self, expr):
        msg = 'Step "%s" failed ' % self.step.sentence
        assert_false(expr, msg)

class command_output(object):
    def __init__(self, output):
        self.output = output

    def successful(self):
        return self.output[0] == 0

    def output_contains_pattern(self, pattern):
        regex2match = re.compile(pattern)
        search_result = regex2match.search(self.output[1])
        return (not search_result is None) and len(search_result.group()) > 0

    def output_text(self):
        def does_not_contain_garbage(str_item):
            for item in OUTPUT_GARBAGE:
                if item in str_item:
                    return False
            return True
        lines_without_warning = filter(does_not_contain_garbage, self.output[1].split(os.linesep))
        return string.join(lines_without_warning, os.linesep)

    def output_nonempty(self):
        return len(self.output) > 1 and len(self.output[1]) > 0

class bash(command_output):
    last_error_code = 0
    @classmethod
    def get_last_error_code(cls):
        return cls.last_error_code

    def __init__(self, cmdline):
        output = self.__execute(cmdline)
        super(bash,self).__init__(output)
        bash.last_error_code = self.output[0]

    def __execute(self, cmd):
        retcode = commands.getstatusoutput(cmd)
        status, text = retcode
        conf.bash_log(cmd, status, text)

#        print "------------------------------------------------------------"
#        print "cmd: %s" % cmd
#        print "sta: %s" % status
#        print "out: %s" % text
        return retcode



# UGLY, UGLY SOLUTION

@screen_on_failure
@patch_browser
@step(u'I search and remember IP of instance "(.*)"')
def remember_instance_ip(step, instance_name):
    world.selenium['wait'].until(lambda d: world.content_table.is_displayed())
    data_rows = world.content_table.find_elements_by_css_selector('tr')[1:]
    for row in data_rows:
        if 'IP' in row.text:
            td = row.find_elements_by_tag_name('td')[1]
            world.instances[instance_name] = {}
            world.instances[instance_name]['ip'] = td.text.split(':')[-1].strip()
            return
    raise RuntimeError("can't find instance ip")


## CHECK
# ping
@step(u'I ping host "(.*)"')
def ping_instance(step, instance_name):
    try:
        ip = world.instances[instance_name]['ip']
    except:
        ip = instance_name
    out = bash('ping -c3 %s || exit 1' % (ip))
    StepAssert(step).assert_true(out.successful())

@step(u'I ping host "(.*)" from master node')
def ping_instance(step, target_host):
    try:
        target = world.instances[target_host]['ip']
    except:
        target = target_host

    out = bash("""ssh %s -A root@%s 'ping -c3 %s'""" % 
                  (SSH_OPTS, config['cloud']['master'], target))
    StepAssert(step).assert_true(out.successful())


@step(u'I ping host "(.*)" from host "(.*)"')
def ping_instance(step, target_host, gateway_host):
    try:
        target = world.instances[target_host]['ip']
    except:
        target = target_host

    try:
        gateway = world.instances[gateway_host]['ip']
    except:
        gateway = gateway_host
    bash('chmod 600 %s' % SSH_PRIVATE_KEY_PATH)
    out = bash("""ssh %s -A -f -L 11111:%s:22 root@%s "sleep 10" && 
                ssh %s -i %s -p 11111 root@localhost 'ping -c3 %s'""" % 
                (SSH_OPTS, gateway, config['cloud']['master'], SSH_OPTS, SSH_PRIVATE_KEY_PATH, target))
    StepAssert(step).assert_true(out.successful())


@step(u'I cannot ping host "(.*)" from master node')
def ping_instance(step, target_host):
    try:
        target = world.instances[target_host]['ip']
    except:
        target = target_host

    out = bash("""ssh %s -A root@%s 'ping -c3 %s'""" % 
                  (SSH_OPTS, config['cloud']['master'], target))
    StepAssert(step).assert_true(not out.successful())


@step(u'I cannot ping host "(.*)" from host "(.*)"')
def ping_instance(step, target_host, gateway_host):
    try:
        target = world.instances[target_host]['ip']
    except:
        target = target_host

    try:
        gateway = world.instances[gateway_host]['ip']
    except:
        gateway = gateway_host
    bash('chmod 600 %s' % SSH_PRIVATE_KEY_PATH)
    out = bash("""ssh %s -A -f -L 11111:%s:22 root@%s "sleep 10" && 
                ssh %s -i %s -p 11111 root@localhost 'ping -c3 %s'""" % 
                (SSH_OPTS, gateway, config['cloud']['master'], SSH_OPTS, SSH_PRIVATE_KEY_PATH, target))
    StepAssert(step).assert_true(not out.successful())



# ssh
@step(u'I check ssh on host "(.*)" from master node')
def ssh_instance_key(step, target_host):
    try:
        target = world.instances[target_host]['ip']
    except:
        target = target_host
    bash('chmod 600 %s' % SSH_PRIVATE_KEY_PATH)
    out = bash("""ssh %s -A -f -L 11111:%s:22 root@%s 'sleep 10' && 
                ssh %s -i %s -p 11111 root@localhost 'hostname' || exit 1""" % 
                (SSH_OPTS, target, config['cloud']['master'],
                 SSH_OPTS, SSH_PRIVATE_KEY_PATH))
    StepAssert(step).assert_true(out.successful())


@step(u'I check ssh on host "(.*)" from host "(.*)"')
def ssh_instance_key(step, target_host, gateway_host):
    try:
        target = world.instances[target_host]['ip']
    except:
        target = target_host

    try:
        gateway = world.instances[gateway_host]['ip']
    except:
        gateway = gateway_host
    bash('chmod 600 %s' % SSH_PRIVATE_KEY_PATH)
    out = bash("""ssh %s -A -f -L 11111:%s:22 root@%s 'sleep 10' && 
                ssh %s -i %s -f -L 11112:%s:22 -p 11111 root@localhost 'sleep 10' && 
                ssh %s -i %s -p 11112 root@localhost 'hostname' || exit 1""" % 
                (SSH_OPTS, gateway, config['cloud']['master'],
                 SSH_OPTS, SSH_PRIVATE_KEY_PATH, target,
                 SSH_OPTS, SSH_PRIVATE_KEY_PATH))
    StepAssert(step).assert_true(out.successful())



@step(u'I check ssh access to host "(.*)" using key file "(.*)" from master node')
def ssh_instance_key(step, target_host, key_priv):
    try:
        target = world.instances[target_host]['ip']
    except:
        target = target_host

    out = bash("""ssh %s -A -f -L 11111:%s:22 root@%s 'sleep 10' && 
                ssh %s -i %s -p 11111 root@localhost 'hostname' || exit 1""" % 
                (SSH_OPTS, target, config['cloud']['master'],
                 SSH_OPTS, os.path.join(get_current_bunch_dir(), key_priv)))
    StepAssert(step).assert_true(out.successful())


@step(u'I check ssh access to host "(.*)" using password "(.*)" from master node')
def ssh_instance_pass(step, instance_name, password):
    out = bash('ssh %s -A -f -L 11112:%s:22 root@%s -N' % (SSH_OPTS, world.instances[instance_name]['ip'], config['cloud']['master']))
    if out.successful():
        from paramiko.client import SSHClient

        client = SSHClient()
        client.load_system_host_keys()
        client.connect('localhost', username='root', password=password, port=11112)
        #stdin, stdout, stderr = client.exec_command('hostname')
        client.exec_command('hostname')
        print 'done'
        client.close()


## EXECUTE
@step(u'I execute command "(.*)"')
def run(step, cmd):
    out = bash(cmd)
    print out.output_text()
    StepAssert(step).assert_true(out.successful())


@step(u'I execute on master node command "(.*)"')
def execute_on_master(step, cmd):
    out = bash('ssh %s -A root@%s %s' % (SSH_OPTS, config['cloud']['master'], cmd))
    print out.output_text()
    StepAssert(step).assert_true(out.successful())

@step(u'I execute on instance "(.*)" command "(.*)"')
def execute_on_master(step, instance_name, cmd):
    bash('chmod 600 %s' % SSH_PRIVATE_KEY_PATH)
#    keyfile = os.path.join(get_current_bunch_dir(), config['keypair']['private-file'])
    out = bash("""ssh %s -A -f -L 11111:%s:22 root@%s 'sleep 10' && 
                  ssh %s -i %s -p 11111 root@localhost %s""" 
                  % (SSH_OPTS, world.instances[instance_name]['ip'], config['cloud']['master'], SSH_OPTS, SSH_PRIVATE_KEY_PATH, cmd))
    print out.output_text()
    StepAssert(step).assert_true(out.successful())


@step(u'debug')
def debug(step):
    trace_me()


@step(u'screenshot "(.*)"')
def screenshot(step, name):
    world.selenium['browser'].get_screenshot_as_file(os.path.join(get_current_bunch_dir(), 'screen_%s.png' % name))


@step(u'I open page "(.*)"')
@patch_browser
def open_page(step, url):
    world.selenium['browser'].get(world.selenium['srv']+url)


@step(u'I see page title "(.*)"')
def see_page_title(step, title):
    world.selenium['wait'].until(lambda d: d.title.lower().startswith(title.lower()))


@step(u'I see text "(.*)" in element with css "(.*)"')
@screen_on_failure
def see_element_text(step, text, element_css):
    elem = world.selenium['browser'].find_element_by_css_selector(element_css)
    StepAssert(step).assert_true(re.compile(text).match(elem.text))


@step(u'I find window with title "(.*)"')
@screen_on_failure
def find_window(step, title):
    browser = world.selenium['browser']
    for handle in browser.window_handles:
        browser.switch_to_window(handle)
        if re.compile(title).match(browser.title):
            return

    StepAssert(step).assert_false(True)


@step(u'I see page header "(.*)"')
@screen_on_failure
def see_page_header(step, header):
    header_elem = world.selenium['wait'].until(
        lambda driver: driver.find_element_by_css_selector(PAGE_BLOCKS["header"]))
    StepAssert(step).assert_equals(header_elem.text.lower(), header.lower(), 'Page header mismatch.')


@step(u'I see page subheader "(.*)"')
@screen_on_failure
def see_page_subheader(step, subheader):
    subheader_elem = world.selenium['wait'].until(
        lambda driver: driver.find_element_by_css_selector(PAGE_BLOCKS["subheader"]))
    StepAssert(step).assert_equals(subheader_elem.text.lower(), subheader.lower(), 'Page subheader mismatch.')


@step(u'I type "(.*)" in field "(.*)"')
@screen_on_failure
def type_in_field(step, keys, field):
    el = world.selenium['wait'].until(
        lambda d: d.find_element_by_css_selector("input[name=%s]" % slugify(field)))
    world.selenium['wait'].until(lambda d: el.is_displayed())
    el.clear()
    el.send_keys(keys)

@step(u'I see "(.*)" in select "(.*)"')
@screen_on_failure
def check_selected_option(step, text, name):
    world.selenium['wait'].until(lambda d: d.find_element_by_css_selector("select[name=%s]" % name).is_displayed())
    selected = world.selenium['browser'].find_elements_by_css_selector("select[name=%s] option" % name)
    StepAssert(step).assert_not_equals(len(selected), 0)
    StepAssert(step).assert_equals(selected[0].text, text)

@step(u'I see "(.*)" in select "(.*)"')
@screen_on_failure
def check_selected_option(step, text, name):
    selected = world.selenium['wait'].until(lambda d: d.find_element_by_css_selector("select[name=%s]" % name))
    options = selected.find_elements_by_css_selector("option")
    StepAssert(step).assert_not_equals(len(options), 0)
    StepAssert(step).assert_equals(options[0].text, text)


@step(u'I click radio button "(.*)" in field "(.*)"')
@screen_on_failure
@patch_browser
def click_radio_button_in_field(step, field, label):
    radio_button_group = world.selenium['wait'].until(lambda d: world.content_form.find_element_by_css_selector("div.control-group.%s" % slugify2(label)))
    inputs = radio_button_group.find_elements_by_id('id_%s' % slugify(label))
    for input in inputs:
        if input.get_attribute('value') == slugify(field):
            input.click()
            return
    raise RuntimeError('radio button not found')


@step(u'I select file "(.*)" in "([^"]*)"( and click cancel)?')
@screen_on_failure
def select_file(step, path, uploader_class, is_cancel_required):
    uploader = world.selenium['browser'].find_element_by_css_selector('div.%s' % uploader_class)
    inputs = uploader.find_elements_by_tag_name('input')
    for input in inputs:
        if input.get_attribute('type') == 'file':
            if is_cancel_required:
                click_selector = 'div.%s a.cancel-upload' % uploader_class
                interval_id = world.selenium['browser'].execute_script(
                    'return setInterval(function(){jQuery("%s").click()}, 5)' % click_selector)
            input.send_keys(path)
            world.selenium['browser'].execute_script('console.log("keys sent")')
            if is_cancel_required:
                world.selenium['browser'].execute_script(
                    'clearInterval(%s)' % interval_id)
            break


@step(u'I select file "(.*)" in select "(.*)"')
@screen_on_failure
def select_file_in_select(step, path, uploader):
    uploader = world.selenium['browser'].find_element_by_css_selector('div.%s' % uploader)
    inputs = uploader.find_elements_by_tag_name('input')
    for input in inputs:
        if input.get_attribute('type') == 'file':
            input_id = input.get_attribute('id')
            world.selenium['browser'].execute_script("el = $('#%s'); el.css('height', '100px').css('width','100px'); el[0].checked = true;" % input_id)
            input.send_keys(path)
            world.selenium['browser'].execute_script("$('select#id_initrd').removeAttr('disabled');")
            world.selenium['browser'].execute_script("$('button#filesystem_uploaded_file_button').removeAttr('disabled');")
            break


@step(u'I click top menu "(.*)", sub-menu "(.*)"')
@screen_on_failure
@patch_browser
def click_top_menu_with_submenu(step, top_menu_text, sub_menu_text):
    world.selenium['wait'].until(lambda d: world.top_menu.find_element_by_partial_link_text(top_menu_text).is_displayed())
    world.top_menu.find_element_by_partial_link_text(top_menu_text).click()
    world.selenium['wait'].until(lambda d: world.top_menu.find_element_by_partial_link_text(sub_menu_text).is_displayed())
    world.top_menu.find_element_by_partial_link_text(sub_menu_text).click()


@step(u'I click top menu "(.*)"')
@screen_on_failure
@patch_browser
def click_top_menu(step, top_menu_text):
    top_menu = world.selenium['wait'].until(
        lambda d: d.find_element_by_css_selector(
            PAGE_BLOCKS["top_menu"]).find_element_by_partial_link_text(top_menu_text))
    StepAssert(step).assert_true(top_menu.is_enabled(), 'Top menu item "%s" is disabled' % top_menu_text)
    time.sleep(2)
    top_menu.click()


@step(u'I click project menu item "(.*)"')
@screen_on_failure
@patch_browser
def click_project_menu(step, project_menu_link):
    menu_item = world.selenium['wait'].until(
        lambda d: d.find_element_by_css_selector(
            PAGE_BLOCKS["project_menu"]).find_element_by_partial_link_text(project_menu_link))
    StepAssert(step).assert_true(menu_item.is_enabled(), 'Project menu item "%s" is disabled' % project_menu_link)
    menu_item.click()


@step(u'I click "(.*)" in line containing "(.*)", row "(.*)"')
@screen_on_failure
@patch_browser
def click_in_line_containing(step, link_text, line_text, row_text):
    from selenium.common.exceptions import StaleElementReferenceException
    try:
        world.selenium['wait'].until(lambda d: world.content_table.is_displayed())
    except StaleElementReferenceException:
        world.selenium['wait'].until(lambda d: world.content_table.is_displayed())
    head_tds = world.content_table.find_elements_by_css_selector('thead th')
    column = None
    for i, td in enumerate(head_tds):
        if row_text in td.text:
            column = i
            break
    if column is None:
        raise RuntimeError('Cant see row %s' % row_text)

    data_rows = world.content_table.find_elements_by_css_selector('tr')[1:]

    for row in data_rows:
        if line_text in row.text:
            td = row.find_elements_by_tag_name('td')[column]
            link = td.find_element_by_partial_link_text(link_text)
            link.click()
            return
    raise RuntimeError("can't see %s in line containing %s, row %s", (link_text, line_text, row_text))


@step(u'I see modal dialog "(.*)" contains "(.*)"')
@screen_on_failure
def see_modal_dialog(step, modal_header, modal_data):
    world.selenium['wait'].until(lambda d: world.modal_dialog.is_displayed())
    header = world.modal_dialog.find_element_by_css_selector('div.modal-header h3')
    if not (modal_header in header.text):
        raise RuntimeError("Modal header text mismatch")
    body = world.modal_dialog.find_element_by_css_selector('div.modal-body')
    if not (modal_data in body.text):
        raise RuntimeError("Modal body text mismatch")


@step(u'I see project menu item "(.*)" active')
@screen_on_failure
def see_project_menu_item(step, text):
    world.selenium['wait'].until(lambda d: world.project_menu.find_element_by_partial_link_text(text).is_displayed())
    active_element = world.project_menu.find_element_by_css_selector('li.active')
    StepAssert(step).assert_equals(text, active_element.text)


@step(u'I see "(.*)" in line (.*)')
@screen_on_failure
def see_in_line(step, text, line):
    world.selenium['wait'].until(lambda d: world.content_table.is_displayed())
    data_rows = world.content_table.find_elements_by_css_selector('tr')[1:]
    for row in data_rows:
        if text in row.text:
            return
    raise RuntimeError("can't see '%s' in line '%s'", (text, line))


@step(u'I see empty table:')
@screen_on_failure
def see_empty_table(step):
    world.selenium['wait'].until(lambda d: world.content_table.is_displayed())
    data_rows = world.content_table.find_elements_by_css_selector('tr')
    if len(data_rows) > 1:
        raise RuntimeError('Table is not empty!')
    

@step(u'I remember table:')
def remember_table(step):
    world.selenium['wait'].until(lambda d: world.content_table.is_displayed())
    data_rows = world.content_table.find_elements_by_css_selector('tr')
    world.table_state = [r.text for r in data_rows[1:]]
    

@step(u'I forget table:')
def forget_table(step):
    world.table_state = None
    
    
def compare_table_content(hashes, rows, keys):
    for i, step_hash in enumerate(hashes, start=1):
        # create hash from row tds
        tds = rows[i-1].find_elements_by_tag_name('td')
        for j, key in enumerate(keys):
            if step_hash[key] == 'not_empty':
                if tds[j].text == '':
                    raise RuntimeError('Data in column "%s": "%s" should be not empty!' % (key, step_hash[key]))
            elif step_hash[key] == 'empty':
                if not tds[j].text in ['', ' ']:
                    raise RuntimeError('Data in column "%s": "%s" should be empty!' % (key, step_hash[key]))
            else:
                if tds[j].text.replace('\n', ' ') != step_hash[key]:
                    raise RuntimeError('Data in column "%s": "%s" is not present in table. Got %s instead' % (key, step_hash[key], tds[j].text.replace('\n', ' ')))




@step(u'I see in table:')
@screen_on_failure
def see_in_table(step):
    world.selenium['wait'].until(lambda d: world.content_table.is_displayed())
    data_rows = world.content_table.find_elements_by_css_selector('tr')
    if step.hashes:
        current_table_state = [r.text for r in data_rows[1:]]
        difference_texts = set(current_table_state) - set(world.table_state)
        difference_rows = []
        for row in data_rows[1:]:
            if row.text in difference_texts:
                difference_rows.append(row)
        if difference_rows:
            compare_table_content(step.hashes, difference_rows, step.keys)
        else:
            raise RuntimeError('No new lines found in the table') 
    else:
        if len(world.table_state) == len(data_rows[1:]):
            # table is unchanged
            return
        if len(world.table_state) - len(data_rows[1:]) != 1:
            raise RuntimeError('Row was not deleted')


@step(u'I see table:')
@screen_on_failure
def see_table(step):
    world.selenium['wait'].until(lambda d: world.content_table.is_displayed())
    data_rows = world.content_table.find_elements_by_css_selector('tr')
    if step.hashes:
        # checks data matching
        for i, step_hash in enumerate(step.hashes, start=1):
            # create hash from row tds
            tds = data_rows[i].find_elements_by_tag_name('td')
            for j, key in enumerate(step.keys):
                if step_hash[key] == 'not_empty':
                    if tds[j].text == '':
                        raise RuntimeError('Data in column "%s": "%s" should be not empty!' % (key, step_hash[key]))
                elif step_hash[key] == 'empty':
                    if not tds[j].text in ['', ' ']:
                        raise RuntimeError('Data in column "%s": "%s" should be empty!' % (key, step_hash[key]))
                else:
                    if tds[j].text.replace('\n', ' ') != step_hash[key]:
                        raise RuntimeError('Data in column "%s": "%s" is not present in table. Got %s instead' % (key, step_hash[key], tds[j].text.replace('\n', ' ')))
    else:
        # check presence on the table on the page
        head_text = world.content_table.find_element_by_tag_name('thead').text
        for key in step.keys:
            if not key in head_text:
                raise RuntimeError('Column "%s" is not present in table header.' % key)
        if len(data_rows) > 1:
            raise RuntimeError('Table is not empty!')


@step(u'I cannot click form button "(.*)"')
@screen_on_failure
@patch_browser
def cannot_click_button(step, link_text):
    world.selenium['wait'].until(lambda d: world.content_form.find_element_by_css_selector('button.tc-add').is_displayed())
    StepAssert(step).assert_equals(u'true', world.content_form.find_element_by_css_selector('button.tc-add').get_attribute('disabled'))


@step(u'I click modal dialog button "(.*)"')
@screen_on_failure
@patch_browser
def click_modal_dialog_button(step, link_text):
    try:
        world.selenium['wait'].until(lambda d: world.modal_dialog.find_element_by_partial_link_text(link_text).is_displayed())
        world.modal_dialog.find_element_by_partial_link_text(link_text).click()
        return
    except:
        world.selenium['wait'].until(lambda d: world.modal_dialog.find_element_by_tag_name('button').is_displayed())
        buttons = world.modal_dialog.find_elements_by_tag_name('button')
        for button in buttons:
            if button.text == link_text:
                button.click()
                return
    raise RuntimeError('Button not found "%s"' % link_text)



@step(u'I click button "(.*)"')
@screen_on_failure
@patch_browser
def push_the_button(step, button_text):
    import time

    buttons_classes = [
        "button.btn",
        "button.btn.btn-primary",           # active button
        "a.btn.btn-primary",           # active button
        "a.btn"
        #"div.subnav a.btn.btn-primary",     # active link which looks like button
        #"div.subnav a"                      # not active link which looks like button
    ]

    global click_button_element
    def watchout(d):
        global click_button_element
        for css in buttons_classes:
            for x in d.find_elements_by_css_selector(css):
                if x.is_displayed() and x.text == button_text:
                    click_button_element = x
                    return True
        raise RuntimeError, "false!"
        return False

    try:
        world.selenium['wait'].until(watchout)
    except:
        time.sleep(1)
        try:
            world.selenium['wait'].until(watchout)
        except:
            time.sleep(1)
            world.selenium['wait'].until(watchout)

    click_button_element.click()

    # import pdb; pdb.set_trace()
    # raise RuntimeError, "No button with text '%s' for click." % button_text


@step(u'I see "([^"]+)" in form field "([^"]+)"')
@screen_on_failure
def see_in_form_field(step, content, field_name):
    world.selenium['wait'].until(lambda d: d.find_element_by_name(field_name).is_displayed())
    input = world.selenium['browser'].find_element_by_name(field_name)
    StepAssert(step).assert_equals(input.get_attribute('value'), content)


@step(u'I select "(.*)" in field "(.*)"')
@screen_on_failure
def select_in_field(step, value, select_name):
    try:
        world.selenium['wait'].until(lambda d: d.find_element_by_name(slugify(select_name)).is_displayed())
        Select(world.selenium['browser'].find_element_by_name(slugify(select_name))).select_by_visible_text(value)
    except:
        world.selenium['wait'].until(lambda d: d.find_element_by_name(slugify1(select_name)).is_displayed())
        Select(world.selenium['browser'].find_element_by_name(slugify1(select_name))).select_by_visible_text(value)


@step(u'I wait (\d+) seconds')
@screen_on_failure
@patch_browser
def wait(step, seconds):
    time.sleep(float(seconds))
    
    
@step(u'I wait page refresh for "(.*)" seconds')
@screen_on_failure
@patch_browser
def wait_for_page(step, seconds):
    t_start = datetime.datetime.now()
    current_url = world.selenium['browser'].current_url
    while True:
        t_end = datetime.datetime.now()
        delta = t_end - t_start
        if delta.seconds > float(seconds):
            break
        time.sleep(5)
        if world.selenium['browser'].current_url != current_url:
            return
    raise RuntimeError("Timeout")
    

@step(u'I refresh page until I see "(.*)" in line containing "(.*)"')
@screen_on_failure
@patch_browser
def wait_until_text_in_table_is_present(step, text, line):
    """
    200 seconds is a timeout for whole function
    check every 5 seconds
    """
    world.selenium['wait'].until(lambda d: world.content_table.is_displayed())
    t_start = datetime.datetime.now()
    while True:
        t_end = datetime.datetime.now()
        delta = t_end - t_start
        if delta.seconds > 200:
            break
        time.sleep(5)
        world.selenium['browser'].refresh()
        #check if the given text is present on page
        content_table = world.selenium['browser'].find_element_by_css_selector('div.container table.table')
        data_rows = content_table.find_elements_by_css_selector('tr')
        for row in data_rows:
            tds = row.find_elements_by_css_selector('td')
            for td in tds:
                if td.text == line: # - correct row
                    if text in row.text:
                        return True
    raise RuntimeError("Timeout")


@step(u'I wait you')
def wait_you(step):
    import pdb; pdb.set_trace()

# Appears on top of the page. Success/Info and operational errors

@step(u'I see (.*) notification "(.*)"')
@screen_on_failure
def notification(step, _type, text):
    world.selenium['wait'].until(lambda d: d.find_element_by_css_selector("div.alert.alert-%s" % _type).is_displayed())
    StepAssert(step).assert_equals(text, world.selenium['browser'].find_element_by_css_selector("div.alert.alert-%s" % _type).text.replace('\n', '')[1:])

@step(u'I do not see (.*) notification "(.*)"')
@screen_on_failure
def no_notification(step, _type, text):
    import time
    time.sleep(2)
    for x in world.selenium['browser'].find_elements_by_css_selector("div.alert.alert-%s" % _type):
        StepAssert(step).assert_not_equals(text, x.text.replace('\n', '')[1:])


@step(u'I do not see selector "(.*)"')
def no_selector(step, selector):
    import time
    time.sleep(2)
    for x in world.selenium['browser'].find_elements_by_css_selector(selector):
        StepAssert(step).assert_false(x.is_displayed())
    
    

# Appears when needed more input

@step(u'I see error tip "(.*)"')
@screen_on_failure
def error_tip(step, text):
    world.selenium['wait'].until(lambda d: d.find_element_by_css_selector("div.help-inline").is_displayed())
    tips = world.selenium['browser'].find_elements_by_css_selector("div.help-inline")
    for tip in tips:
        if text in tip.text:
            return True
    raise RuntimeError('No such error tip: `%s`' % text)


def _get_last_email(login, password):
    mail = imaplib.IMAP4_SSL('imap.gmail.com')
    mail.login(login, password)
    mail.select("inbox")
    result, data = mail.search(None, "ALL")
    latest_email_id = data[0].split()[-1]
    result, data = mail.fetch(latest_email_id, "(RFC822)")
    raw_email = data[0][1]
    return raw_email

@step(u'I open invitation email as "(.*)", "(.*)"')
@screen_on_failure
def open_invitation_email(step, login, password):
    raw_email = _get_last_email(login, password)
    url = raw_email.replace('\n', '').replace('\r', '').split(world.selenium['srv'])[-1]
    world.selenium['browser'].get(world.selenium['srv'] + url)
    

@step(u'I see "([^"]+)" in last email as "([^"]+)", "([^"]+)"')
@screen_on_failure
def see_in_last_email(step, content, login, password):
    raw_email = _get_last_email(login, password)
    return content in raw_email


@step(u'I open recovery email as "(.*)", "(.*)"')
@screen_on_failure
def open_recovery_email(step, login, password):
    raw_email = _get_last_email(login, password)
    url = raw_email.replace('\n', '').replace('\r', '').split(world.selenium['srv'])[-1]
    world.selenium['browser'].get(world.selenium['srv'] + url)
    
@step(u'I open new-password email as "(.*)", "(.*)" and type new password')
@screen_on_failure
def open_new_password_email(step, login, password):
    raw_email = _get_last_email(login, password)
    new_password = raw_email.replace('\n', '').replace('\r', '').strip().split('Your new password:')[-1]
    el = world.selenium['browser'].find_element_by_id("password")
    el.send_keys(new_password)


@step(u'I see "(.*)" in document')
@screen_on_failure
def see_in_document(step, text):
    world.selenium['wait'].until(lambda d: d.find_element_by_tag_name("body").is_displayed())
    elem = world.selenium['browser'].find_element_by_tag_name("code")
    if text not in elem.text:
        raise RuntimeError("can't see '%s' in line '%s'", (text, line))
    return True

@step(u'I click period menu item "(.*)"')
@screen_on_failure
@patch_browser
def click_period_menu_item(step, link_text):
    world.selenium['wait'].until(lambda d: world.period_menu.find_element_by_partial_link_text(link_text).is_displayed())
    world.period_menu.find_element_by_partial_link_text(link_text).click()

@step(u'I see period images')
@screen_on_failure
def see_period_images(step):
    imgs = world.selenium['browser'].find_elements_by_css_selector("img.graph")
    displayed_count = 0;
    for img in imgs:
        if img.is_displayed():
            displayed_count += 1;
    if displayed_count != 4:
        raise RuntimeError('Can\'t see exactly 4 for images on page')

@step(u'I click link "(.*)"')
@screen_on_failure
@patch_browser
def click_link(step, text):
    world.selenium['wait'].until(lambda d: d.find_element_by_partial_link_text(text).is_displayed())
    world.selenium['browser'].find_element_by_partial_link_text(text).click()

@step(u'I see empty input "(.*)"')
def empty_input(step, selector):
    try:
        world.selenium['wait'].until(lambda d: d.find_element_by_css_selector(selector).is_displayed())
    except:
        time.sleep(1)
        world.selenium['wait'].until(lambda d: d.find_element_by_css_selector(selector).is_displayed())
    StepAssert(step).assert_equals('', world.selenium['browser'].find_element_by_css_selector(selector).text)

@step(u'I click selector "(.*)"')
def click_selector(step, selector):
    world.selenium['wait'].until(lambda d: d.find_element_by_css_selector(selector).is_displayed())
    world.selenium['browser'].find_elements_by_css_selector(selector).click()





class debug(object):
    @staticmethod
    def current_bunch_path():
#        global __file__
#        return __file__
        return get_current_bunch_dir()

    class save(object):
        @staticmethod
        def file(src, dst):
            def saving_function():
                bash("sudo dd if={src} of={dst}".format(src=src,dst=dst))
            return saving_function

        @staticmethod
        def command_output(command, file_to_save):
            def command_output_function():
                dst = os.path.join(debug.current_bunch_path(),file_to_save)
                conf.log(dst, bash(command).output_text())
            return command_output_function

        @staticmethod
        def nova_conf():
            debug.save.file('/etc/nova/nova.conf', os.path.join(debug.current_bunch_path(), 'nova.conf.log'))()

        @staticmethod
        def log(logfile):
            src = logfile if os.path.isabs(logfile) else os.path.join('/var/log', logfile)
            dst = os.path.basename(src)
            dst = os.path.join(debug.current_bunch_path(), dst if os.path.splitext(dst)[1] == '.log' else dst + ".log")
            return debug.save.file(src, dst)


class MemorizedMapping(collections.MutableMapping,dict):
    class AmbiguousMapping(Exception):
        pass

    class EmptyResultForKey(Exception):
        pass

    def __init__(self, restore_function=None,store_function=None, **kwargs):
        self.__rst_fcn = restore_function
        self.__store_fcn = store_function
        super(MemorizedMapping, self).__init__(**kwargs)

    def __getitem__(self,key):
        if not self.__contains__(key) and self.__rst_fcn is not None:
            items = self.__rst_fcn(key)
            if len(items) > 1:
                raise MemorizedMapping.AmbiguousMapping(items)
            elif not len(items):
                raise MemorizedMapping.EmptyResultForKey(key)
            else:
                self[key] = items[0]

        return dict.__getitem__(self,key)

    def __setitem__(self, key, value):
        if self.__store_fcn is not None:
            self.__store_fcn(key, value)

        dict.__setitem__(self,key,value)

    def __delitem__(self, key):
        dict.__delitem__(self,key)

    def __iter__(self):
        return dict.__iter__(self)

    def __len__(self):
        return dict.__len__(self)

    def __contains__(self, x):
        return dict.__contains__(self,x)

class translate(object):
    @classmethod
    def register(cls, name, restore_function=None, store_function=None):
        """
        Register property 'name' which acts as mapping of keys and values:
        translate.name[key] -> value
        if key is not found for dictionary name name, then
        it is tried to be resolved by callng mapping_function(key).
        mapping_function(key) -> [value1, value2, ...]
        If value is not unique for key, then exception is raised. The same happens if list is empty
        """
        setattr(cls, name, MemorizedMapping(restore_function=restore_function, store_function=store_function))

    @classmethod
    def unregister(cls, name):
        delattr(cls, name)

class SerializeMapping(object):
    @staticmethod
    def mapping_file(mapping_name):
        return os.path.join(get_current_bunch_dir(), mapping_name + '.map')

    @staticmethod
    def restore_fcn(mapping_name):
        filename = SerializeMapping.mapping_file(mapping_name)

        def restore_fcn(key):
            if os.path.exists(filename):
                with open(filename, 'r') as map_file:
                    mapping = yaml.load(map_file)
                    return [mapping[key]]
            else:
                return []
        return restore_fcn

    @staticmethod
    def store_fcn(mapping_name):
        filename = SerializeMapping.mapping_file(mapping_name)
        def store_fcn(key, value):
            mapping = {}
            if os.path.exists(filename):
                with open(filename, 'r') as map_file:
                    mapping = yaml.load(map_file)
            mapping[key] = value
            with open(filename, 'w') as map_file:
                map_file.write(yaml.dump(mapping, default_flow_style=False))

        return store_fcn

def register_persistent_mapping(name):
    translate.register(name,
        restore_function=SerializeMapping.restore_fcn(name),
        store_function=SerializeMapping.store_fcn(name))
    return getattr(translate, name)


world.selenium = register_persistent_mapping('selenium')
world.instances = register_persistent_mapping('instances')
