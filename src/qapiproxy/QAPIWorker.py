# Copyright (c) 2016 Iotic Labs Ltd. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://github.com/Iotic-Labs/IoticHttp/blob/master/LICENSE
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# pylint: disable=invalid-name

import logging
logger = logging.getLogger(__name__)

from threading import Thread, Event
from queue import Queue
from time import sleep

from IoticAgent import Core as IoticAgentCore


class QAPIWorker(object):
    """QAPI Worker is one IoticAgent instance
    """

    def __init__(self, details, managerStop, keepFeeddata=50, keepControlreq=50, keepUnsolicited=50):
        self.__details = details
        self.__stop = Event()
        self.__managerStop = managerStop

        self.__keepFeeddata = 0
        try:
            self.__keepFeeddata = int(keepFeeddata)
        except:
            logger.warning("QAPIWorker failed to int keepFeeddata '%s'", keepFeeddata)

        self.__keepControlreq = 0
        try:
            self.__keepControlreq = int(keepControlreq)
        except:
            pass

        self.__keepUnsolicited = 0
        try:
            self.__keepUnsolicited = int(keepUnsolicited)
        except:
            pass
        #
        self.__qFeeddata = Queue()
        self.__qControlreq = Queue()
        self.__qUnsolicited = Queue()
        #
        self.__thread = None
        self.__qc = None        # IoticAgent.Core.Client instance
        #
        self.__polltime = 5
        self.__dead_max = 6     # How many times to try to start a dead worker?
        self.__dead_sleep = 5   # How long to sleep between worker.start attempts?
        #
        # IoticAgent Core throttle settings
        self.__queue_size = 128
        if 'queue_size' in details:
            self.__queue_size = details['queue_size']
        self.__throttle_conf = '540/30,1890/300'
        if 'throttle' in details:
            self.__throttle_conf = details['throttle']
        #
        self.__vhost = 'container1'
        if 'vhost' in details:
            self.__vhost = details['vhost']
        #
        self.__sslca = None
        if 'sslca' in details:
            self.__sslca = details['sslca']
        #
        self.__prefix = ''
        if 'prefix' in details:
            self.__prefix = details['prefix']

    def check_details(self, details):
        for ek in details:
            if ek in self.__details:
                if self.__details[ek] != details[ek]:
                    return False
        return True

    def check_authtoken(self, authToken):
        if 'authtokens' in self.__details:
            tokens = self.__details['authtokens'].strip().split("\n")
            for et in tokens:
                if et == authToken:
                    return True
        elif authToken == self.__details['token']:  # todo: Allow Agent token as API Key ??
            return True
        return False

    def start(self):
        self.__thread = Thread(target=self.__run)
        self.__thread.start()

    def stop(self):
        self.__stop.set()
        self.__thread.join()

    @property
    def default_lang(self):
        return self.__qc.default_lang

    def request_entity_create(self, lid, tepid=None):
        return self.__qc.request_entity_create(lid, epId=tepid)

    def request_entity_rename(self, lid, newlid):
        return self.__qc.request_entity_rename(lid, newlid)

    def request_entity_reassign(self, lid, nepid=None):
        return self.__qc.request_entity_reassign(lid, nepid)

    def request_entity_delete(self, lid):
        return self.__qc.request_entity_delete(lid)

    def request_entity_list(self, limit=500, offset=0):
        return self.__qc.request_entity_list(limit=limit, offset=offset)

    def request_entity_list_all(self, limit=500, offset=0):
        return self.__qc.request_entity_list_all(limit=limit, offset=offset)

    def request_entity_meta_get(self, lid, fmt="n3"):
        return self.__qc.request_entity_meta_get(lid, fmt=fmt)

    def request_entity_meta_set(self, lid, meta, fmt="n3"):
        return self.__qc.request_entity_meta_set(lid, meta, fmt=fmt)

    def request_entity_meta_setpublic(self, lid, public=True):
        return self.__qc.request_entity_meta_setpublic(lid, public=public)

    def request_entity_tag_create(self, lid, tags, lang=None, delete=False):
        return self.__qc.request_entity_tag_create(lid, tags, lang=lang, delete=delete)

    def request_entity_tag_delete(self, lid, tags, lang=None):
        return self.request_entity_tag_create(lid, tags, lang=lang, delete=True)

    def request_entity_tag_list(self, lid, limit=100, offset=0):
        return self.__qc.request_entity_tag_list(lid, limit=limit, offset=offset)

    def request_point_create(self, foc, lid, pid, control_cb=None):
        return self.__qc.request_point_create(foc, lid, pid, control_cb=control_cb)

    def request_point_rename(self, foc, lid, pid, newpid):
        return self.__qc.request_point_rename(foc, lid, pid, newpid)

    def request_point_confirm_tell(self, foc, lid, pid, success=True, requestId=None):
        return self.__qc.request_point_confirm_tell(foc, lid, pid, success=success, requestId=requestId)

    def request_point_delete(self, foc, lid, pid):
        return self.__qc.request_point_delete(foc, lid, pid)

    def request_point_list(self, foc, lid, limit=500, offset=0):
        return self.__qc.request_point_list(foc, lid, limit=limit, offset=offset)

    def request_point_list_detailed(self, foc, lid, pid):
        return self.__qc.request_point_list_detailed(foc, lid, pid)

    def request_point_meta_get(self, foc, lid, pid, fmt="n3"):
        return self.__qc.request_point_meta_get(foc, lid, pid, fmt=fmt)

    def request_point_meta_set(self, foc, lid, pid, meta, fmt="n3"):
        return self.__qc.request_point_meta_set(foc, lid, pid, meta, fmt=fmt)

    def request_point_value_create(self, lid, pid, foc, label, vtype, lang=None, comment=None, unit=None):
        return self.__qc.request_point_value_create(lid, pid, foc, label, vtype, lang=lang, comment=comment, unit=unit)

    def request_point_value_delete(self, lid, pid, foc, label, lang=None):
        return self.__qc.request_point_value_delete(lid, pid, foc, label, lang=lang)

    def request_point_value_list(self, lid, pid, foc, limit=500, offset=0):
        return self.__qc.request_point_value_list(lid, pid, foc, limit=limit, offset=offset)

    def request_point_tag_create(self, foc, lid, pid, tags, lang=None, delete=False):
        return self.__qc.request_point_tag_create(foc, lid, pid, tags, lang=lang, delete=delete)

    def request_point_tag_delete(self, foc, lid, pid, tags, lang=None):
        return self.__qc.request_point_tag_create(foc, lid, pid, tags, lang=lang, delete=True)

    def request_point_tag_list(self, foc, lid, pid, limit=500, offset=0):
        return self.__qc.request_point_tag_list(foc, lid, pid, limit=limit, offset=offset)

    def request_sub_create(self, lid, foc, gpid, callback=None):
        return self.__qc.request_sub_create(lid, foc, gpid, callback=callback)

    def request_sub_create_local(self, slid, foc, lid, pid, callback=None):
        return self.__qc.request_sub_create_local(slid, foc, lid, pid, callback=callback)

    def request_point_share(self, lid, pid, data, mime=None):
        return self.__qc.request_point_share(lid, pid, data, mime=mime)

    def request_sub_ask(self, sub_id, data, mime=None):
        return self.__qc.request_sub_ask(sub_id, data, mime=mime)

    def request_sub_tell(self, sub_id, data, timeout, mime=None):
        return self.__qc.request_sub_tell(sub_id, data, timeout, mime=mime)

    def request_sub_delete(self, sub_id):
        return self.__qc.request_sub_delete(sub_id)

    def request_sub_list(self, lid, limit=500, offset=0):
        return self.__qc.request_sub_list(lid, limit=limit, offset=offset)

    def request_search(self, text=None, lang=None, location=None, unit=None, limit=100, offset=0, type_='full'):
        return self.__qc.request_search(text=text, lang=lang, location=location, unit=unit,
                                        limit=limit, offset=offset, type_=type_)

    def request_describe(self, guid):
        return self.__qc.request_describe(guid)

    def __cb_feeddata(self, data):
        if self.__keepFeeddata == 0:
            return
        while self.__qFeeddata.qsize() > self.__keepFeeddata:
            self.__qFeeddata.get()  # throw away element
        self.__qFeeddata.put(data)

    def get_feeddata(self):
        ret = []
        while self.__qFeeddata.qsize() > 0:
            ret.append(self.__qFeeddata.get())
        return ret

    def __cb_controlreq(self, data):
        if self.__keepControlreq == 0:
            return
        while self.__qControlreq.qsize() > self.__keepControlreq:
            self.__qControlreq.get()  # throw away element
        self.__qControlreq.put(data)

    def get_controlreq(self):
        ret = []
        while self.__qControlreq.qsize() > 0:
            ret.append(self.__qControlreq.get())
        return ret

    def __cb_unsolicited(self, data):
        if self.__keepUnsolicited == 0:
            return
        while self.__qUnsolicited.qsize() > self.__keepUnsolicited:
            self.__qUnsolicited.get()  # throw away element
        self.__qUnsolicited.put(data)

    def get_unsolicited(self):
        ret = []
        while self.__qUnsolicited.qsize() > 0:
            ret.append(self.__qUnsolicited.get())
        return ret

    def __run(self):
        #
        self.__qc = IoticAgentCore.Client(
            self.__details['host'],
            self.__vhost,
            self.__details['epid'],
            self.__details['passwd'],
            self.__details['token'],
            prefix=self.__prefix,
            sslca=self.__sslca,
            send_queue_size=self.__queue_size,
            throttle_conf=self.__throttle_conf
        )
        # network_retry_timeout=10,  # todo: override in config ?
        #
        # Keep trying to start the worker
        dead_count = 0
        done = False
        while not done and not self.__stop.is_set() and\
                not self.__managerStop.is_set() and\
                dead_count < self.__dead_max:
            done = True
            try:
                self.__qc.start()
            except:
                logger.error("Worker %s FAILED TO START sleep(%i)...", self.__details['epid'], self.__dead_sleep)
                done = False
                dead_count += 1
                sleep(self.__dead_sleep)
        if dead_count >= self.__dead_max:
            return
        #
        self.__qc.register_callback_feeddata(self.__cb_feeddata)
        self.__qc.register_callback_controlreq(self.__cb_controlreq)
        self.__qc.register_callback_reassigned(self.__cb_unsolicited)
        self.__qc.register_callback_subscription(self.__cb_unsolicited)
        #
        while not self.__stop.is_set() and not self.__managerStop.is_set():
            logger.debug("QAPIWorker %s still running", self.__details['epid'])
            self.__stop.wait(self.__polltime)
        # Clean-up
        try:
            self.__qc.stop()
        except:
            pass
