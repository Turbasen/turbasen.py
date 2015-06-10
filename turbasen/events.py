handlers = {}

def handle_event(event, callback):
    if event in handlers:
        handlers[event].append(callback)
    else:
        handlers[event] = [callback]

def trigger(event):
    for callback in handlers.get(event, []):
        callback()
