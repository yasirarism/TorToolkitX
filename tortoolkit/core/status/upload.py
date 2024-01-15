# -*- coding: utf-8 -*-
# (c) YashDK [yash-dk@github]
# (c) modified by AmirulAndalib [amirulandalib@github]

import logging
import os
import re

from telethon.errors.rpcerrorlist import FloodWaitError, MessageNotModifiedError

from ..getVars import get_val
from .status import Status

torlog = logging.getLogger(__name__)


class TGUploadTask(Status):
    def __init__(self, task):
        super().__init__()
        self.Tasks.append(self)
        self._dl_task = task
        self._files = 0
        self._dirs = 0
        self._uploaded_files = 0
        self._active = True
        self._current_file = ""
        self._message = None
        self._omess = None
        self.cancel = False

    async def get_message(self):
        return self._message

    async def get_sender_id(self):
        return self._omess.sender_id

    async def get_original_message(self):
        return self._omess

    async def set_message(self, message):
        self._message = message

    async def set_original_message(self, omess):
        self._omess = omess

    async def set_inactive(self):
        self._active = False

    async def is_active(self):
        return self._active

    async def add_a_dir(self, path):
        await self.dl_files(path)

    async def dl_files(self, path=None):
        if path is None:
            path = await self._dl_task.get_path()

        if os.path.isfile(path):
            self._files += 1
            return

        files = self._files
        dirs = self._dirs
        for _, d, f in os.walk(path, topdown=False):
            for _ in f:
                files += 1
            for _ in d:
                dirs += 1

        # maybe will add blacklisting of Extensions
        self._files = files
        self._dirs = dirs

    async def uploaded_file(self, name=None):
        self._uploaded_files += 1
        print(f"\n----updates files to {self._uploaded_files}\n")
        self._current_file = str(name)

    async def create_message(self):
        msg = f"<b>Uploading:- </b> <code>{self._current_file}</code>\n"
        prg = 0
        try:
            prg = self._uploaded_files / self._files

        except ZeroDivisionError:
            pass
        msg += f"<b>Progress:- </b> {self.progress_bar(prg)} - {prg * 100}%\n"
        msg += f"<b>Files:- </b> {self._uploaded_files} of {self._files} done.\n"
        msg += "<b>Using Engine:- </b> <code>TG Upload</code>\n"
        return msg

    def progress_bar(self, percentage):
        """Returns a progress bar for download"""
        # percentage is on the scale of 0-1
        comp = get_val("COMPLETED_STR")
        ncomp = get_val("REMAINING_STR")
        return "".join(
            comp if i <= int(percentage * 10) else ncomp for i in range(1, 11)
        )


class RCUploadTask(Status):
    def __init__(self, task):
        super().__init__()
        self.Tasks.append(self)
        self._dl_task = task
        self._active = True
        self._upmsg = ""
        self._prev_cont = ""
        self._message = None
        self._error = ""
        self._omess = None
        self.cancel = False

    async def set_original_message(self, omess):
        self._omess = omess

    async def get_original_message(self):
        return self._omess

    async def get_sender_id(self):
        return self._omess.sender_id

    async def set_message(self, message):
        self._message = message

    async def refresh_info(self, msg):
        # The rclone is process dependent so cant be updated here.
        self._upmsg = msg

    async def create_message(self):
        mat = re.findall("Transferred:.*ETA.*", self._upmsg)
        nstr = mat[0].replace("Transferred:", "")
        nstr = nstr.strip()
        nstr = nstr.split(",")
        prg = nstr[1].strip("% ")
        prg = f"Progress:- {self.progress_bar(prg)} - {prg}%"
        return f'<b>Uploaded:- {nstr[0]} \n{prg} \nSpeed:- {nstr[2]} \nETA:- {nstr[3].replace("ETA", "")}</b> \n<b>Using Engine:- </b><code>RCLONE</code>'

    def progress_bar(self, percentage):
        """Returns a progress bar for download"""
        # percentage is on the scale of 0-1
        comp = get_val("COMPLETED_STR")
        ncomp = get_val("REMAINING_STR")
        try:
            percentage = int(percentage)
        except:
            percentage = 0

        return "".join(comp if i <= percentage // 10 else ncomp for i in range(1, 11))

    async def update_message(self):
        progress = await self.create_message()
        if self._prev_cont != progress:
            # kept just in case
            self._prev_cont = progress
            try:
                await self._message.edit(progress, parse_mode="html")
            except MessageNotModifiedError as e:
                torlog.debug(f"{e}")
            except FloodWaitError as e:
                torlog.error(f"{e}")
            except Exception as e:
                torlog.info(f"Not expected {e}")

    async def is_active(self):
        return self._active

    async def set_inactive(self, error=None):
        self._active = False
        if error is not None:
            self._error = error
