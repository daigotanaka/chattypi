# The MIT License (MIT)
#
# Copyright (c) 2013 Daigo Tanaka (@daigotanaka)
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

from config import config
import inspect
import logging
import os
import sqlite3
import sys

from peewee import CharField, Model, SqliteDatabase


logger = logging.getLogger(__name__)

sqlite_db = SqliteDatabase(
    os.path.join(
        config.get("system")["default_path"],
        config.get("system")["db_file"]))


def connect_db():
    sqlite_db.connect()
    init_db()


def init_db():
    module = sys.modules[__name__]
    for symbol in dir(module):
        if symbol == "BaseModel":
            continue
        model = getattr(module, symbol)
        if not inspect.isclass(model):
            continue
        try:
            instance = model()
        except Exception:
            continue
        if not isinstance(instance, BaseModel):
            continue
        try:
            model.create_table()
            logger.debug("Created DB table for %s" % symbol)
        except sqlite3.OperationalError:  # Table already exists
            pass


class BaseModel(Model):
    class Meta:
        database = sqlite_db


class CommandNickname(BaseModel):
    nickname = CharField()
    command = CharField()
