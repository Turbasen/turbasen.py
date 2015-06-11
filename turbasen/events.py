# encoding: utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

handlers = {}

def handle_event(event, callback):
    if event in handlers:
        handlers[event].append(callback)
    else:
        handlers[event] = [callback]

def trigger(event):
    for callback in handlers.get(event, []):
        callback()
